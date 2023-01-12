from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple

from game_engine.dice import Roll
from mam_game.mam_constants import Direction


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


# Just a type (not the entity)
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


@dataclass(frozen=False)
class Entity:
    pos_x: int
    pos_y: int
    facing: Direction
    specific_name: str
    alive: bool
    deleted: bool
    visible: bool

    def get_pos(self) -> Tuple[int, int, Direction]:
        """
        return (x, y, facing)
        """
        return self.pos_x, self.pos_y, self.facing

    def set_pos(self, x: int, y: int, facing: Direction):
        self.pos_x, self.pos_y, self.facing = x, y, facing


@dataclass()
class NPCCharacter(Entity):
    npc_type: NPCType


@dataclass()
class PlayerParty(Entity):
    pass






