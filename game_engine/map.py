import copy
import itertools
from dataclasses import dataclass, asdict
from enum import Enum, IntFlag
from typing import Dict, Tuple, List

import numpy as np

from game_engine.why import Why
from helpers.archetyped_table import ArchetypedTable, InstanceTable, DifferenceTable
from mam_game.mam_constants import Direction


#
# class TileFlags(IntFlag):
#     FACE_N:    0b0000_0000
#     FACE_S:    0b0000_0001
#     FACE_E:    0b0000_0010
#     FACE_W:    0b0000_0011
#     BLOCKED:   0b0000_0100
#
#
# @dataclass
# class Tile:
#     idx_ground:   int
#     idx_object:   int
#     flags:        TileFlags
#     height:       int
#     idx_map_tile: int
#     idx_map_icon: int


# class Tile:
#     def __init__(self, height, *kwargs):
#         self.height: int = height
#         self.layers: List[int] = list(kwargs)
#
#     def asdict(self):
#         return {
#             "height": self.height,
#             "layers": self.layers
#         }

# ["ground", "object", "map_tile", "map_icon"]

class Map:
    # a grid based map
    def __init__(self, map_identifier, w, h, num_layers, layer_names=None):
        if num_layers <= 0:
            raise ValueError("numer of layers must be > 0")

        self.map_identifier = str(map_identifier)
        self.num_layers = num_layers
        self.width: int = w
        self.height: int = h
        if layer_names is None:
            self.layer_names = tuple([f"layer_{i:02d}" for i in range(num_layers)])
        else:
            if len(layer_names) != num_layers:
                raise ValueError("numer of layer names != number of layers")
            ln = copy.copy(layer_names)  # TODO: do I want to normalise they layer names?
            self.layer_names = tuple(ln)

        self._map: DifferenceTable = ArchetypedTable({n: 0 for n in layer_names}, self.width * self.height)

    def recompress_map(self):
        self._map = ArchetypedTable(self._map, lru_cache_size=self._map.lru_cache_size)

    def size(self):
        return self.width, self.height

    @property
    def layer_names(self):
        return copy.copy(self._layer_names)

    @layer_names.setter
    def layer_names(self, value):
        self._layer_names = value
        self._layer_lut = {n: i for i, n in enumerate(self._layer_names)}

    def __getitem__(self, pos):
        if len(pos) == 2:
            x, y = pos
            return self._map[y * self.width + x]
        if len(pos) == 3:
            x, y, layer_name = pos
            return self._map[y * self.width + x, layer_name]
        raise KeyError()

        # if len(pos) == 2:
        #     x, y = pos
        #     return self._map[y * self.width + x]
        # if len(pos) == 3:
        #     x, y, layer_name = pos
        #     layer_num = self._layer_lut[layer_name]
        #     return self._map[y * self.width + x].layers[layer_num]

    def __setitem__(self, pos, value):
        x, y = pos
        self._map[y * self.width + x] = value

    def __iter__(self):
        for x, y in itertools.product(range(self.width), range(self.height)):
            yield x, y, self._map[y * self.width + x]

    def __len__(self):
        return self.width * self.height

    def asdict(self):
        d = {"map_identifier": self.map_identifier,
             "width": self.width,
             "height": self.height,
             "num_layers": self.num_layers,
             "layer_names": self.layer_names,
             "map": list(self._map)
             }
        return d


class MapInstance(Map):
    def __init__(self, base_map: Map):
        super.__init__(base_map.width, base_map.height, base_map.num_layers, layer_names=base_map.layer_names)
        # To save ram, this table only stores the differences of this instance vs. the reference map.
        # If a lock is picked, or chest looted, the changes won't affect the master copy.
        self._map = InstanceTable(base_map._map)

    def can_move_to(self, x: int, y: int, direction: Direction) -> Why:
        # TODO
        return Why.true()

    def get_spawn_info(self):
        # TODO
        return self.width // 2, self.height // 2, Direction.NORTH





def load_map_from_dict(d) -> Map:
    # note "map.json" is Map.asdict() with an extra "layer_sprites" key entered for sprite location.
    map_id = d["map_identifier"]
    w = d["width"]
    h = d["height"]
    num_layers = d["num_layers"]
    layer_names = d["layer_names"]
    map_tiles = d["map"]
    the_map = Map(map_id, w, h, num_layers, layer_names)
    for x, y in itertools.product(range(w), range(h)):
        the_map[x, y] = map_tiles[(y * w) + x]
    return the_map


