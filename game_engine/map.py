import copy
import itertools
from dataclasses import dataclass, asdict
from enum import Enum, IntFlag
from typing import Dict, Tuple, List

import numpy as np

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


class Tile:
    def __init__(self, height, *kwargs):
        self.height: int = height
        self.layers: List[int] = list(kwargs)

    def asdict(self):
        return {
            "height": self.height,
            "layers": self.layers
        }

# ["ground", "object", "map_tile", "map_icon"]

class Map:
    # a grid based map
    def __init__(self, w, h, num_layers, layer_names=None):
        if num_layers <= 0:
            raise ValueError("numer of layers must be > 0")

        self.width: int = w
        self.height: int = h
        self._map: List[Tile] = [Tile(0, 0, 0, 0, 0) for _ in range(self.width * self.height)]
        self.num_layers: int = num_layers
        self._layer_names: List[str]
        self._layer_lut: Dict[str, int] = {}
        if layer_names is None:
            self.layer_names = [f"layer_{i:02d}" for i in range(num_layers)]
        else:
            if len(layer_names) != num_layers:
                raise ValueError("numer of layer names != number of layers")
            ln = copy.copy(layer_names)  # TODO: do I want to normalise they layer names?
            self.layer_names = ln

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
            layer_num = self._layer_lut[layer_name]
            return self._map[y * self.width + x].layers[layer_num]

    def __setitem__(self, pos, value):
        x, y = pos
        self._map[y * self.width + x] = value

    def __iter__(self):
        for x, y in itertools.product(range(self.width), range(self.height)):
            yield x, y, self._map[y * self.width + x]

    def __len__(self):
        return self.width * self.height

    def asdict(self):
        d = {"width": self.width,
             "height": self.height,
             "num_layers": self.num_layers,
             "layer_names": self.layer_names,
             "map": [tile.asdict() for tile in self._map]
             }
        return d



class MapInstance:
    def __init__(self, base_map: Map):
        self.base_map: Map = base_map
        self.modified_tiles: Dict[Tuple[int, int], Tile] = {}

#      int[] joiningMaps;
#      List<String> cantCastList;
#      boolean canRest;
#      boolean canSave;
#      boolean[] miscFlags;
#      boolean isDark;
#      boolean isOutdoors;
#     //private MaMSprite tilesSprite;
#      int floorType;
#      int wallNoPass;
#      int surfNoPass;
#      int unlockDoor;
#      int unlockBox;
#      int bashDoor;
#      int bashGrate;
#      int bashWall;
#      int chanceToRun;
#      int trapDamage;
#      int wallKind;
#      int tavernTips;
#      Point runPos;
