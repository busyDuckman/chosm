from dataclasses import dataclass
from typing import Tuple, Dict

from mam_game.mam_constants import Direction
from mam_game.mam_asset import MamAsset
from mam_game.sound_fx_decoder import SoundFXAsset
from mam_game.sprite_file_decoder import SpriteFile

@dataclass
class EntityAnimation:
    sprite: SpriteFile
    animation: str
    sound: SoundFXAsset
    pos: Tuple[int, int]


class Entity(MamAsset):
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
