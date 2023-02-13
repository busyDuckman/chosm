import collections
import fnmatch
import json
import logging
import os
from os.path import join
from threading import Lock
from typing import List, Dict, Any
from chosm.asset import Asset
from chosm.game_constants import AssetTypes, parse_asset_type
from game_engine.map import load_map_from_dict, Map
from helpers.why import Why

import weakref

# AssetRecord:
#   - built for use by the web server
#   - store metadata for the viewer and editor
#   - store a slug representing the folder
#   - validate their own structure
#   - can bootstrap an Asset from primary files

# Asset:
#   - built for use by software creating graphics for the game.
#     - Might and magic asset import scripts
#     - Sprite resize & creation AI
#   - can be created from in memory objects
#   - holds raw data, such as images and sound in memory
#   - can perform operations on the data
#   - can "bake" that data to an asset.
#     - by this process, it will create secondary files from primary files

def _is_hidden_file(folder: str, file_name: str):
    """
    Defines asset files that should not be considered part of the asset.
    eg a ".desktop" file or something appeared.
    """
    return file_name.startswith(".")


class AssetRecord(collections.abc.Mapping):
    def __init__(self, asset_path: str):
        if not os.path.isdir(asset_path):
            raise NotADirectoryError(asset_path)

        # bootstrap from info.json
        self.folder: str = asset_path  # set the path, or self.get_info() won't work

        self.info: Dict[str, Any] = None
        self.file_id: int = None
        self.name: str = None
        self.asset_type: AssetTypes = None
        self.asset_type_as_string = None
        self.created_timestamp: str = None
        self.slug: str = None

        self._file_names: List[str] = None
        self._file_paths: List[str] = None

        self._file_path_by_name: Dict[str, str] = {}

        self._mtime_info = 0
        self._mtime_folder = 0

        self.animations: Dict[str, Dict[str, Any]] = {}
        self.idle_animation: Dict[str, Any] = None

        self._the_map_ref: weakref.ref = None

        self._refresh_lock = Lock()

        self.refresh()

    def refresh(self, forced=False):
        """
        Refresh if anything changed.
        :param forced: Refresh regardless.
        :return: True if a refresh occurred
        """

        with self._refresh_lock:
            mtime_info = os.path.getmtime(join(self.folder, "info.json"))
            mtime_folder = os.path.getmtime(self.folder)

            if forced or mtime_info != self._mtime_info or mtime_folder != self._mtime_folder:
                self.info: Dict[str, Any] = self._read_info_file()
                self.file_id: int = self.info["id"]
                self.name: str = self.info["name"]
                self.asset_type: str = parse_asset_type(self.info["type_name"])
                self.asset_type_as_string = str(self.asset_type)
                self.created_timestamp: str = self.info["created"]
                self.slug: str = self.info["slug"]

                self._file_names: List[str] = None
                self._file_paths: List[str] = None

                self._mtime_info = mtime_info
                self._mtime_folder = mtime_folder

                if "animations" in self.info:
                    self.animations = {}
                    for anim_info in self.info["animations"]:
                        self.animations[anim_info["slug"]] = anim_info

                    if "idle" in self.animations:
                        self.idle_animation = self.animations["idle"]

                return True

            return False

    def _refresh_file_list(self, force=False):
        if self._file_names is None or force:
            with self._refresh_lock:
                self._file_names = [f for f in os.listdir(self.folder) if os.path.isfile(join(self.folder, f))]
                self._file_names = sorted([f for f in self._file_names if not _is_hidden_file(self.folder, f)])
                self._file_paths = [join(self.folder, f) for f in self._file_names]
                self._file_path_by_name: Dict[str, str] = {n: p for n, p in zip(self._file_names, self._file_paths)}

                if len(self._file_names) == 0:
                    logging.error("No files found for asset in path: path='" + self.folder + "'")

    def is_valid(self) -> Why:
        if os.path.split(self.folder)[1] != self.slug:
            return Why.false("slug in info.json was different to folder name.")
        if self.slug.startswith("-"):
            return Why.false("slug starts with a '-'.")
        if not isinstance(self.name, str):
            return Why.false("Name was not a string.")
        if len(self.name.strip()) == 0:
            return Why.false("Name can not be blank.")
        return Why.true()

    def _read_info_file(self) -> Dict[str, str]:
        with open(join(self.folder, "info.json")) as f:
            return json.load(f)

    def __str__(self):
        return "Asset: " + self.slug

    def __eq__(self, other):
        if isinstance(other, AssetRecord):
            return self.number == other.number and \
                self.name == other.name and \
                self.created_timestamp == other.created_timestamp and \
                self.asset_type == other.asset_type
        return NotImplemented

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.name, self.created_timestamp, self.asset_type))

    def get_file_names(self, glob_exp: str = None, refresh_from_disk=False) -> List[str]:
        """
        Get the files (names only) associated with this asset.
        """
        self._refresh_file_list(force=refresh_from_disk)
        if glob_exp is not None:
            return list(fnmatch.filter(self._file_names, glob_exp))
        else:
            return self._file_names

    def get_file_paths(self, glob_exp: str = None, refresh_from_disk=False) -> List[str]:
        """
        Get the files (full path) associated with this asset.
        """
        self._refresh_file_list(force=refresh_from_disk)
        if glob_exp is not None:
            return list(fnmatch.filter(self._file_paths, glob_exp))
        else:
            return self._file_paths

    def get_file_path(self, name: str, refresh_from_disk=False) -> str:
        self._refresh_file_list(force=refresh_from_disk)
        return self._file_path_by_name[name]

    def __getitem__(self, key):
        return self.info[key]

    def __iter__(self):
        return self.info.__iter__()

    def __len__(self):
        return len(self.info)

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

    def load_json_file(self, json_file_name) -> Dict[str, Any]:
        path = join(self.folder, json_file_name)
        assert os.path.isfile(path)
        with open(path, 'rt') as f:
            return json.load(f)

    def load_txt_file_from_resource(self, file_name, remove_blank_lines=True) -> List[str]:
        file_path = join(self.folder, file_name)
        assert os.path.isfile(file_path)
        with open(file_path, 'rt') as f:
            lines = f.readlines()

        if remove_blank_lines:
            lines = [q for q in lines if len(q.strip()) > 0]

        return lines

    def load_asset(self) -> Asset:
        return NotImplemented

    def load_map(self, new_name: str = None) -> Map:
        """
        Loads a map, or returns a cached copy.
        Uses a week reference, so the map if not loaded separately for multiple sessions
        or kept in memory unnecessarily if no sessions are using the map.
        :return:
        """
        # will be none if map has not been loaded yet
        if self._the_map_ref is not None:
            the_map = self._the_map_ref()
            if the_map is not None:
                logging.info("Using cached map: asset = " + self.slug)
                return the_map

        # no existing copy of the map
        logging.info("loading map: asset = " + self.slug)
        d = self.load_json_file("map.json")
        the_map = load_map_from_dict(d)
        if new_name is not None:
            the_map.name = str(new_name)
        self._the_map_ref = weakref.ref(the_map)

        return the_map





