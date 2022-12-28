from typing import Dict

from game_engine.game_engine import Spell
from game_engine.map import Map


class World:
    maps: Dict[str: Map]
    spells: Dict[str: Spell]
