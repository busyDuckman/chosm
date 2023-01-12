# this is all stubs for now.
from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from game_engine.game_engine import PlayerParty
from game_engine.game_state import GameState
from game_engine.map import Map
from game_engine.world import World
from mam_game.mam_constants import Direction



@dataclass
class Session:
    user_name: str
    game_state: GameState

    def save_game(self):
        pass

    def translate(self, message):
        """
        Translates a system message to the users preferred language.
        :param message:
        :return:
        """
        return message  # TODO: i18n






