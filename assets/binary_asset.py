import os

from PIL import Image

from assets.asset import Asset
from assets.game_constants import AssetTypes
from helpers import pil_image_helpers as pih


class BinaryAsset(Asset):
    def __init__(self, file_id: int, name: str, data: bytearray):
        super().__init__(file_id, name)
        self.data: bytearray = data

    def __str__(self):
        return f"Binary File: id={self.file_id} len={len(self.data)}"

    def get_type(self) -> AssetTypes:
        return AssetTypes.BINARY

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "bin", bottom_text=f"{len(self.data)//1024}kb")
        return img

    def bake(self, file_path):
        with open(os.path.join(file_path, "data.bin"), 'wb') as f:
            f.write(bytes(self.data))
        super().bake(file_path)

def load_binary_from_baked_folder(folder: str):
    # TODO: implement this
    return NotImplemented
