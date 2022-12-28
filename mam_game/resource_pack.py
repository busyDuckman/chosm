import os
from enum import Enum
from os.path import join
import json
import fnmatch
from functools import lru_cache
from typing import Dict

from mam_game.mam_file import MAMFile
from mam_game.pal_file import pal_from_baked_folder
from mam_game.sprite_file import sprite_from_baked_folder


class ResourcePack:
    def __init__(self, base_uri):
        self._base_uri = base_uri
        self.resource_lut = self.list_resources()

        with open(join(self._base_uri, "info.json")) as f:
            self.name = json.load(f)["name"]

    @lru_cache(maxsize=None)
    def _get_resource_name(self, info_file_path, st_mtime) -> str:
        # st_mtime is just there to cause the cache to fail if the modification time changes
        with open(info_file_path) as f:
            return json.load(f)["name"]

    @lru_cache(maxsize=None)
    def get_info(self, resource_name):
        info_file_path = self.get_resource_path(resource_name)
        with open(join(info_file_path, "info.json")) as f:
            return json.load(f)


    def list_sprites(self):
        return self.list_resources("sprite_*")

    def list_resources(self, glob_exp: str = None) -> Dict[str, str]:
        dirs = [f.path for f in os.scandir(self._base_uri) if f.is_dir()]
        info_files = [join(f.path, "info.json") for f in os.scandir(self._base_uri) if f.is_dir()]
        names = [self._get_resource_name(f, os.stat(f).st_mtime) for f in info_files]
        if glob_exp is not None:
            keep_names = set(fnmatch.filter(names, glob_exp))
            names_and_dirs = {n: d for n, d in zip(names, dirs) if n in keep_names}
        else:
            names_and_dirs = {n: d for n, d in zip(names, dirs)}
        return names_and_dirs

    def get_resource_path(self, resource_name):
        if resource_name not in self.resource_lut:
            # freshen
            self.resource_lut = self.list_resources()
        # let it fail, if key is still not in the lut
        path = self.resource_lut[resource_name]
        return path

    def get_resource_type(self, resource_name):
        path = self.get_resource_path(resource_name)
        type_name = os.path.split(path)[1].split("-")[0].strip().lower()
        return type_name

    def load_resource(self, resource_name) -> MAMFile:
        path = self.get_resource_path(resource_name)
        type_name = self.get_resource_type(resource_name)

        match type_name:
            case 'sprite':
                return sprite_from_baked_folder(path)
            case "palette":
                return pal_from_baked_folder(path)
        raise ValueError()

    def _is_hidden_file(self, f):
        hidden = set(["info.json"])
        return f in hidden

    def get_resource_files(self, resource_name, glob_exp=None, full_path=False):
        path = self.get_resource_path(resource_name)
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

