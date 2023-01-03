import copy
import itertools
from typing import List

from chosm.map_asset import MapAsset
from game_engine.map import Map, Tile
from mam_game.mam_constants import Direction, MAMVersion, Platform, MAMFileParseError
from mam_game.map_file_decoder import MAMMapAsset


def organise_maps(joined_maps: List[MAMMapAsset]):
    joined_maps_by_id = {m.file_id: m for m in joined_maps}
    top_left_maps = [m for m in joined_maps if m.is_top_left()]

    organised = []
    for tl_map in top_left_maps:
        sorted_maps = []
        width, height = 0, 0
        for y, left_most in enumerate(tl_map.walk(joined_maps_by_id, Direction.SOUTH)):
            height = max(y + 1, height)
            for x, sub_map in enumerate(left_most.walk(joined_maps_by_id, Direction.EAST)):
                width = max(x + 1, width)
                sub_map.map_pos_x = x
                sub_map.map_pos_y = y
                sorted_maps.append(sub_map)
        organised.append((sorted_maps, width, height))

    return organised


def to_single_map(sorted_maps: List[MAMMapAsset], width_super_map, height_super_map) -> MAMMapAsset:
    sub_map_width, sub_map_height = sorted_maps[0].game_map.size()
    if not all(m.game_map.size() == (sub_map_width, sub_map_height) for m in sorted_maps):
        raise MAMFileParseError(None, "attempt to merge maps of different size")

    if len(sorted_maps) != width_super_map * height_super_map:
        raise MAMFileParseError(None, f"can't merge maps, wrong amount of maps."
                                      f" expected={len(sorted_maps)}, present={width_super_map * height_super_map}")

    # just use the attributes from the top left. for now
    # TODO: Does this shortcut (assuming all maps have the ame attributes) matter?
    merged_map = copy.copy(sorted_maps[0])
    gm = merged_map.game_map
    merged_map.game_map = Map(width_super_map * sub_map_width, height_super_map * sub_map_height,
                              gm.num_layers, gm._layer_names)

    for sub_map in sorted_maps:
        # if sub_map.map_pos_x != 0:
        #     continue
        for x_sub_map, y_sub_map, in itertools.product(range(sub_map_width), range(sub_map_height)):

            x_merged_map = sub_map.map_pos_x*sub_map_width + x_sub_map
            y_merged_map = sub_map.map_pos_y*sub_map_height + y_sub_map

            tile = sub_map.game_map[x_sub_map, y_sub_map]
            merged_map.game_map[x_merged_map, y_merged_map] = tile

    return merged_map


def combine_map_assets(map_assets: List[MAMMapAsset],
                       ver: MAMVersion,
                       platform: Platform) -> List[MapAsset]:
    organised = organise_maps(map_assets)
    single_maps = []
    for sorted_maps, width, height in organised:
        print("combining map map:", width, height)
        single_map = to_single_map(sorted_maps, width, height)
        single_maps.append(single_map)

    return single_maps