from typing import Dict, List

from game_engine.game_engine import Spell
from game_engine.map import Map
from mam_game.mam_constants import Direction


class World:
    """
    The world class contains only what is _necessary_ for the server
    to simulate the world. Things like images and sound effects are
    referenced by name, not stored here.
    """
    def __init__(self,
                 world_name,
                 maps: List[Map],
                 spells: List[Spell],
                 default_map: str = None):
        self.maps: Dict[str, Map] = {m.map_identifier: m for m in maps}
        self.default_map = maps[0].map_identifier if default_map is None else default_map
        self.spells: Dict[str, Spell] = {s.name: s for s in spells}
        self.world_name = world_name

    def as_dict(self):
        map_names = [m for m in self.maps.keys()]
        spell_names = [s for s in self.spells.keys()]

        d = {
            "world_name": self.world_name,
            "map_identifiers": map_names,
            "spell_names": spell_names,
            "default_map": self.default_map
        }

        return d

    def get_default_map(self):
        return self.maps[self.default_map]

    def get_spawn_info(self):
        return 8, 8, Direction.NORTH, self.get_default_map()

# class WorldInstance:
#     def __init__(self, world: World):
#         self.world = World
#         # self.map_instances = [MapInstance(m) for m in world.maps]
#         pass
#
#     def take_turn(self, new_location):
#         pass

