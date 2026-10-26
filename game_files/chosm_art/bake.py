import os
import shutil
from os.path import join
from pathlib import Path

from PIL import Image
from slugify import slugify

from assets.resource_pack import ResourcePackInfo
from assets.sprite_asset import SpriteAsset, AnimLoop


def bake_single_image_sprite(file_name: str, sprite_name, bake_path, src_path):
    img = Image.open(join(src_path, file_name)).convert(mode="RGBA")
    sprite = SpriteAsset(0, sprite_name, [img], [AnimLoop.make_static(0, "idle")])
    sprite_path = os.path.join(bake_path, sprite.slug)
    assert Path(bake_path) in Path(sprite_path).parents
    os.makedirs(sprite_path, exist_ok=True)
    print("  - baking single frame sprite: " + str(sprite))
    sprite.bake(sprite_path)


def bake(bake_dir=None):
    """
    Extract all files to a folder
    """
    print("Initialising resource pack: ")
    rpi = ResourcePackInfo("chosm default", "duckman", True)
    rpi.author_info = "Replacement image set for M&M games"
    rpi.is_private = False
    rpi.overrides.append("dark-cccur-darkside-pc-dos")

    bake_path = init_destination_folder(bake_dir, rpi)
    print("  -       path:", bake_path)

    # create the info.json
    info_file = rpi.save_info_file(bake_path)
    print("  -      json:", info_file)

    src_path = os.getcwd()
    if not src_path.endswith("chosm_art"):
        # perhaps invoked in the repos root folder
        src_path = join(src_path, "game_files", "chosm_art")

    print("  -  src path:", src_path)

    # open and bake assets
    print("\nBaking resources: ")
    bake_single_image_sprite("sky.png", "sky.sky_flat", bake_path, src_path)
    bake_single_image_sprite("grass.png", "grass.srf_flat", bake_path, src_path)
    bake_single_image_sprite("water_2.png", "water.srf_flat", bake_path, src_path)


    print("  - Done.")
    print()


def init_destination_folder(bake_dir: str, rpi: ResourcePackInfo):
    if bake_dir is None:
        bake_dir = ["game_files", "../game_files", "../../game_files"]
        bake_dir = [b for b in bake_dir if os.path.isdir(b)]
        assert len(bake_dir) > 0
        bake_dir = os.path.abspath(bake_dir[0])
        bake_dir = os.path.join(bake_dir, "baked")

    bake_path = os.path.join(bake_dir, rpi.slug)

    # remove path if it exists
    if os.path.exists(bake_path):
        # because I don't trust software to delete a path without some sanity checks
        assert Path(bake_dir) in Path(bake_path).parents
        assert len(rpi.slug.strip()) > 0
        shutil.rmtree(bake_path)

    # create the path
    os.makedirs(bake_path, exist_ok=True)
    return bake_path


if __name__ == '__main__':
    bake()