import logging
import os
from os.path import join
import json
import fnmatch
from functools import lru_cache
from typing import Dict

from game_engine.map import Map, load_map_from_dict

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


class ResourcePack:
    def __init__(self, base_uri):
        if not os.path.exists(base_uri):
            logging.info("Asset Pack Init: error='could not find path'")
            raise ResourcePackError(None, "base_uri not found")
        self._base_uri = base_uri

        info_file = join(self._base_uri, "info.json")
        if not os.path.exists(info_file):
            raise ResourcePackError(None, "info.json not found")

        self.asset_lut = self.list_assets()

        # load the name for this pack
        with open(info_file) as f:
            self.name = json.load(f)["name"]

        logging.info("Asset Pack Init: error=could not find path")

    @lru_cache(maxsize=None)
    def _get_asset_name(self, info_file_path, st_mtime) -> str:
        # st_mtime is just there to cause the cache to fail if the modification time changes
        with open(info_file_path) as f:
            return json.load(f)["name"]

    @lru_cache(maxsize=None)
    def get_info(self, resource_name):
        info_file_path = self.get_asset_path(resource_name)
        with open(join(info_file_path, "info.json")) as f:
            return json.load(f)

    def list_sprites(self):
        return self.list_assets("sprite_*")

    def list_assets(self, glob_exp: str = None) -> Dict[str, str]:
        dirs = [f.path for f in os.scandir(self._base_uri) if f.is_dir()]
        info_files = [join(f.path, "info.json") for f in os.scandir(self._base_uri) if f.is_dir()]
        names = [self._get_asset_name(f, os.stat(f).st_mtime) for f in info_files]
        if glob_exp is not None:
            keep_names = set(fnmatch.filter(names, glob_exp))
            names_and_dirs = {n: d for n, d in zip(names, dirs) if n in keep_names}
        else:
            names_and_dirs = {n: d for n, d in zip(names, dirs)}
        return names_and_dirs

    def get_asset_path(self, asset_name):
        if asset_name not in self.asset_lut:
            logging.warning(f"Key not found: pack={self.name}, asset_name={asset_name}")
            # freshen
            # self.asset_lut = self.list_assets()
        # let it fail, if key is still not in the lut
        path = self.asset_lut[asset_name]
        return path

    def get_resource_type(self, resource_name):
        path = self.get_asset_path(resource_name)
        type_name = os.path.split(path)[1].split("-")[0].strip().lower()
        return type_name

    # def load_resource(self, resource_name) -> MAMFile:
    #     path = self.get_resource_path(resource_name)
    #     type_name = self.get_resource_type(resource_name)
    #
    #     match type_name:
    #         case 'sprite':
    #             return sprite_from_baked_folder(path)
    #         case "palette":
    #             return pal_from_baked_folder(path)
    #     raise ValueError()

    def _is_hidden_file(self, f):
        # hidden = set(["info.json"])
        # return f in hidden
        return False

    def get_resource_files(self, asset_name, glob_exp=None, full_path=False):
        path = self.get_asset_path(asset_name)
        assert os.path.isdir(path)
        files = [f for f in os.listdir(path) if os.path.isfile(join(path, f))]
        files = [f for f in files if not self._is_hidden_file(f)]
        if glob_exp is not None:
            files = list(fnmatch.filter(files, glob_exp))

        files = list(files)
        files.sort()
        if full_path:
            files = [join(path, f) for f in files]
        return files

    def load_json_file_from_resource(self, resource_name, json_file_name):
        path = self.get_asset_path(resource_name)
        assert os.path.isdir(path)
        file_path = join(path, json_file_name)
        assert os.path.isfile(file_path)
        with open(file_path, 'rt') as f:
            return json.load(f)

    def load_txt_file_from_resource(self, resource_name, file_name, remove_blank_lines=True):
        path = self.get_asset_path(resource_name)
        assert os.path.isdir(path)
        file_path = join(path, file_name)
        assert os.path.isfile(file_path)
        with open(file_path, 'rt') as f:
            lines = f.readlines()

        if remove_blank_lines:
            lines = [q for q in lines if len(q.strip()) > 0]

        return lines

    def load_map_from_resource(self, resource_name) -> Map:
        logging.info("load_map_from_resource resource_name={resource_name}")
        d = self.load_json_file_from_resource(resource_name, "map.json")
        the_map = load_map_from_dict(d)
        return the_map


