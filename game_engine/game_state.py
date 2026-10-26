from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple

from assets.asset_record import AssetRecord
from assets.resource_pack import ResourcePack
from game_engine.game_engine import PlayerParty
from game_engine.map import Map, MapInstance
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
        self.party: PlayerParty = PlayerParty(14, 52, Direction.NORTH, "player", True, False, True)
        self.current_world: WorldInstance = WorldInstance(world)
        self.pack: ResourcePack = pack

        x, y, direction, spawn_map = world.get_spawn_info()  # this sets the actual initial player pos
        self.current_map_asset: AssetRecord = spawn_map
        self.current_map: MapInstance = MapInstance(spawn_map)
        self.party.pos_x = x
        self.party.pos_y = y
        self.party.facing = direction

    def attempt_to_take_action(self, action: GameAction) -> Why:
        new_location = False
        x, y, facing = self.party.get_pos()
        match action:
            case GameAction.MOVE_FWD:
                new_location = True
                x, y = facing.walk_from(x, y)
            case GameAction.MOVE_BACK:
                new_location = True
                x, y = facing.other_way().walk_from(x, y)
            case GameAction.TURN_LEFT:
                new_location = True
                facing = facing.left()
            case GameAction.TURN_RIGHT:
                new_location = True
                facing = facing.right()

        if new_location:
            can_do_it = self.current_map.can_move_to(x, y, facing)
            if not can_do_it:
                return can_do_it
            self.party.set_pos(x, y, facing)

        self.current_world.take_turn(new_location)
        return Why.true()

    def get_tile(self, steps_f, steps_r, off_map_value):
        x = self.party.pos_x
        y = self.party.pos_y
        x, y = self.party.facing.walk_from(x, y, steps_f)
        x, y = self.party.facing.right().walk_from(x, y, steps_r)

        the_map = self.current_map

        if 0 <= x < the_map.width and 0 <= y < the_map.height:
            return the_map[x, y]
        else:
            return off_map_value

def main():
    ga = GameAction("move_forward")
    print(ga)

if __name__ == '__main__':
    main()



