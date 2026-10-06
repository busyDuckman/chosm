# CHOSM data
import os
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

    def load_resource_packs(self):
        # load the resource packs for every folder.
        print("Loading resource packs:")
        for d in os.scandir(ServerData.resource_folder):
            rp = ResourcePack(d.path)
            self.resource_packs[rp.slug] = rp
            print("  - " + rp.slug)

        # link dependencies
        for pack in self.resource_packs.values():
            pack.refresh(forced=True, other_resource_packs=self.resource_packs)

        chosm_pack: ResourcePack = self.resource_packs['chosm-default']
        # print()
        # print(chosm_pack.slug)
        # print(chosm_pack.keys())
        # print(chosm_pack["sprite-030-mon"].asset_type)
        # print(chosm_pack._asset_records_by_type)
        # print()

    def save_game(self, user_name, game_state: GameState):
        pass

    def load_game(self, user_name) -> GameState:
        # TODO: for now just create a new game
        mam5_pack: ResourcePack = self.resource_packs['dark-cccur-darkside-pc-dos']
        chosm_pack: ResourcePack = self.resource_packs['chosm-default']

        # chosm_pack.includes.append(mam5_pack)
        world = chosm_pack.load_world("main_world")
        return GameState(world, chosm_pack)


class ServerData(object, metaclass=_ServerDataMeta):
    pass

