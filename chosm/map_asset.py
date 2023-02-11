import itertools
import json
import logging
from os.path import join
from typing import Dict, Any

from PIL import Image

from chosm.asset import Asset
from chosm.game_constants import AssetTypes
from chosm.sprite_asset import SpriteAsset
from game_engine.map import Map, load_map_from_dict, AssetLut
from helpers.misc import my_json_dumps


class MapAsset(Asset):
    def __init__(self, file_id,
                 name,
                 game_map: Map,
                 ):
        super().__init__(file_id, name)
        self.game_map: Map = game_map
        self.luts_by_name: dict[str, dict[Any, SpriteAsset]] = {}

    def set_luts(self, luts: dict[str, dict[Any, SpriteAsset]]):
        """
        Sets the sprites indexed by the map.
        :param luts: look out tables, by layer name. {layer_name: {index: sprite}}
        :return:
        """
        self.luts_by_name = luts

        # create the datatable that the server will use
        asset_record_luts = [AssetLut(name, {i: q.slug if q is not None else None
                                             for i, q in lut.items()}) for name, lut in luts.items()]
        self.game_map.set_luts(asset_record_luts)

    def __str__(self):
        return f"Palette File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type(self) -> AssetTypes:
        return AssetTypes.MAP

    def _gen_preview_image(self, preview_size) -> Image.Image:
        return self.gen_2d_map().resize((preview_size, preview_size), Image.NEAREST)

    def gen_2d_map(self):
        some_tile = next(s for s in self.luts_by_name["ground-map"].values() if s is not None)
        tile_w = some_tile.width
        tile_h = some_tile.height
        total_w = self.game_map.width * tile_w
        total_h = self.game_map.height * tile_h
        map_img = Image.new("RGB", size=(total_w, total_h))

        for x, y in itertools.product(range(self.game_map.width), range(self.game_map.height)):
            for layer_name in ["ground", "env", "building"]:
                x_pos, y_pos = (x * tile_w, y * tile_h)
                sprite_idx = self.game_map[x, y, layer_name]

                tile_name = layer_name + "-map"
                if tile_name in self.luts_by_name:
                    image_lut = self.luts_by_name[tile_name]

                    if sprite_idx in image_lut:
                        sprite = image_lut[sprite_idx]
                        # sprite might be none, indicating nothing there
                        if sprite is not None:
                            frame = sprite.frames[0] # just get the first frame
                            map_img.paste(frame, (x_pos, y_pos), frame)
                    # else:
                    #     logging.error("map idx no in sprite lut")

                # if layer_name == "ground" or frame_idx != 0:
                    # frames = self.game_map[layer_name]
                    # frame = frames[frame_idx % len(frames)]
                    # frame = self.luts_by_name[layer_name].
                    # map_img.paste(frame, (x_pos, y_pos), frame)

        return map_img

    def bake(self, file_path):
        super().bake(file_path)

        d = self.game_map.asdict()
        # layer_info = {k: {"slug": v.slug, "name": v.name} for k, v in self.layers.items()}
        # d |= {"layer_sprites": layer_info}

        with open(join(file_path, "map.json"), "wt") as f:
            f.write(my_json_dumps(d))
            # json.dump(d, f, indent=2)


# def load_map_from_baked_folder(folder: str):
#     logging.info("loading MapAsset: path = " + folder)
#     with open(join(folder, "info.json"), "r") as f:
#         info = json.load(f)
#
#     with open(join(folder, "map.json"), "r") as f:
#         map_info = json.load(f)
#
#     the_map = load_map_from_dict(map_info)
#     file_id = int(info["id"])
#     name = str(info["name"])
#     # TODO
#     #return MapAsset(file_id, name, the_map, layers)
#     return NotImplemented
