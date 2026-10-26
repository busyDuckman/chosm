"""
Checks the game data needed to bake assets and run the server is present.

When something is missing, a banner explains how to fix it, rather than a stack trace from deep in the code.
"""
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOS_DIR = PROJECT_ROOT / "game_files" / "dos"
BAKED_DIR = PROJECT_ROOT / "game_files" / "baked"

# The original game files `just bake` reads (see mam_game/cc_file.py main), and the resource packs it makes.
REQUIRED_GAME_FILES = ["DARK.CC", "DARK.CUR"]
REQUIRED_PACKS = ["dark-cccur-darkside-pc-dos"]


def print_banner(*lines: str):
    width = max(len(line) for line in lines) + 6
    border = "#" * width
    blank = "#" + " " * (width - 2) + "#"
    body = ["#   " + line.ljust(width - 5) + "#" for line in lines]
    print("\n".join(["", border, blank, *body, blank, border, ""]), file=sys.stderr, flush=True)


def missing_game_files() -> List[str]:
    return [f for f in REQUIRED_GAME_FILES if not (DOS_DIR / f).is_file()]


def missing_packs() -> List[str]:
    # info.json is written when a pack is baked, a folder without one is a failed bake
    return [p for p in REQUIRED_PACKS if not (BAKED_DIR / p / "info.json").is_file()]


def _copy_game_files_lines(files: List[str]) -> List[str]:
    return [f"Copy these files from your Might and Magic: Darkside of Xeen install",
            f"into {DOS_DIR}",
            "",
            *[f"    {f}" for f in files]]


def check_can_bake() -> bool:
    """
    Returns True if `just bake` has what it needs, otherwise prints how to fix it and returns False.
    """
    if files := missing_game_files():
        print_banner("CAN NOT BAKE: game files are missing.",
                     "",
                     *_copy_game_files_lines(files),
                     "",
                     "Then run:  just bake")
        return False
    return True


def check_can_serve() -> bool:
    """
    Returns True if the server has the baked assets it needs, otherwise prints how to fix it and returns False.
    """
    packs = missing_packs()
    if not packs:
        return True

    lines = ["CAN NOT START THE SERVER: game assets have not been baked.",
             "",
             f"Missing from {BAKED_DIR}:",
             *[f"    {p}" for p in packs],
             ""]
    if files := missing_game_files():
        lines += ["Step 1: " + _copy_game_files_lines(files)[0],
                  *["        " + line if line else "" for line in _copy_game_files_lines(files)[1:]],
                  "",
                  "Step 2: run  just bake"]
    else:
        lines += ["Run:  just bake"]

    print_banner(*lines)
    return False


if __name__ == '__main__':
    # used by `just serve`, to explain what is missing before uvicorn starts
    sys.exit(0 if check_can_serve() else 1)
