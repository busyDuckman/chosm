import copy
import itertools
from typing import Iterator, Any, Dict, List

from slugify import slugify

from helpers.misc import popo_to_dict
from helpers.why import Why
from helpers.archetyped_table import ArchetypedTable, InstanceTable, DifferenceTable
from mam_game.mam_constants import Direction
from collections.abc import Mapping


class AssetLut(Mapping):
    """
    An asset Look Up Table. Maps a value (often an integer) to an asset slug [see: ResourcePack].
    A map may use an index into a table of images/sprites/scripts.

    This is also a bit like css for dungeons, or like an "environment set". If you change a wall sprite for
    AssetLut "stone-dungeon-03", then all maps using "stone-dungeon-03" will receive the new graphics.

    Notes:
      - "None" is a valid and normal value for a key. eg: {0: None} means thar if the value is 0, nothing is there.
      - This class is intended to be memory resident in a running game server.
      - This class is managed by the Map class.
      - The goal is not to index via sprite frame number style lookups (everything is a sprite mantra).
        - TODO: the tile based mini-map still does this.
    """
    def __init__(self, name, mapping: Dict[Any, str]):
        self.name = slugify(name)  # also the name of the layer
        self.mapping = mapping

    def __getitem__(self, key: Any) -> str:
        return self.mapping[key]

    def __len__(self) -> int:
        return len(self.mapping)

    def __iter__(self) -> Iterator:
        return self.mapping.__iter__()


class Map:
    """
    This class is an immutable collection of layers representing a grid based world in its initial state.

    Another class: MapInstance, handles the "game state" or changes the player makes to the world defined
    in this class.

    Notes:
      - This class uses ArchetypedTable to store the world in a memory efficient manner.
      - This class is intended to be memory resident in a running game server.
      - Every session has one instance of the MapInstance class. Multiple instances of
        the MapInstance class can reference the same instance of a Map class.
    """
    def __init__(self, map_identifier, w, h,
                 layer_names: List[str],
                 luts: List[AssetLut]):
        """
        Creates a new game map
        :param map_identifier: map name
        :param w: Map width
        :param h: Map height
        :param layer_names: Layer names
        :param luts: List of AssetLuts with names that match the layer names.
        """
        if layer_names is None or len(layer_names) == 0:
            raise ValueError("numer of layers must be > 0")

        self.map_identifier = str(map_identifier)
        self.num_layers = len(layer_names)
        self.width: int = w
        self.height: int = h
        self.layer_names = tuple([slugify(q) for q in layer_names])
        self.luts: List[AssetLut] = luts
        self.luts_by_name: Dict[str: AssetLut] = {q.name: q for q in luts}
        self._map: DifferenceTable = ArchetypedTable({n: 0 for n in self.layer_names}, self.width * self.height)

    def set_luts(self, luts: List[AssetLut]):
        self.luts = luts
        self.luts_by_name = {q.name: q for q in luts}

    def recompress_map(self):
        self._map = ArchetypedTable(self._map, lru_cache_size=self._map.lru_cache_size)

    def size(self):
        return self.width, self.height

    # @property
    # def layer_names(self):
    #     return copy.copy(self._layer_names)
    #
    # @layer_names.setter
    # def layer_names(self, value):
    #     self._layer_names = value
    #     self._layer_lut = {n: i for i, n in enumerate(self._layer_names)}

    def __getitem__(self, pos):
        if len(pos) == 2:
            x, y = pos
            return self._map[y * self.width + x]
        if len(pos) == 3:
            x, y, layer_name = pos
            layer_name = slugify(layer_name)
            return self._map[y * self.width + x, layer_name]
        raise KeyError()

    def __setitem__(self, pos, value: Dict[str, Any]):
        """
        Assignes multiple layers (cols) to a row in the table.
        :param pos:
        :param value: A
        :return:
        """
        x, y = pos
        self._map[y * self.width + x] = {slugify(n): q for n, q in value.items()}

    def __iter__(self):
        for x, y in itertools.product(range(self.width), range(self.height)):
            yield x, y, self._map[y * self.width + x]

    def __len__(self):
        return self.width * self.height

    def map_as_array_of_arrays(self):
        rows = []
        for row_idx in range(len(self._map)):
            row = self._map[row_idx]
            row = [row[k] for k in self._map.col_headings]
            rows.append(row)
        return rows

    def asdict(self):
        d = {"map_identifier": self.map_identifier,
             "width": self.width,
             "height": self.height,
             "layer_names": self._map.col_headings,  # to ensure layer_names is in the same order as the dumped table.
             "luts": [popo_to_dict(q) for q in self.luts],
             "map": self.map_as_array_of_arrays()
             }
        return d


class MapInstance(Map):
    def __init__(self, base_map: Map):
        super().__init__(base_map.map_identifier, base_map.width, base_map.height,
                         base_map.num_layers, layer_names=base_map.layer_names)
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
    layer_names = d["layer_names"]
    map_tiles = d["map"]
    luts = [AssetLut(**q) for q in d["luts"]]

    # rectify to the format required
    map_tiles = [{h: c for h, c in zip(layer_names, row)} for row in map_tiles]

    the_map = Map(map_id, w, h, layer_names, luts)
    for x, y in itertools.product(range(w), range(h)):
        the_map[x, y] = map_tiles[(y * w) + x]
    return the_map


