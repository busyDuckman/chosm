import datetime
import logging
import os
import pathlib
from dataclasses import dataclass
from itertools import chain
from os.path import join
import json
import fnmatch
from functools import lru_cache
from typing import Dict, Any, List, Type, Union, Literal

from slugify import slugify

from assets.asset_record import AssetRecord
from assets.game_constants import AssetTypes, parse_asset_type
from game_engine.map import Map, load_map_from_dict
from game_engine.world import World
from helpers.misc import popo_to_dict, popo_from_dict


class ResourcePackError(Exception):
    def __init__(self, pack_name, error_msg, **kwargs):
        msg = "ResourcePackError -> " + str(error_msg)
        info = ""
        if pack_name is not None:
            info += " pack_name = " + pack_name
        info = ", ".join([str(k) + "=" + ResourcePackError.quote_as_needed(v) for k, v in kwargs.items()])
        if len(info) > 0:
            msg += ": " + info

        super().__init__(msg)

    @staticmethod
    def quote_as_needed(value):
        s = str(value)
        if isinstance(value, str) or any(c.isspace() for c in s):
            return '"' + str(value) + '"'
        return s


class ResourcePackInfo:
    def __init__(self, name: str, admin_username: str, creative_commons: bool):
        """
        ResourcePack meta-data, without asset management code.

        This is the base class for ResourcePack, but the inheritance is not done for classical OOP purposes.
        As a ResourcePack can only be loaded from "info.json"; this class is used to
        solve the "info.json" / "ResourcePack instance" chicken/egg situation.
        """
        self.name = name
        self.admin_username: str = admin_username
        self.author_info: str = "anon"
        self.creative_commons: bool = creative_commons
        self.is_private: bool = False
        self.editor_access_list: List[str] = []
        self.viewer_access_list: List[str] = []
        self.ver: str = "0.1"
        self.description: str = None
        self.created_timestamp: str = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        # inclusions
        self.overrides: List[str] = []  # archetypes, which act as part of this pack, with this packs names taking priority.
        self.includes: List[str]  = []  # includes which can be used as per: "general_monsters->ice_dragon_027".

    def save_info_file(self, base_uri):
        d = popo_to_dict(self)
        info_file = join(base_uri, "info.json")

        with open(info_file, "wt") as f:
            json.dump(d, f, indent=2)

    def load_info_file(self, base_uri):
        info_file = join(base_uri, "info.json")
        if not os.path.exists(info_file):
            raise ResourcePackError(None, "info.json not found")

        with open(info_file, "rt") as f:
            d = json.load(f)

        popo_from_dict(self, d)


class ResourcePack(ResourcePackInfo):
    """
    A resource pack is a folder with an "info.json" and subdirectories that contain game assets.
    This class is the logic of retrieving assets from such a folder.

    This class is intended to be memory resident on a running game server. As such it is a tool for accessing asset
    metadata and file locations.

    It maps either a slug, or a (AssetTypes, name) pair, to a AssetRecord that represents asset data in a subdirectory.

    By example:
      resource_pack["sprite-ice-dragon-027"]
      resource_pack[AssetTypes.SPRITE, "ice-dragon-027"]

    TODO: override and include are just stubs for now.
    Resource Packs can interact with each other in two ways:
      - override: A slug not present in this pack will map to the slug in the pack being overriden.
      - include:  A special @ slug redirects to the named resource pack.
                  eg: "sprite-ice-dragon-027@stock_dragons"
                  Note: if stock_dragons overrides another class, the include carries through as you would expect.
    """
    def __init__(self, base_uri):
        super().__init__(None, None, None)
        self._base_uri = base_uri

        # resource management
        self._asset_record_lut: Dict[str: AssetRecord] = {}  # look up table by slug
        self._asset_records_by_type: Dict[AssetTypes, Dict[str, AssetRecord]] = {}

        self._overrides: List[ResourcePack] = []
        self._includes: List[ResourcePack] = []

        # know when to refresh
        self._mtime_info = 0
        self._mtime_folder = 0

        # load
        self._reload_info_and_assets()

    def link_dependencies(self, other_resource_packs: Dict[str, Any]):
        self._overrides: List[ResourcePack] = [other_resource_packs[p] for p in self.overrides]
        self._includes:  List[ResourcePack] = [other_resource_packs[p] for p in self.includes]

    def _reload_info_and_assets(self):
        if not os.path.exists(self._base_uri):
            logging.info("Asset Pack reload: error='could not find path'")
            raise ResourcePackError(None, "base_uri not found")
        self._mtime_folder = os.path.getmtime(self._base_uri)

        self.load_info_file(self._base_uri)
        self._mtime_info = os.path.getmtime(join(self._base_uri, "info.json"))

        dirs = [f.path for f in os.scandir(self._base_uri) if f.is_dir()]
        self._asset_record_lut = {}

        for folder in dirs:
            info_file = join(folder, "info.json")
            if not os.path.isfile(info_file):
                logging.error("Asset missing info file at: "+ info_file)
                continue

            r = AssetRecord(folder)
            valid = r.is_valid()
            if not valid:
                logging.error("Asset not valid: " + valid.why)
                continue

            self._asset_record_lut[r.slug] = r

        self._asset_records_by_type = {t: {q.name: q for q in self._asset_record_lut.values() if q.asset_type == t}
                                       for t in AssetTypes}

    def refresh(self, forced: bool, other_resource_packs: Dict[str, Any]):
        mtime_info = os.path.getmtime(join(self._base_uri, "info.json"))
        mtime_folder = os.path.getmtime(self._base_uri)

        if forced or mtime_info != self._mtime_info or mtime_folder != self._mtime_folder:
            self._reload_info_and_assets()
            self.link_dependencies(other_resource_packs)
            self._mtime_info = mtime_info
            self._mtime_folder = mtime_folder
        else:
            # This will cause all assets to natural refresh if a file changed.
            for name, asset in self._asset_record_lut.items():
                asset.refresh()

            # TODO: what is the criterion for a natural refresh.
            # TODO: new / missing folders
            # TODO, asset may have changed names (and now be in the wrong folder)
            # if not valid:
            #     logging.error("Asset not valid: " + valid.why)
            #     continue


    def get_asset_by_slug(self, slug: str) -> AssetRecord:
        return self._asset_record_lut[slug]

    def get_asset_by_name(self, asset_type: Union[AssetTypes, str], name: str) -> AssetRecord:
        if isinstance(asset_type, str):
            asset_type = parse_asset_type(asset_type)
        return self.get_assets_by_type(asset_type)[name]

    def get_assets_by_type(self, asset_type: AssetTypes, glob_exp: str=None) -> Dict[str, AssetRecord]:
        """
        eg:
            rm.get_assets_by_type(Sprite)["ice-dragon-027"]
            rm.get_assets_by_type(Sprite, "*dragon*")
        """
        if glob_exp is not None:
            rec_by_type = self._asset_records_by_type[asset_type]
            return {k: v for k, v in rec_by_type.items() if fnmatch.fnmatch(k, glob_exp)}
        else:
            return self._asset_records_by_type[asset_type]

    def get_assets(self, glob_exp: str = None) -> Dict[str, AssetRecord]:
        """
        Gets assets in the resource pack.
        :param glob_exp:
        :return: { slug: AssetRecord, ... }
        """
        if glob_exp is None:
            return self._asset_record_lut
        else:
            return {k: v for k, v in self._asset_record_lut.items() if fnmatch.fnmatch(k, glob_exp)}

    def get_sprites(self) -> Dict[str, AssetRecord]:
        return self.get_assets_by_type(AssetTypes.SPRITE)

    def get_sprites_for_map(self, map_name) -> List[AssetRecord]:
        the_map: Map = self[AssetTypes.MAP, map_name].load_map()
        sprite_slugs = set(chain(*[lut.values() for lut in the_map.luts]))
        return [s for s in self.get_sprites().values() if s.slug in sprite_slugs]


    def __getitem__(self, key) -> Union[AssetRecord, List[AssetRecord]]:
        """
        by example:
            resource_pack["sprite-ice-dragon-027"]
            resource_pack[AssetTypes.SPRITE, "ice-dragon-027"]
        """
        if isinstance(key, str):
            # key is a  slug
            return self.get_asset_by_slug(key)
        elif isinstance(key, AssetTypes):
            return self.get_assets_by_type(key)
        else:
            asset_type, asset_name = key
            return self.get_asset_by_name(asset_type, asset_name)


    def __iter__(self):
        for asset_rec in self._asset_record_lut.values():
            yield asset_rec

    def __len__(self):
        return len(self._asset_record_lut)

    def __contains__(self, item):
        return item in self.info

    def keys(self):
        return self.info.keys()

    def items(self):
        return self.info.items()

    def values(self):
        return self.info.values()

    def get(self, key):
        return self.info.get(key)

    def get(self, key, default):
        return self.info.get(key, default)

    # I think this is overthinking things
    # def get_map(self, name):
        # self._cached_maps: Dict[str, Map] = {}
        # map_asset = self[AssetTypes.MAP, name]
        # if map_asset.refresh(forced=False):
        #     logging.info("map was changed on disk, reloading: map=" + name)
        #     new_map = map_asset.load_map()
        #     self._cached_maps[name] = new_map
        #
        # return self._cached_maps[name]

    # def generate_all_css(self):
    #     """
    #     Creates a css file linking to the css code for all assets in this resource pack.
    #
    #     There hare hundreds of .css files (one per game sprite, because the animation is done in css).
    #     Embedding in theo .html response just the .css files needed to render a scene would burden the
    #     server with extra work and lengthen the html response creating bandwidth overhead. It's also
    #     complicates the html template logic, to try and figure out all used assets prior
    #     to rendering, just to build a list of .css imports.
    #
    #     This function creates a single .css file that has everything in this asset pack bundled into it.
    #     :return:
    #     """
    #
    #     # TODO: handle included and overriden files
    #     # TODO: need a common way to included and overriden files without circular loops.
    #
    #     sprites = self.get_assets_by_type(AssetTypes.SPRITE)
    #     css_files = [sprite.get_file_path("_animation.css") for sprite in sprites.values()]
    #     # css_files = [str(pathlib.Path(f).absolute()) for f in css_files]
    #     # f"/download/resource-packs/{pack_name}/by_type/{asset_type}/by_name/{asset_name}/{file_name}"
    #     print(css_files[0])
    #     import_statements = [f'@import "{f}";' for f in css_files]
    #
    #     css = f"<!-- All sprite animations in the {slugify(self.name)} resource pack -->\n\n"
    #     css += "\n".join(import_statements)
    #     css += "\n"
    #
    #     return css

    def get_modification_time(self) -> datetime.datetime:
        # TODO: This may not work for an updated asset.
        #       It needs to be properly tested
        ts = max(self._mtime_info, self._mtime_folder)
        if ts == 0:
            # timestamp unknown
            logging.error(f"NO MODIFICATION TIMESTAMP FOR ASSET PACK: pack={slugify(self.name)}")
            return datetime.datetime.now()

        return datetime.datetime.fromtimestamp(ts)

    def get_worlds(self):
        return self.get_assets_by_type(AssetTypes.WORLD)

    def load_world(self, world_name):
        """
        Loading a world is done here, because it draws together multiple assets.
        :param world_name:
        :return:
        """
        logging.info("loading map: name = " + world_name)
        world_ar = self[AssetTypes.WORLD, world_name]

        world_info = world_ar.load_json_file("world_info.json")
        name = world_info["world_name"]
        map_ids = world_info["map_names"]
        spell_names = world_info["spell_names"]  # ignore for now
        default_map = world_info["default_map"]
        print(f"found {len(map_ids)} world maps: world=" + name + ", maps=" + ", ".join(map_ids))

        all_maps_by_id = [ma.load_map(new_name=ma.name) for ma in self.get_assets_by_type(AssetTypes.MAP).values()]
        all_maps_by_id = {m.name: m for m in all_maps_by_id}
        maps = [all_maps_by_id[q] for q in map_ids]

        world = World(name, maps, [], default_map=default_map)

        return world


def create_new_pack(base_folder: str, pack_name):
    logging.info("Creating resource pack: " + pack_name)
    pack_slug = slugify(pack_name)
    pack_folder = join(base_folder, pack_slug)