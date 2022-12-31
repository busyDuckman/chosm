from typing import List

from PIL import Image

from chosm.asset import Asset
from game_engine.game_engine import NPCType
from helpers import pil_image_helpers as pih


class NPCDatabaseAsset(Asset):
    def __init__(self, file_id: int, name: str, monsters: List[NPCType]):
        super().__init__(file_id, name)
        self.monsters = monsters

    def __str__(self):
        return f"Binary File: id={self.file_id} len={len(self.data)}"

    def get_type_name(self):
        return "mondb"

    def _get_bake_dict(self):
        info = super()._get_bake_dict()
        # info["width"] = self.width
        # info["height"] = self.height
        # info["num_frames"] = len(self.frames)
        #
        # def anim_dict(a: AnimLoop):
        #     d = asdict(a)
        #     d["fps"] = a.get_fps()
        #     d["seconds_per_loop"] = a.get_seconds_per_loop()
        #     return d
        #
        # info["animations"] = [anim_dict(a) for a in self.animations.values()]
        return info

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = Image.new("RGB", size=(preview_size, preview_size))
        img = pih.annotate(img, "monsters", bottom_text=f"n={len(self.monsters)}")
        return img

    def bake(self, file_path):
        # with open(os.path.join(file_path, "data.bin"), 'wb') as f:
        #     f.write(bytes(self.data))
        super().bake(file_path)

def load_npc_db_from_baked_folder(folder: str):
    # TODO: implement this
    return NotImplemented
