from dataclasses import dataclass
from typing import Tuple, Dict

from mam_game.mam_constants import Direction
from mam_game.mam_file import MAMFile
from mam_game.sound_fx_file import SoundFX
from mam_game.sprite_file import SpriteFile

@dataclass
class EntityAnimation:
    sprite: SpriteFile
    animation: str
    sound: SoundFX
    pos: Tuple[int, int]


class Entity(MAMFile):
    def __init__(self):
        # eg: self.views[Direction.NORTH]["mon"].sprite.animations["idle"]
        self.views: Dict[Direction, Dict[str, EntityAnimation]] = {}




def merge_sprite(self, other):
    """
    Make a new sprite from this and another.
    """
    other: SpriteFile = other
    width = max(self.width, other.width)
    height = max(self.height, other.height)
