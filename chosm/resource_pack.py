import datetime
import logging
import os
from dataclasses import dataclass
from os.path import join
import json
import fnmatch
from functools import lru_cache
from typing import Dict, Any, List, Type, Union

from chosm.asset_record import AssetRecord
from chosm.game_constants import AssetTypes, parse_asset_type
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
        ResourcePack meta-data, without asset management stuff.
        used to solve the "info.json" / ResourcePack obj chicken/egg situation.
        Creat this class, if you want to generate an info.json file.
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
    def __init__(self, base_uri):
        super().__init__(None, None, None)
        self._base_uri = base_uri

        # resource management
        self._asset_record_lut: Dict[str: AssetRecord] = {}  # look up table by slug
        self._asset_records_by_type: Dict[AssetTypes, Dict[str, AssetRecord]] = {}

        # inclusions
        self.overrides: List[str]  # archetypes, which act as part of this pack, with this packs names taking priority.
        self.includes: List[str]  # includes which can be used as per: "general_monsters->ice_dragon_027".

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


    def get_sprites(self):
        return self.get_assets_by_type(AssetTypes.SPRITE)

    def __getitem__(self, key) -> Union[AssetRecord, List[AssetRecord]]:
        """
        by example:
            resource_pack["sprite-ice-dragon-027"]
            resource_pack[Sprite, "ice-dragon-027"]
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
        map_ids = world_info["map_identifiers"]
        spell_names = world_info["spell_names"]  # ignore for now
        default_map = world_info["default_map"]
        print(f"found {len(map_ids)} world maps: world=" + name + ", maps=" + ", ".join(map_ids))

        all_maps_by_id = [ma.load_map() for ma in self.get_assets_by_type(AssetTypes.MAP).values()]
        all_maps_by_id = {m.map_identifier: m for m in all_maps_by_id}
        maps = [all_maps_by_id[q] for q in map_ids]

        world = World(name, maps, [], default_map=default_map)

        return world

#
#
#
#
#
#
#
#
#
# class ResourcePack:
#     def __init__(self, base_uri):
#         if not os.path.exists(base_uri):
#             logging.info("Asset Pack Init: error='could not find path'")
#             raise ResourcePackError(None, "base_uri not found")
#         self._base_uri = base_uri
#
#         info_file = join(self._base_uri, "info.json")
#         if not os.path.exists(info_file):
#             raise ResourcePackError(None, "info.json not found")
#
#         self.asset_lut = self.list_assets()
#
#         # load the name for this pack
#         with open(info_file) as f:
#             self.name = json.load(f)["name"]
#
#         logging.info("Asset Pack Init: error=could not find path")
#
#     @lru_cache(maxsize=None)
#     def _get_asset_name(self, info_file_path, st_mtime) -> str:
#         # st_mtime is just there to cause the cache to fail if the modification time changes
#         with open(info_file_path) as f:
#             return json.load(f)["name"]
#
#     @lru_cache(maxsize=None)
#     def get_info(self, resource_name):
#         info_file_path = self.get_asset_path(resource_name)
#         with open(join(info_file_path, "info.json")) as f:
#             return json.load(f)
#
#     def list_sprites(self):
#         return self.list_assets("sprite_*")
#
#     def list_assets(self, glob_exp: str = None) -> Dict[str, str]:
#         dirs = [f.path for f in os.scandir(self._base_uri) if f.is_dir()]
#         info_files = [join(f.path, "info.json") for f in os.scandir(self._base_uri) if f.is_dir()]
#         names = [self._get_asset_name(f, os.stat(f).st_mtime) for f in info_files]
#         if glob_exp is not None:
#             keep_names = set(fnmatch.filter(names, glob_exp))
#             names_and_dirs = {n: d for n, d in zip(names, dirs) if n in keep_names}
#         else:
#             names_and_dirs = {n: d for n, d in zip(names, dirs)}
#         return names_and_dirs
#
#     def list_assets_of_type(self, type_name):
#         # get_info
#         return self.list_assets(type_name + "-*")
#
#     def get_asset_path(self, asset_name):
#         if asset_name not in self.asset_lut:
#             logging.warning(f"Key not found: pack={self.name}, asset_name={asset_name}")
#             # freshen
#             # self.asset_lut = self.list_assets()
#         # let it fail, if key is still not in the lut
#         path = self.asset_lut[asset_name]
#         return path
#
#     def get_resources_type(self, resource_name):
#         path = self.get_asset_path(resource_name)
#         type_name = os.path.split(path)[1].split("-")[0].strip().lower()
#         return type_name
#
#     # def load_resource(self, resource_name) -> MAMFile:
#     #     path = self.get_resource_path(resource_name)
#     #     type_name = self.get_resource_type(resource_name)
#     #
#     #     match type_name:
#     #         case 'sprite':
#     #             return sprite_from_baked_folder(path)
#     #         case "palette":
#     #             return pal_from_baked_folder(path)
#     #     raise ValueError()
#
#     def _is_hidden_file(self, f):
#         # hidden = set(["info.json"])
#         # return f in hidden
#         return False
#
#     def get_resource_files(self, asset_name, glob_exp=None, full_path=False):
#         path = self.get_asset_path(asset_name)
#         assert os.path.isdir(path)
#         files = [f for f in os.listdir(path) if os.path.isfile(join(path, f))]
#         files = [f for f in files if not self._is_hidden_file(f)]
#         if glob_exp is not None:
#             files = list(fnmatch.filter(files, glob_exp))
#
#         files = list(files)
#         files.sort()
#         if full_path:
#             files = [join(path, f) for f in files]
#         return files
#
#     def load_json_file_from_resource(self, resource_name, json_file_name):
#         path = self.get_asset_path(resource_name)
#         assert os.path.isdir(path)
#         file_path = join(path, json_file_name)
#         assert os.path.isfile(file_path)
#         with open(file_path, 'rt') as f:
#             return json.load(f)
#
#     def load_txt_file_from_resource(self, resource_name, file_name, remove_blank_lines=True):
#         path = self.get_asset_path(resource_name)
#         assert os.path.isdir(path)
#         file_path = join(path, file_name)
#         assert os.path.isfile(file_path)
#         with open(file_path, 'rt') as f:
#             lines = f.readlines()
#
#         if remove_blank_lines:
#             lines = [q for q in lines if len(q.strip()) > 0]
#
#         return lines
#
#     def load_map_from_resource(self, resource_name) -> Map:
#         logging.info("load_map_from_resource resource_name={resource_name}")
#         d = self.load_json_file_from_resource(resource_name, "map.json")
#         the_map = load_map_from_dict(d)
#         return the_map
#
#
#
