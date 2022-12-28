import os
from typing import List
import json

from PIL import Image

from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError
from mam_game.mam_file import MAMFile
import helpers.pil_image_helpers as pih


class BinaryFile(MAMFile):
    def __init__(self, file_id: int, name: str, data: bytearray):
        super().__init__(file_id, name)
        self.data: bytearray = data

    def __str__(self):
        return f"Binary File: id={self.file_id} len={len(self.data)}"

    def get_type_name(self):
        return "binary"

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "bin", bottom_text=f"{len(self.data)//1024}kb")
        return img

    def bake(self, file_path):
        with open(os.path.join(file_path, "data.bin"), 'wb') as f:
            f.write(bytes(self.data))
        super().bake(file_path)


def load_bin_file(file_id: int, name: str, data: List,
                  ver: MAMVersion, platform: Platform) -> BinaryFile:
    if len(data) == 0:
        raise MAMFileParseError(file_id, name, "Binary file was empty")

    return BinaryFile(file_id, name, bytearray(data))
