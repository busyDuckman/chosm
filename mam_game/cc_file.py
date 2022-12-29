import copy
import fnmatch
import io
import itertools
import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, Dict, List, Tuple, Literal, Iterator, Type
import logging
import os

import numpy as np
from slugify import slugify
import helpers.stream_helpers as sh
from mam_game.binary_file import load_bin_file
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, normalise_file_name
from mam_game.mam_file import MAMFile
from mam_game.map_file import RawFile, load_map_file
from mam_game.mmorpg_constants import default_new_policy
from mam_game.monster_db_file import load_monster_database_file
from mam_game.pal_file import load_pal_file, get_default_pal, PalFile
from mam_game.sprite_file import load_sprite_file, SpriteFile


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

        self._resources: List[MAMFile] = []

    def merge(self, other):
        other: CCFile = other
        print(f"Merging {self.file} and {other.file}")
        merged = copy.deepcopy(self)
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



    def get_resources(self, res_type: Type, glob_epr: str = None):
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

    # def all_resources(self) -> Iterator[MAMFile]:
    #     pals = list(set(self.resources_pal.values()))
    #     return itertools.chain(pals)

    # def _set_file(self, name, file_id, mam_file: MAMFile):
    #     if file_id is None:
    #         raise ValueError(f"Key can not be none: file={str(file_id)}")
    #     self._files_by_id[file_id] = mam_file
    #     self._files_by_name[name] = mam_file

    # def get_file(self,
    #              name_or_id: Literal[str, int],
    #              chained_cc_file_name: str = None):
    #     # check if redirect
    #     if chained_cc_file_name is not None:
    #         self._chained_files[chained_cc_file_name].get_file(name_or_id)
    #
    #     # check if file was loaded previously
    #     if type(name_or_id) == int:
    #         if name_or_id in self._files_by_id:
    #             return self._files_by_id[name_or_id]
    #         r = self._toc_lut_by_id.get(name_or_id, None)
    #     else:
    #         name_or_id = normalise_file_name(name_or_id)
    #         if name_or_id in self._files_by_name:
    #             return self._files_by_name[name_or_id]
    #         r = self._toc_lut_by_name.get(name_or_id, None)
    #
    #     if r is None:
    #         raise ValueError(f"key not found: file={self.file}, key={name_or_id}")
    #
    #     # Load from cc_file data
    #     try:
    #         mam_file = self.load_mam_file(r.file_id, r.name, self._data_lut_by_id[r.file_id])
    #         if mam_file is not None:
    #             self._set_file(r.name, r.file_id, mam_file)
    #             return mam_file
    #     except MAMFileParseError as ex:
    #         logging.error(ex.message)
    #         raise ex
    #     # raise MAMFileParseError(r.file_id, self.file, "File not loaded, parse function returned None (perhaps unknown file type)")
    #     return None  # TODO, uncomment above


    # def parse_all_files(self):
    #     for r in self.toc:
    #         try:
    #             self.get_file(r.file_id)
    #         except MAMFileParseError as ex:
    #             logging.error(ex.message)
    #
    #     print(sorted(list(set([os.path.splitext(r.name)[1].lower() for r in self.toc if r.name is not None]))))
    #     print(f"  - Loaded {len(self._files_by_id)} files of {self.num_files}")

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

    # def load_mam_file(self, file_id: int,
    #                   name: str,
    #                   data: List,
    #                   fmt: str = None) -> MAMFile:
    #     if name is not None:
    #         name = name.strip().lower()
    #     else:
    #         name = "#" + str(file_id)
    #
    #     if fmt is None:
    #         f_name, fmt = [s.strip('.').lower() for s in os.path.splitext(name)]
    #
    #         # some files don't have an extension
    #         if fmt == '':
    #             name_lut = {"fnt": "fnt", "nullsnd": "voc"}
    #             fmt = name_lut.get(f_name, '')
    #
    #     # make the name more meaningful
    #     # extended_name = f"{name}@{self.file}"
    #     sprite_formats = ['mon', '0bj', 'sky', 'til', 'att']
    #     # sprite_formats = ['att', 'fac', 'fwl', 'gnd', 'icn',
    #     #                   'int', 'mon', '0bj', 'pic', 'sky', 'swl', 'til',
    #     #                   'twn', 'vga']  # 'fnt'
    #
    #     thing_formats = ['obj']
    #     text_formats = ['txt']
    #     raw_img_formats = ['raw']
    #     surface_formats = ['srf']
    #     pal_formats = ['pal']
    #     audio_formats = ['voc']
    #     music_formats = ['m']
    #     script_formats = ['evt']
    #     maze_formats = ['dat', 'mob']
    #     unknown_fmt = ['', 'brd', 'buf', 'drv', 'hed', 'out', 'wal', 'xen', 'zom', 'fnt']
    #     binary_fmt = ['bin']
    #     monster_db_fmt = ['mdb']  # note: not an actual extension in the .cc files AFAIK
    #
    #     match fmt:
    #         case ext if ext in sprite_formats:
    #             logging.info("Loading sprite: " + name)
    #
    #             pal = self.get_pal_for_file(name)
    #             return load_sprite_file(file_id, name, data, pal, self.mam_version, self.mam_platform)
    #
    #         case ext if ext in thing_formats:
    #             logging.info("Loading thing: " + name)
    #
    #         case ext if ext in text_formats:
    #             logging.info("Loading text file: " + name)
    #
    #         case ext if ext in raw_img_formats:
    #             logging.info("Loading raw image: " + name)
    #
    #         case ext if ext in surface_formats:
    #             logging.info("Loading surface: " + name)
    #
    #         case ext if ext in pal_formats:
    #             logging.warning("Loading palette: " + name)
    #             return load_pal_file(file_id, name, data, self.mam_version, self.mam_platform)
    #
    #         case ext if ext in audio_formats:
    #             logging.info("Loading audio sfx file: " + name)
    #
    #         case ext if ext in music_formats:
    #             logging.info("Loading music file: " + name)
    #
    #         case ext if ext in script_formats:
    #             logging.info("Loading script file: " + name)
    #
    #         case ext if ext in maze_formats:
    #             logging.info("Loading maze file: " + name)
    #
    #         case ext if ext in unknown_fmt:
    #             logging.info("Unknown unknown file: " + name)
    #
    #         case ext if ext in binary_fmt:
    #             logging.info("Loading binary file: " + name)
    #             return load_bin_file(file_id, name, data, self.mam_version, self.mam_platform)
    #
    #         case ext if ext in monster_db_fmt:
    #             logging.info("Loading monster database file: " + name)
    #             return load_monster_database_file(file_id, name, data, self.mam_version, self.mam_platform)
    #
    #         case _:
    #             logging.info("Unknown file (new format): " + name)
    #
    #     return None

    def get_pal_for_file(self, name):
        pal = None
        match self.mam_version:
            case MAMVersion.CLOUDS:
                pal = self.get_resource(PalFile, "MM4.PAL")
            case MAMVersion.DARKSIDE:
                pal = self.get_resource(PalFile, "default.pal")
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

        # get the monster configs
        print(f"  - loading monster stats: ", end="")
        for f_name in ["dark.mon", "xeen.mon"]:
            if f_name in self._toc_file_names:
                print(f"{f_name}, ", end="")
                mon_file = load_monster_database_file(self._raw_data_lut[f_name], self.mam_version, self.mam_platform)
                self._resources.append(mon_file)
        print("done.")

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

        print(f"  - loading hud/misc graphics: ")
        glob_list = ["*.til"]
        image_names = [fnmatch.filter(self._toc_file_names, e) for e in glob_list]
        image_names = np.array(image_names).flatten().tolist()
        for f_name in image_names:
            # print(f_name)
            pal = self.get_pal_for_file(f_name)
            raw = self._raw_data_lut[f_name]
            sprite = load_sprite_file(raw, pal, self.mam_version, self.mam_platform)
            self._resources.append(sprite)

        maps = fnmatch.filter(self._toc_file_names, "m*.dat")
        print([s for s in self._toc_file_names if '.dat' in s])
        print([s for s in self._toc_file_names if '.mob' in s])
        print(f"  - loading {len(maps)} maps: ", end="")
        # tile_sets = ["cave.til", "cstl.til", "dung.til", "outdoor.til", "town.til",  "scfi.til",  "towr.til"]
        for f_name in maps:
            print(f_name)
            raw_dat = self._raw_data_lut[f_name]
            mob_file_name = f_name.replace(".dat", ".mob")
            evt_file_name = f_name.replace(".dat", ".mob")
            tile_sets = self.get_resources(SpriteFile, "*.til")
            if mob_file_name in self._raw_data_lut:
                raw_mob = self._raw_data_lut[mob_file_name]
                raw_evt = self._raw_data_lut[evt_file_name]
                map_file = load_map_file(raw_dat, raw_mob, raw_evt, tile_sets, self.mam_version, self.mam_platform)
                self._resources.append(map_file)
            else:
                print("Expected a mob file: " + mob_file_name)
                map_file = load_map_file(raw_dat, None, None, tile_sets, self.mam_version, self.mam_platform)
                self._resources.append(map_file)
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

        # dump resource pack meta data
        info = {"name": self.slug,
                "chained_packs": [cc.slug for cc in self.chained_files],
                "policy": default_new_policy("duckman").to_dict()}

        with open(os.path.join(bake_path, "info.json"), 'w') as f:
            json.dump(info, f)

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


def load_cc_file(path: str, ver: MAMVersion, platform: Platform) -> CCFile:
    p, f = os.path.split(path)
    csv_path = os.path.join(p, (f+".csv").lower())
    known_files = parse_toc_csv(csv_path)
    id_to_name_lut = {CCFile.get_file_name_hash(k_name.strip()): k_name for k_name, _, _ in known_files}
    cc_file = CCFile(path, id_to_name_lut, ver, platform)
    return cc_file

# ----------------------------------------------------------------------------------------------------------------------
def main():
    # logging.basicConfig(level=logging.WARNING)
    logging.basicConfig(level=logging.ERROR)
    assert CCFile.get_file_name_hash("SPELLS.XEN") == 0x64B2

    #         CLOUDS_INTRO (null, WoXWorld.WoxVariant.CLOUDS),
    #         CLOUDS_WORLD (null, WoXWorld.WoxVariant.CLOUDS),
    #         CLOUDS_CUR (null, WoXWorld.WoxVariant.CLOUDS),
    #         CLOUDS_BOSS (null, WoXWorld.WoxVariant.CLOUDS),
    #         DARK_CC("MM4.PAL", WoXWorld.WoxVariant.DARK_SIDE),
    #         DARK_CUR (null, WoXWorld.WoxVariant.DARK_SIDE),
    #         DARK_SAV (null, WoXWorld.WoxVariant.DARK_SIDE),
    #         DARK_INTRO("DARK.PAL", WoXWorld.WoxVariant.DARK_SIDE),
    #         CLOUDS_CC ("MM4.PAL", WoXWorld.WoxVariant.CLOUDS),
    #         CLOUDS_DAT (null, WoXWorld.WoxVariant.CLOUDS),
    #         CLOUDS_SAV (null, WoXWorld.WoxVariant.CLOUDS),
    #         UNKNOWN ("MM3.PAL", WoXWorld.WoxVariant.UNKNOWN);

    def next_file():
        logging.getLogger().handlers[0].flush()
        time.sleep(0.5)
        print()

    dark_cc = load_cc_file(f"../game_files/dos/DARK.CC",  MAMVersion.DARKSIDE, Platform.PC_DOS)
    # ccf_dark_cc.bootstrap()
    dark_cur = load_cc_file(f"../game_files/dos/DARK.CUR", MAMVersion.DARKSIDE, Platform.PC_DOS)

    mm5_cc = dark_cc.merge(dark_cur)
    mm5_cc.bootstrap()
    mm5_cc.bake()


    # ccf_intro_cc = load_cc_file(f"../game_files/dos/INTRO.CC", MAMVersion.DARKSIDE, Platform.PC_DOS)
    # ccf_xeen_cc =  load_cc_file(f"../game_files/dos/XEEN.CC",  MAMVersion.CLOUDS,   Platform.PC_DOS)
    # ccf_mm3_cc =   load_cc_file("../game_files/dos/MM3.CC",    MAMVersion.MM3,      Platform.PC_DOS)

    # ccf_dark_cc.bake()

    # all_cc_files = [ccf_dark_cc, ccf_intro_cc, ccf_xeen_cc, ccf_mm3_cc]
    # all_cc_files = [ccf_dark_cc]

    # for cc_file in all_cc_files:
    #     cc_file.bake()

if __name__ == '__main__':
    main()
