import json
import os
from typing import List

from PIL import Image

from chosm.asset import Asset
from helpers.color import Color
from mam_game.mam_constants import MAMFileParseError


class PalAsset(Asset):
    def __init__(self, file_id: int, name: str, pal: List[Color]):
        super().__init__(file_id, name)
        if len(pal) != 256:
            raise MAMFileParseError(file_id, name, "Must be 256 colors in a palette")
        self.colors: List[Color] = pal.copy()
        self.colors_rgb = [tuple(c.as_array()) for c in self.colors]

    def __str__(self):
        return f"Palette File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type_name(self):
        return "palette"

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(16, 16))
        for y in range(16):
            for x in range(16):
                img.putpixel((x, y), self.colors_rgb[y*16 + x])
        return img.resize((preview_size, preview_size), Image.NEAREST)

    def bake(self, file_path):
        with open(os.path.join(file_path, "pal.json"), 'w') as f:
            json.dump(self.colors_rgb, f)

        # with open(os.path.join(file_path, "html_cols.pal"), 'wt') as f:
        #     txt = "\n".join([c.as_html() for c in self.colors])
        #     f.write(txt)
        super().bake(file_path)


def pal_from_baked_folder(folder: str):
    with open(os.path.join(folder, "info.json"), "r") as f:
        info = json.load(f)
    with open(os.path.join(folder, "pal.json"), "r") as f:
        pal_info = json.load(f)
        pal = [Color(c[0], c[1], c[2]) for c in pal_info]

    file_id = int(info["id"])
    name = int(info["name"])
    t = int(info["type"])
    return PalAsset(file_id, name, pal)
