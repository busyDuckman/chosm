import itertools
from dataclasses import dataclass
from enum import Enum, IntFlag
from typing import Dict, Tuple

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

@dataclass
class Tile:
    idx_ground:   int
    idx_object:   int
    idx_map_tile: int
    idx_map_icon: int
    height: int


class Map:
    # a grid based map
    def __init__(self, w, h):
        self.width = w
        self.height = h
        self._map = [Tile(0, 0, 0, 0, 0) for _ in range(self.width * self.height)]

    def __getitem__(self, pos):
        x, y = pos
        return self._map[y*self.width+x]

    def __setitem__(self, pos, value):
        x, y = pos
        self._map[y * self.width + x] = value

    def __iter__(self):
        for x, y in itertools.product(range(self.width), range(self.height)):
            yield x, y, self._map[y * self.width + x]

    def __len__(self):
        return self.width * self.height


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

def main():
    map = Map(10, 10)

if __name__ == '__main__':
    main()