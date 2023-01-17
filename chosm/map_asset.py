import itertools
import json
import logging
from os.path import join
from typing import Dict

from PIL import Image

from chosm.asset import Asset
from chosm.game_constants import AssetTypes
from chosm.sprite_asset import SpriteAsset
from game_engine.map import Map, load_map_from_dict


class MapAsset(Asset):
    def __init__(self, file_id,
                 name,
                 game_map: Map,
                 layers: Dict[str, SpriteAsset]
                 ):
        super().__init__(file_id, name)
        self.game_map: Map = game_map
        self.layers: Dict[str, SpriteAsset] = layers

    def __str__(self):
        return f"Palette File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type(self) -> AssetTypes:
        return AssetTypes.MAP

    def _gen_preview_image(self, preview_size) -> Image.Image:
        return self.gen_2d_map().resize((preview_size, preview_size), Image.NEAREST)

    def gen_2d_map(self):
        some_tile = list(self.layers.values())[0]
        tile_w = some_tile.width
        tile_h = some_tile.height
        total_w = self.game_map.width * tile_w
        total_h = self.game_map.height * tile_h
        map_img = Image.new("RGB", size=(total_w, total_h))

        for x, y in itertools.product(range(self.game_map.width), range(self.game_map.height)):
            for layer_name in ["ground", "env", "building"]:
                x_pos, y_pos = (x * tile_w, y * tile_h)
                frame_idx = self.game_map[x, y, layer_name]

                if layer_name == "ground" or frame_idx != 0:
                    frames = self.layers[layer_name].frames
                    frame = frames[frame_idx % len(frames)]
                    map_img.paste(frame, (x_pos, y_pos), frame)

        return map_img

    def bake(self, file_path):
        super().bake(file_path)

        d = self.game_map.asdict()
        layer_info = {k: {"slug": v.slug, "name": v.name} for k, v in self.layers.items()}
        d |= {"layer_sprites": layer_info}

        with open(join(file_path, "map.json"), "wt") as f:
            json.dump(d, f, indent=2)


def load_map_from_baked_folder(folder: str):
    logging.info("loading MapAsset: path = " + folder)
    with open(join(folder, "info.json"), "r") as f:
        info = json.load(f)

    with open(join(folder, "map.json"), "r") as f:
        map_info = json.load(f)

    the_map = load_map_from_dict(map_info)
    file_id = int(info["id"])
    name = str(info["name"])
    # TODO
    #return MapAsset(file_id, name, the_map, layers)
    return NotImplemented
