import json
import os

from PIL import Image

from assets.asset import Asset
from assets.game_constants import AssetTypes
from game_engine.world import World

import helpers.pil_image_helpers as pih


class WorldAsset(Asset):
    def __init__(self, file_id: int, name: str, world: World):
        super().__init__(file_id, name)
        self.world = world

    def __str__(self):
        return f"Palette File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type(self) -> AssetTypes:
        return AssetTypes.WORLD

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "World", bottom_text=f"n={len(self.world._maps)}")
        return img

    def bake(self, file_path):
        d = self.world.as_dict()

        with open(os.path.join(file_path, "world_info.json"), 'wt') as f:
            json.dump(d, f, indent=2)

        super().bake(file_path)
