
import datetime
import json
import os
from os.path import join

from PIL import Image
from slugify import slugify

from chosm.game_constants import AssetTypes


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

class Asset(object):
    def __init__(self, file_id: int, name: str):
        self.file_id = file_id
        if name is None or len(name.strip()) == 0:
            name = f"FILEID_{self.file_id}"
        self.name: str = name
        self.slug = slugify(f"{self.get_type_name()}_{self.name}")
        self.created_timestamp = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    def __str__(self):
        return f"Asset: id={self.file_id}"

    def get_type(self) -> AssetTypes:
        return NotImplemented

    def get_type_name(self):
        return str(self.get_type()).lower()


    def _get_bake_dict(self):
        d = {"id": self.file_id, "name": self.name, "type_name": self.get_type_name(),
             "slug": self.slug, "created": self.created_timestamp}
        return d

    def _gen_preview_image(self, preview_size) -> Image.Image:
        """
        Creates a RGB image preview of the file.
        :return:
        """
        preview_img = Image.new(mode="RGB", size=(preview_size, preview_size), color=(255, 128, 255))

        return preview_img

    def bake(self, file_path):
        """
        Writes the file to a local proxy in a sensible format.
        """
        with open(os.path.join(file_path, "info.json"), 'w') as f:
            json.dump(self._get_bake_dict(), f, indent=2)

        preview_image = self._gen_preview_image(128)
        preview_image.save(join(file_path, "preview.jpg"))

    def __eq__(self, other):
        if isinstance(other, Asset):
            return self.number == other.number and \
                self.file_id == other.file_id and \
                self.created_timestamp == other.created_timestamp
        return NotImplemented

    def __hash__(self):
        return hash((self.file_id, self.name, self.created_timestamp))
