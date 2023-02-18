# CHOSM data
from typing import Dict

from game_engine.dynamic_file_manager import DynamicFileManager
from assets.resource_pack import ResourcePack
from game_engine.game_state import GameState
from game_engine.single_vanishing_point_painting import SingleVanishingPointPainting


class _ServerDataMeta(type):
    resource_folder = ""
    resource_packs: Dict[str, ResourcePack] = {}
    chosm_version = "0.05"

    dynamic_folder = ""
    dyna_file_manager: DynamicFileManager = None

    default_svp_composer: SingleVanishingPointPainting = None

    def save_game(self, user_name, game_state: GameState):
        pass

    def load_game(self, user_name) -> GameState:
        # TODO: for now just create a new game
        mam5_pack: ResourcePack = self.resource_packs['dark-cccur-darkside-pc-dos']
        mam5_world = mam5_pack.load_world("main_world")
        return GameState(mam5_world, mam5_pack)


class ServerData(object, metaclass=_ServerDataMeta):
    pass



