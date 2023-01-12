from typing import Dict, List

from game_engine.game_engine import Spell
from game_engine.map import Map


class World:
    """
    The world class contains only what is _necessary_ for the server
    to simulate the world. Things like images and sound effects are
    referenced by name, not stored here.
    """
    def __init__(self,
                 world_name,
                 maps: List[Map],
                 spells: List[Spell]):
        self.maps: Dict[str, Map] = {m.map_identifier: m for m in maps}
        self.spells: Dict[str, Spell] = {s.name: s for s in spells}
        self.world_name = world_name

    def as_dict(self):
        map_names = [m for m in self.maps.keys()]
        spell_names = [s for s in self.spells.keys()]

        d = {
            "world_name": self.world_name,
            "map_names": map_names,
            "spell_names": spell_names
        }

        return d

# class WorldInstance:
#     def __init__(self, world: World):
#         self.world = World
#         # self.map_instances = [MapInstance(m) for m in world.maps]
#         pass
#
#     def take_turn(self, new_location):
#         pass

