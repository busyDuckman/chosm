import asyncio
import copy
import fnmatch
import io
import itertools
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Dict, List, Tuple, Literal, Iterator, Type, Any
import logging
import os
import time

import numpy as np
from slugify import slugify
from numba import njit

import helpers.stream_helpers as sh
from chosm.asset import Asset
from chosm.game_constants import SpriteRoles
from chosm.map_asset import MapAsset
from chosm.resource_pack import ResourcePackInfo
from chosm.sprite_asset import SpriteAsset
from chosm.world_asset import WorldAsset
from game_engine.map import AssetLut
from game_engine.world import World
from mam_game.binary_file import load_bin_file
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, normalise_file_name
from mam_game.mam_sprite_alignments import flatten_ground_sprite, flatten_sky_sprite
from mam_game.map_organiser import combine_map_assets
from mam_game.map_file_decoder import RawFile, load_map_file
from mam_game.npc_db_decoder import load_monster_database_file
from mam_game.pal_file_decoder import load_pal_file, get_default_pal
from chosm.pal_asset import PalAsset
from mam_game.sprite_file_decoder import load_sprite_file


@dataclass
class TOCRecord:
    """
    Ued internally by CCFile to store table of contents records.
    """
    file_id: int
    offset: int
    length: int
    toc_position: int
    name: str

    def __str__(self):
        return f"[{hex(self.file_id)}->'{self.name}' (toc index {self.toc_position}, {self.length} bytes at {self.offset})]"


# TODO: This needs a superclass, so the functionality of "asset manager" can be shared with:
#   - other legacy game loading logic
#   - asset reprocessing logic (eg: upscaling)

class CCFile:
    def __init__(self, file_path, id_to_name_lut: Dict[int, str], ver: MAMVersion, platform: Platform):
        """
        This loads the cc file.
          - Note: this is not a 1:1 set of files for every file in the cc file.
            Rather we create "self.resources", a collection of game assets that may integrate
            multiple source files into the final output.

        :param id_to_name_lut:
            Only integer hashes, used as file IDs are stored in the game source data (.cc, .cur, .sav).
            This lut provides a corresponding file name, if known.
        """

        print("Loading: " + os.path.split(file_path)[1])
        self.file = os.path.split(file_path)[-1]
        self.file_size = os.path.getsize(file_path)
        self.xor_encryption_value = 0x35
        self.mam_version: MAMVersion = ver
        self.mam_platform = platform
        self.slug = slugify(f"{self.file}_{self.mam_version}_{self.mam_platform}")

        logging.debug(f"loading cc file: file={self.file}, size={self.file_size}")
        with open(file_path, 'rb') as f:
            # parse TOC
            self.num_files = sh.read_uint16(f)
            if not (10 < self.num_files < 10_000):
                raise MAMFileParseError(0, self.file, f"{self.file} has an improbable amount of files ({self.num_files}).")
            logging.debug(f"parsing cc file: file={self.file}, num_files={self.num_files}")
            print(f"  - decrypting TOC")
            self.toc = self._read_toc(f, id_to_name_lut)
            print(f"  - TOC has {len(self.toc)} files")

            # read and decrypt all files
            print(f"  - decrypting files")
            self._raw_data_lut: Dict[Literal[int, str], RawFile] = {}
            for r in self.toc:
                raw = self._load_raw_file(r, f)
                self._raw_data_lut[r.file_id] = raw
                self._raw_data_lut[r.name] = raw

        # note: names in the TOC are normalised
        self._toc_file_names = [r.name for r in self.toc if r.name is not None]
        self._toc_file_ids = [r.file_id for r in self.toc if r.file_id is not None]

        # A chained file is like an include or import. ie: The file contains assets needed to load this file.
        self.chained_files: Dict = {}

        self._resources: List[Asset] = []

    def merge(self, other, to_copy=True):
        other: CCFile = other
        print(f"Merging {self.file} and {other.file}")
        if to_copy:
            merged = copy.deepcopy(self)
        else:
            merged = self

        if os.path.splitext(merged.file)[0] == os.path.splitext(other.file)[0]:
            merged.file += os.path.splitext(other.file)[1].strip(".")
        else:
            merged.file = f"{self.file}_{other.file}"

        merged.file_size = -1
        merged.slug = slugify(f"{merged.file}_{self.mam_version}_{self.mam_platform}")
        merged.num_files += other.num_files
        merged.toc += other.toc
        merged._raw_data_lut |= other._raw_data_lut
        merged._toc_file_names += other._toc_file_names
        merged._toc_file_ids += other._toc_file_ids
        merged._resources += other._resources

        return merged


    def get_resources(self, res_type: Type, glob_epr: str = None) -> List[Asset]:
        res = [r for r in self._resources if isinstance(r, res_type)]
        if glob_epr is not None:
            res = [r for r in res if fnmatch.fnmatch(r.name, glob_epr)]
        return res

    def get_resource(self, res_type: Type, id_or_name: Literal[int, str]):
        # turns out, making this getter complex makes a lot of other code simple.
        # if it needs to work faster, add LUTs later.
        # assert type(res_type) == type
        assert id_or_name is not None

        if type(id_or_name) == int:
            res = [r for r in self._resources if isinstance(r, res_type) and r.file_id == id_or_name]
        else:
            name = normalise_file_name(str(id_or_name))
            res = [r for r in self._resources if isinstance(r, res_type) and r.name == name]

        assert len(res) <= 1  # check for duplicated key
        if len(res) == 0:
            raise KeyError(id_or_name)
        return res[0]

    def chain_cc_file(self, other):
        self.chained_files[other.file] = other


    def _read_toc(self, f, id_to_name_lut) -> List[TOCRecord]:
        """
        Reads and validates the table of contents.
        :param f: file stream
        :param id_to_name_lut: get a known name for an id (names are not stores in the cc file).
        """

        # read and decrypt the TOC data
        toc_size = self.num_files * 8
        toc_bytes = sh.read_byte_array(f, n=toc_size)
        toc_bytes = self._decrypt_toc(toc_bytes)

        # parse the TOC
        ftoc = io.BytesIO(bytearray(toc_bytes))
        toc_rows = sh.read_dict(ftoc,
                        [("file_id", "uint16"), ("offset", "uint24"), ("length", "uint16"), ("padding", "byte")],
                        n=self.num_files)

        # Create output
        toc: List[TOCRecord] = []
        for i, t in enumerate(toc_rows):
            f_id, f_offset, f_len = t["file_id"], t["offset"], t["length"]
            toc_rec = TOCRecord(f_id, f_offset, f_len, i, None)

            # get known name
            if f_id in id_to_name_lut:
                name = normalise_file_name(id_to_name_lut[f_id])
                if len(name) > 0:
                    toc_rec.name = name

            if toc_rec.name is None:
                logging.warning(f"No known filename for TOC entry: file={self.file}. TOC={toc_rec}")

            # append
            toc.append(toc_rec)

            # validate
            if t["padding"] != 0:
                logging.warning(f"expected padding to be 0 in toc entry: file={self.file}, toc_number={i}")
            if toc_rec.offset + toc_rec.length > self.file_size:
                # logging.error(f"toc record {i} went pat end of file: {toc_rec}")
                raise MAMFileParseError(0, self.file, f"toc record {i} went past end of file: file={self.file}, toc={toc_rec}")

        # validate TOC: any overlaps or gaps?
        toc.sort(key=lambda r: r.offset)
        for i, rec in enumerate(toc[:-1]):
            next_rec = toc[i+1]
            end = rec.offset + rec.length
            if end > next_rec.offset:
                raise MAMFileParseError(0, self.file, f"TOC record went past next file: file={self.file}, toc={rec}")
            if end < (next_rec.offset - 1):
                gap_length = (next_rec.offset - 1) - end
                logging.warning(f"A gap exists in the cc file: file={self.file} offset={end}, length={gap_length}")

        # validate TOC: gap at start or end of file?
        if (toc[-1].offset + toc[-1].length) != self.file_size:
            gap_length = self.file_size - (toc[-1].offset + toc[-1].length)
            logging.warning(f"Unused data at end of file: file={self.file}, length={gap_length}")

        file_pos = f.tell()
        if toc[0].offset != file_pos:
            gap_length = file_pos - toc[0].offset
            logging.warning(f"Unused data after TOC: file={self.file}, len={gap_length}")

        # done.
        return toc

    def _decrypt_toc(self, toc_bytes: List) -> List:
        """
        The TOC has a custom encryption algorithm.
        It needs to be decrypted as one blob.
        https://xeen.fandom.com/wiki/CC_File_Format#Table_of_Contents
        """
        raw_toc = toc_bytes.copy()
        ah = 0xac
        for i, r in enumerate(raw_toc):
            r = r & 0xff
            lsl2 = (r << 2) & 0xff
            raw_toc[i] = (((lsl2 | (r >> 6)) + ah) & 0xff)
            ah += 0x67
        return raw_toc

    @staticmethod
    def get_file_name_hash(name) -> int:
        """
        Hashes a string to creat a file_id in the TOC
        see: https://xeen.fandom.com/wiki/CC_File_Format#Filename_hashing_algorithm
        """
        if len(name) == 0:
            return -1

        name_ascii = list(bytes(name, 'ascii'))
        h = int(name_ascii[0])
        for i in range(1, len(name_ascii)):
            h = ((h & 0x007F) << 9) | ((h & 0xFF80) >> 7)
            h += int(name_ascii[i])

        return h

    def is_encrypted(self):
        if self.file.lower() in ["dark.cur", "clouds.cur"]:
            return False
        return True

    def decrypt(self, data: List) -> List:
        d2 = [(d ^ self.xor_encryption_value) & 0xff for d in data]
        return d2

    def _load_raw_file(self, toc_record: TOCRecord, f) -> RawFile:
        f.seek(toc_record.offset)
        data = f.read(toc_record.length)
        if self.is_encrypted():
            data = self.decrypt(data)
        return RawFile(toc_record.file_id, toc_record.name, data)

    def get_pal_for_file(self, name):
        pal = None
        match self.mam_version:
            case MAMVersion.CLOUDS:
                pal = self.get_resource(PalAsset, "MM4.PAL")
            case MAMVersion.DARKSIDE:
                pal = self.get_resource(PalAsset, "default.pal")
        return pal

    def bootstrap(self):
        """
        Loads a set of game assets into self.resources, by parsing the files in this cc file.
        It may be necessary to chain other .cc files prior to calling bootstrap.
        """
        print(f"Loading game assets from {self.file}")
        # first we need tha palettes, so sprites can be decoded
        pal_names = fnmatch.filter(self._toc_file_names, "*.pal")
        print("  - found palettes: " + ", ".join(pal_names))
        for f_name in pal_names:
            raw = self._raw_data_lut[f_name]
            pal = load_pal_file(self._raw_data_lut[f_name], self.mam_version, self.mam_platform)
            self._resources.append(pal)

        def_pal = get_default_pal(self.mam_version, self.mam_platform)
        self._resources.append(def_pal)

        self.bootstrap_environment_sprites()
        self._bootstrap_tiles()
        self._bootstrap_maps()
        self._bootstrap_monsters()

        self._bootstrap_faces()
        self._bootstrap_worlds()

    def _bootstrap_faces(self):
        print(f"  - loading faces: ")
        sprites = fnmatch.filter(self._toc_file_names, f"*.fac")
        for f_name in sprites:
            print(".", end='')
            pal = self.get_pal_for_file(f_name)
            raw: RawFile = self._raw_data_lut[f_name]
            sprite = load_sprite_file(raw, pal, self.mam_version, self.mam_platform)
            self._resources.append(sprite)
        print()

    def bootstrap_environment_sprites(self):
        # graphics for the 3d view (environment ets)
        print(f"  - loading environment sprites: ")
        for ext, role in zip(["sky", "gnd", "srf"],
                             [SpriteRoles.SKY, SpriteRoles.GROUND, SpriteRoles.GROUND]):
            sprites = fnmatch.filter(self._toc_file_names, f"*.{ext}")
            print(f"  - {ext} ({len(sprites)}): ", end='')
            for f_name in sprites:
                print(".", end='')

                pal = self.get_pal_for_file(f_name)
                raw: RawFile = self._raw_data_lut[f_name]
                sprite = load_sprite_file(raw, pal, self.mam_version, self.mam_platform)

                environment_name = os.path.splitext(f_name)[0].strip(".").lower()

                sprite.add_role(role)
                sprite.add_env_description(environment_name)

                sprite.tag(f"type_{ext}")
                sprite.tag(f"environment_{environment_name}")
                sprite.tag("environment")

                self._resources.append(sprite)

                if ext == "srf":
                    sprite_flat = flatten_ground_sprite(sprite)
                    self._resources.append(sprite_flat)
                elif ext == "sky":
                    sky_flat = flatten_sky_sprite(sprite)
                    self._resources.append(sky_flat)
            print()
        print()

        # sprites = fnmatch.filter(self._toc_file_names, "*.sky")
        # sprites += fnmatch.filter(self._toc_file_names, "*.gnd")
        # sprites += fnmatch.filter(self._toc_file_names, "*.fwl")
        # sprites += fnmatch.filter(self._toc_file_names, "*.swl")

    def _bootstrap_worlds(self):
        maps: List[MapAsset] = self.get_resources(MapAsset)
        outdoor = next(m for m in maps if m.file_id == 1)
        name = {MAMVersion.DARKSIDE: "Darkside of Xeen",
                MAMVersion.CLOUDS: "Clouds of Xeen",
                MAMVersion.MM3: "Isles of Terra"}[self.mam_version]
        world = World(name, [outdoor.game_map], [])
        world_asset = WorldAsset(1, "main_world", world)
        self._resources.append(world_asset)

    def _bootstrap_tiles(self):
        # organise the tile graphics
        print(f"  - loading tile graphics:  ")

        image_names = fnmatch.filter(self._toc_file_names, "*.til")

        for f_name in image_names:
            pal = self.get_pal_for_file(f_name)
            raw = self._raw_data_lut[f_name]
            sprite = load_sprite_file(raw, pal, self.mam_version, self.mam_platform)
            if "outdoor" in f_name:
                # outdoor.til handled a bit differently
                sprite = sprite.crop(0, 0, 10, 8)
                ground, rest = sprite.split(16, left_name="outdoor_tile_ground.til")
                env, building = rest.split(16, left_name="outdoor_tile_env.til", right_name="outdoor_tile_building.til")
                self._resources.append(sprite)
                self._resources.append(ground)
                self._resources.append(env)
                self._resources.append(building)

                for tile_set, lut_name in zip([ground, env, building], ["ground-map", "env-map", "building-map"]):
                    # Every frame in tile_sprite is a map drawing sprite.
                    for i in range(tile_set.num_frames()):
                        name = f"{tile_set.name}_{i}"
                        a_tile = tile_set.copy_frames(i, name, new_id=i)
                        a_tile.tag(lut_name)
                        a_tile.tag("tile")
                        self._resources.append(a_tile)

            else:
                tile_set, tile_border = sprite.split(sprite.num_frames() - 1,
                                                     left_name=sprite.name, right_name=sprite.name + "_border",
                                                     left_id=sprite.file_id)

                # The sprite has empty space, with the icons in the top left.
                tile_set: SpriteAsset = tile_set.crop(0, 0, 10, 8, new_name=tile_set.name)
                # tile_set.tag("tile")
                self._resources.append(tile_set)

                # Every frame in this sprite is a map drawing sprite.
                # tile_lut =
                # for i in range(tile_set.num_frames()):
                #     name = f"{tile_set.name}_{i}"
                #     a_tile = tile_set.copy_frames(1, name, new_id=i)
                #     self._resources.append(a_tile)
                #     tile_lut[i] = a_tile.slug
                #     tile_lut = AssetLut(f_name, tile_lut)
                #
                # tile_luts[f_name] = tile_lut

                self._resources.append(tile_border)

                # layer1, rest = tile_set.split(16, left_name=sprite.name + "_layer_00")
                # layer2, rest = rest.split(16, left_name=sprite.name + "_layer_01")
                # layer3, layer4 = rest.split(16, left_name=sprite.name + "_layer_02")

    def _bootstrap_maps(self):
        tile_sprites = [q for q in self.get_resources(SpriteAsset) if "tile" in q.tags]

        # create luts
        # just load the outdoor for now
        luts_by_name: Dict[str, Dict[Any, SpriteAsset]] = {}
        for lut_name in ["ground-map", "env-map", "building-map"]:
            lut = {s.file_id: s for s in tile_sprites if lut_name in s.tags}
            luts_by_name[lut_name] = lut
        # tile_sets = ["cave.til", "cstl.til", "dung.til", "outdoor.til", "town.til",  "scfi.til",  "towr.til"]

        # organise the maps
        maps = fnmatch.filter(self._toc_file_names, "m*.dat")
        print([s for s in self._toc_file_names if '.dat' in s])
        print([s for s in self._toc_file_names if '.mob' in s])
        print(f"  - loading {len(maps)} maps: ", end="")

        # load all maps
        map_assets = []
        for f_name in maps:
            print(f_name)
            raw_dat = self._raw_data_lut[f_name]

            # load .evt and .mob isf possible
            mob_file_name = f_name.replace(".dat", ".mob")
            evt_file_name = f_name.replace(".dat", ".evt")
            if mob_file_name in self._raw_data_lut:
                raw_mob = self._raw_data_lut[mob_file_name]
                raw_evt = self._raw_data_lut[evt_file_name]
            else:
                print("Expected a mob file: " + mob_file_name)
                raw_mob = raw_evt = None

            # load map
            map_file = load_map_file(raw_dat, raw_mob, raw_evt, self.mam_version, self.mam_platform)
            map_assets.append(map_file)

        # join adjacent maps into larger maps
        the_maps = combine_map_assets(map_assets, self.mam_version, self.mam_platform)

        for m in the_maps:
            m.set_luts(luts_by_name)

        self._resources.extend(the_maps)
        print()

    def _bootstrap_monsters(self):
        # get the monster configs
        print(f"  - loading monster stats: ", end="")
        for f_name in ["dark.mon", "xeen.mon"]:
            if f_name in self._toc_file_names:
                print(f"{f_name}, ", end="")
                mon_file = load_monster_database_file(self._raw_data_lut[f_name], self.mam_version, self.mam_platform)
                self._resources.append(mon_file)
        print("  - done.")

        # load the base monster animations
        mons = fnmatch.filter(self._toc_file_names, "*.mon")
        mons = [n for n in mons if n[0].isdigit()]  # ie: NOT "dark.mon", "xeen.mon", etc
        print(f"  - loading {len(mons)} monsters: ", end='')
        for f_name in mons:
            print(".", end='')
            pal = self.get_pal_for_file(f_name)
            raw = self._raw_data_lut[f_name]
            sprite = load_sprite_file(raw, pal, self.mam_version, self.mam_platform)
            self._resources.append(sprite)

            raw_att = self._raw_data_lut[f_name.replace(".mon", ".att")]
            sprite2 = load_sprite_file(raw_att, pal, self.mam_version, self.mam_platform)
            self._resources.append(sprite2)
        print()

    def bake(self, bake_dir=None):
        """
        Extract all files to a folder
        """
        print("Baking resources: ")
        if bake_dir is None:
            bake_dir = ["game_files", "../game_files"]
            bake_dir = [b for b in bake_dir if os.path.isdir(b)]
            bake_dir = os.path.abspath(bake_dir[0])
            bake_dir = os.path.join(bake_dir, "baked")

        bake_path = os.path.join(bake_dir, self.slug)
        if os.path.exists(bake_path):
            # because I don't trust software to delete a path without some sanity checks
            assert Path(bake_dir) in Path(bake_path).parents
            assert len(self.slug.strip()) > 0
            shutil.rmtree(bake_path)
        os.makedirs(bake_path, exist_ok=True)

        print("  - output dir : " + str(bake_path))

        # Setup a resource pack, by creating info.json
        rp = ResourcePackInfo(self.slug, "duckman", False)
        rp.is_private = True
        rp.author_info = "Developed by New World Computing, not in the public domain. Used here for research purposes only."
        rp.save_info_file(bake_path)

        # bake all the files
        print(f"  - baking {len(self._resources)} resources: ", end="")
        for i, obj in enumerate(self._resources):
            try:
                if obj is not None:
                    print(obj.get_type_name()[0], end="\n    " if (i+23) % 70 == 0 else "")
                    obj_path = os.path.join(bake_path, obj.slug)
                    assert Path(bake_dir) in Path(obj_path).parents
                    os.makedirs(obj_path, exist_ok=True)
                    obj.bake(obj_path)
            except MAMFileParseError:
                pass
        print()

        return bake_path


def parse_toc_csv(file_path) -> List[Tuple[str, int, str]]:
    """
    Loads a csv with known file names (a cc file does not list the file names)
    """
    def parse_hash(h):
        if h is None or\
                len(h.strip()) == 0:
            return None
        return int(h, 16)

    with open(file_path, 'rt') as f:
        lines = [r.strip() for r in f.read().splitlines()][1:]
        lines = [r.split(",", maxsplit=2) for r in lines]
        return [(n, parse_hash(h), d) for n, h, d in lines]


def infer_cur_file_lut(num_mazes: int = 200):
    lut = {CCFile.get_file_name_hash(f): f for f in ["MAZE.PTY", "MAZE.CHR", "MAZE.NAM"]}
    for ext in ["DAT", "MOB", "EVT"]:
        for i in range(num_mazes):
            token = "0" if i < 100 else "X"
            file_name = f"MAZE{token}{i:03d}.{ext}"
            file_name_hash = CCFile.get_file_name_hash(file_name)

            assert (file_name_hash not in lut)
            lut[file_name_hash] = file_name
    return lut


def load_cc_file(path: str, ver: MAMVersion, platform: Platform) -> CCFile:
    p, f = os.path.split(path)
    if not f.lower().endswith(".cur"):
        csv_path = os.path.join(p, (f+".csv").lower())
        known_files = parse_toc_csv(csv_path)
        id_to_name_lut = {CCFile.get_file_name_hash(k_name.strip()): k_name for k_name, _, _ in known_files}
    else:
        id_to_name_lut = infer_cur_file_lut()
    cc_file = CCFile(path, id_to_name_lut, ver, platform)
    return cc_file


# ----------------------------------------------------------------------------------------------------------------------
def main():
    logging.basicConfig(level=logging.ERROR)

    started = time.time()

    dark_cc = load_cc_file(f"../game_files/dos/DARK.CC",  MAMVersion.DARKSIDE, Platform.PC_DOS)
    dark_cur = load_cc_file(f"../game_files/dos/DARK.CUR", MAMVersion.DARKSIDE, Platform.PC_DOS)
    mm5_cc = dark_cc.merge(dark_cur, to_copy=False)
    mm5_cc.bootstrap()
    mm5_cc.bake()

    # mm4_cc = load_cc_file(f"../game_files/dos/XEEN.CC",  MAMVersion.CLOUDS, Platform.PC_DOS)
    # mm4_cur = load_cc_file(f"../game_files/dos/XEEN.CUR", MAMVersion.CLOUDS, Platform.PC_DOS)
    # mm4_cc = mm4_cc.merge(mm4_cur, to_copy=False)
    # mm4_cc.bootstrap()
    # mm4_cc.bake()

    finished = time.time() - started
    print(f"Finished in {finished:.1f} seconds")

    # ccf_intro_cc = load_cc_file(f"../game_files/dos/INTRO.CC", MAMVersion.DARKSIDE, Platform.PC_DOS)
    # ccf_mm3_cc =   load_cc_file("../game_files/dos/MM3.CC",    MAMVersion.MM3,      Platform.PC_DOS)

    # ccf_dark_cc.bake()

    # all_cc_files = [ccf_dark_cc, ccf_intro_cc, ccf_xeen_cc, ccf_mm3_cc]
    # all_cc_files = [ccf_dark_cc]

    # for cc_file in all_cc_files:
    #     cc_file.bake()

if __name__ == '__main__':
    main()
