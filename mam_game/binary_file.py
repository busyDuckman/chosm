from typing import List

from assets.binary_asset import BinaryAsset
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError


def load_bin_file(file_id: int, name: str, data: List,
                  ver: MAMVersion, platform: Platform) -> BinaryAsset:
    if len(data) == 0:
        raise MAMFileParseError(file_id, name, "Binary file was empty")

    return BinaryAsset(file_id, name, bytearray(data))
