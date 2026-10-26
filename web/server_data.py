# CHOSM data
import logging
import os
from typing import Dict

from game_engine.dynamic_file_manager import DynamicFileManager
from assets.resource_pack import ResourcePack
from game_engine.game_state import GameState
from game_engine.single_vanishing_point_painting import SingleVanishingPointPainting

log = logging.getLogger(__name__)


class _ServerDataMeta(type):
    resource_folder = ""
    resource_packs: Dict[str, ResourcePack] = {}
    chosm_version = "0.05"

    dynamic_folder = ""
    dyna_file_manager: DynamicFileManager = None

    default_svp_composer: SingleVanishingPointPainting = None

    def load_resource_packs(self):
        # load the resource packs for every folder.
        log.info("Loading resource packs:")
        for d in os.scandir(ServerData.resource_folder):
            rp = ResourcePack(d.path)
            self.resource_packs[rp.slug] = rp
            log.info("  - %s", rp.slug)

        # link dependencies
        for pack in self.resource_packs.values():
            pack.refresh(forced=True, other_resource_packs=self.resource_packs)

    def save_game(self, user_name, game_state: GameState):
        pass

    def load_game(self, user_name) -> GameState:
        # TODO: for now just create a new game.
        # chosm-default overrides the Darkside pack, so the world comes from Darkside but drawn with the new art.
        chosm_pack: ResourcePack = self.resource_packs['chosm-default']
        world = chosm_pack.load_world("main_world")
        return GameState(world, chosm_pack)


class ServerData(object, metaclass=_ServerDataMeta):
    pass

