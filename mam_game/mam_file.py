import datetime
import json
import os
import time
from os.path import join
from typing import List

from PIL import Image
from slugify import slugify


class MAMFile(object):
    def __init__(self, file_id: int, name: str):
        self.file_id = file_id
        if name is None or len(name.strip()) == 0:
            name = f"FILEID_{self.file_id}"
        self.name: str = name
        self.slug = slugify(f"{self.get_type_name()}_{self.name}")
        self.created_timestamp = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    def __str__(self):
        return f"MAM File: id={self.file_id}"

    def get_type_name(self):
        "mamfile"

    def _get_bake_dict(self):
        d = {"id": self.file_id, "name": self.name, "type": self.get_type_name(),
             "slug": self.slug,  "created": self.created_timestamp}
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

        preview_image = self._gen_preview_image(64)
        preview_image.save(join(file_path, "preview.jpg"))


