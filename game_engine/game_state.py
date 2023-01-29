from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple

from chosm.resource_pack import ResourcePack
from game_engine.dice import Roll
from game_engine.game_engine import PlayerParty
from game_engine.map import Map
from helpers.why import Why
from game_engine.world import World, WorldInstance
from mam_game.mam_constants import Direction

class GameAction(Enum):
    NONE        = 0
    MOVE_FWD    = 1
    MOVE_BACK   = 2
    MOVE_LEFT   = 3
    MOVE_RIGHT  = 4
    TURN_LEFT   = 5
    TURN_RIGHT  = 6
    ATTACK      = 7
    CAST        = 8
    QUICK_CAST  = 9
    RUN         = 10
    REST        = 11
    BLOCK       = 12
    INSPECT     = 13
    USE         = 14
    BASH        = 15
    SKIP        = 16


class GameState:
    def __init__(self, world: World, pack: ResourcePack):
        self.party: PlayerParty = PlayerParty(10, 10, Direction.NORTH, "player", True, False, True)
        self.current_world: WorldInstance = WorldInstance(world)
        self.pack: ResourcePack = pack

        x, y, direction, spawn_map = world.get_spawn_info()
        self.current_map: Map = spawn_map
        self.party.pos_x = x
        self.party.pos_y = y
        self.party.facing = direction

    def attempt_to_take_action(self, action: GameAction) -> Why:
        new_location = False
        x, y, facing = self.party.get_pos()
        match action:
            case GameAction.MOVE_FWD:
                new_location = True
                x, y = facing.apply(x, y)
            case GameAction.MOVE_BACK:
                new_location = True
                x, y = facing.other_way().apply(x, y)

        if new_location:
            can_do_it = self.map.can_move_to(x, y, facing)
            if not can_do_it:
                return can_do_it
            self.party.set_pos(x, y, facing)

        self.current_world.take_turn(new_location)
        return Why.true()



