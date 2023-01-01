import datetime
import json
import os
import time
from functools import lru_cache
from os.path import join
from typing import List, Dict

from PIL import Image
from slugify import slugify

from chosm.asset import Asset


# AssetRecord:
#   - built for use by the web server
#   - store metadata for the viewer and editor
#   - store a slug representing the folder
#   - stack to override each other
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

class AssetRecord(object):
    def __init__(self, asset_path: str):
        if not os.path.isdir(asset_path):
            raise NotADirectoryError(asset_path)

        # bootstrap from info.json
        self.asset_dir: str = asset_path  # set the path, or self.get_info() won't work
        info: Dict = self.get_info()
        self.file_id = info["id"]
        self.name = info["name"]
        self.type_name = info["type"]
        self.created_timestamp = info["created"]
        # self.slug = info["slug"]

        if self.name is None or len(self.name.strip()) == 0:
            name = f"FILEID_{self.file_id}"
        self.slug = self._get_slug()

    def is_folder_valid(self):
        return os.path.split(self.asset_dir)[1] == self.slug

    def _get_slug(self):
        return slugify(f"{self.get_type_name()}_{self.name}")

    @lru_cache(maxsize=None)
    def get_info(self):
        with open(join(self.asset_dir, "info.json")) as f:
            return json.load(f)

    def __str__(self):
        return "Asset: " + self.slug

    def __eq__(self, other):
        if isinstance(other, AssetRecord):
            return self.number == other.number and \
                self.file_id == other.file_id and \
                self.created_timestamp == other.created_timestamp and \
                self.type_name == other.type_name
        return NotImplemented

    def __hash__(self):
        return hash((self.file_id, self.name, self.created_timestamp, self.type_name))

    def create_holder(self) -> Asset:
        pass




