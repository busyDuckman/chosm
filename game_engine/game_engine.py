from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple

from game_engine.dice import Roll


class DamageType(Enum):
    PHYSICAL   = 0
    FIRE       = 1
    ELECTRICAL = 2
    COLD       = 3
    POISON     = 4
    ENERGY     = 5
    MAGIC      = 6


@dataclass
class NPCBehaviour:
    is_monster: bool
    will_flee: bool
    can_swim:  bool
    can_walk:  bool
    can_fly:   bool
    target_priority: str
    ranged_attack: bool

@dataclass
class Attack:
    damage: List[Tuple[Roll, DamageType]]
    special_effect: str
    hit_chance: float

    def roll(self):
        return [(r.roll()) for r, d in self.damage]


@dataclass
class NPCType:
    name: str
    type: str
    stats: Dict[str, int]
    spells: List[str]
    resistance: Dict[DamageType, int]
    behaviour: NPCBehaviour
    attacks: List[Attack]


@dataclass()
class Spell:
    name: str
    mp_cost: int
    attack: Attack
    script: str


class Direction(Enum):
    NORTH: 0
    EAST:  1
    SOUTH: 2
    WEST:  3





