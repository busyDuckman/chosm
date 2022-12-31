import itertools
import json
from os.path import join

from PIL import Image

from chosm.asset import Asset
from chosm.sprite_asset import SpriteAsset
from game_engine.map import Map


class MapAsset(Asset):
    def __init__(self, file_id,
                 name,
                 game_map: Map,
                 tile_set: SpriteAsset
                 ):
        super().__init__(file_id, name)
        self.game_map = game_map
        self.tile_set: SpriteAsset = tile_set

    def __str__(self):
        return f"Palette File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type_name(self):
        return "map"

    def _gen_preview_image(self, preview_size) -> Image.Image:
        return self.gen_2d_map().resize((preview_size, preview_size), Image.NEAREST)

    def gen_2d_map(self):
        w = self.game_map.width * self.tile_set.width
        h = self.game_map.height * self.tile_set.height
        map_img = Image.new("RGB", size=(w, h))

        for x, y in itertools.product(range(self.game_map.width), range(self.game_map.height)):
            x_pos, y_pos = (x * self.tile_set.width, y * self.tile_set.height)
            frame_idx = self.game_map[x, y].idx_ground
            frame = self.tile_set.frames[frame_idx]
            map_img.paste(frame, (x_pos, y_pos), frame)

        return map_img

    def bake(self, file_path):
        super().bake(file_path)

        d = self.game_map.asdict()
        d |= {
            "tileset_slug": self.tile_set.slug,
            "tileset_name": self.tile_set.name,
            }

        with open(join(file_path, "map.json"), "wt") as f:
            json.dump(d, f)


def load_map_from_baked_folder(folder: str):
    # TODO: implement this
    return NotImplemented
