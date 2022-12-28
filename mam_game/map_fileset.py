import glob
import io
import json
import os.path
import textwrap
from dataclasses import dataclass, asdict
from os.path import join
from typing import List, Dict, Tuple, Any

import imageio
import slugify
from PIL import Image

import helpers.pil_image_helpers as pih
from game_engine.game_engine import Direction
from game_engine.map import Map, Tile
from helpers.misc import is_continuous_integers
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, map_slug, spell_slug, RawFile
from mam_game.mam_file import MAMFile
import helpers.stream_helpers as sh
import helpers.color as ch
from mam_game.pal_file import PalFile

class MapFile(MAMFile):
    def __init__(self, file_id, name):
        super().__init__(file_id, name)

def get_luts():
    mm5_surface_lut = [
        "WATER.SRF",  "DIRT.SRF",  "GRASS.SRF",   "SNOW.SRF",
        "SWAMP.SRF",  "LAVA.SRF",  "DESERT.SRF",  "ROAD.SRF",
        "DWATER.SRF", "TFLR.SRF",  "SKY.SRF",     "CLOUD.SRF",
        "SEWER.SRF",  "CROAD.SRF", "SCORTCH.SRF", "SPACE.SRF"];

    mm4_surface_lut = [
        "WATER.SRF",  "DIRT.SRF", "GRASS.SRF",  "SNOW.SRF",
        "SWAMP.SRF",  "LAVA.SRF", "DESERT.SRF", "ROAD.SRF",
        "DWATER.SRF", "TFLR.SRF", "SKY.SRF",    "CLOUD.SRF",
        "SPACE.SRF",  # "SEWER.SRF" not in the file   #TODO, there appears to be .SRF files I have not identified
        "SPACE.SRF",  # "CROAD.SRF" not in the file   #TODO, there appears to be .SRF files I have not identified
        "SCORTCH.SRF", "SPACE.SRF"]  # ok

    env_lut = [
        None,           "MOUNT.WAL",   "LTREE.WAL",     "DTREE.WAL",
        "GRASS.WAL",    "SNOTREE.WAL",   "DSNOTREE.WAL", "SNOMNT.WAL",
        "DEDLTREE.WAL",  None,  # "DMOUNT.WAL",
                                         "LAVAMNT.WAL", "PALM.WAL",
        "DMOUNT.WAL"]

    return mm5_surface_lut, mm4_surface_lut, env_lut

def read_map_meta_data(f):
    # 2 bytes: mazenumber, uint16 value indicating this map ID
    maze_id = sh.read_uint16(f)
    maze_slug = map_slug(maze_id)

    # 8 bytes, uint16 mazes_id's to the N, E, S, W
    joining_map_ids = sh.read_uint16(f, 4)
    order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
    joining_map_slugs = {d: map_slug(x) for d, x in zip(order, joining_map_ids)}

    # 2 bytes: mazeFlags
    # 2 bytes: mazeFlags2
    flags = sh.read_uint16(f)
    restricted_spells = []
    known_flags = [(6, "Etheralize"), (8, "Town Portal"), (9, "Super Shelter"),
                   (10, "Time Distortion"), (11, "Lloyds Beacon"), (12, "Teleport")]
    for bit_pos, spell in known_flags:
        if flags & (1 << bit_pos):
            restricted_spells += spell_slug(spell)
    can_rest = (flags & (1 << 14))
    can_save = (flags & (1 << 15))

    flags2 = sh.read_uint16(f)
    is_dark = (flags2 & (1 << 14))
    is_outside = (flags2 & (1 << 15))  # ie overworld

    # 16 bytes: wallTypes, 16 byte array of wall types, used for indirect lookup
    wall_type_lut = sh.read_byte_array(f, 16)
    # 16 bytes: surfaceTypes, 16 byte array of surface types (ie, floors) used for indirect lookup
    surface_type_lut = sh.read_byte_array(f, 16)
    # 1 byte: floor type, the default floor type (lookup table, used by indoor maps)
    default_floor_type = sh.read_byte()

    return maze_slug, joining_map_slugs, restricted_spells, can_rest, can_save, is_dark, is_outside, \
           wall_type_lut, surface_type_lut, default_floor_type



    # 1 byte: runX, the X coordinate the party will land at if they run from a fight
    # 1 byte: wallNoPass, wall values greater than or equal to this value cannot be walked through at all.
    # 1 byte: surfNoPass, suface values greater than or equal to this value cannot be stepped on (typically only ever 0x0F, space).
    # 1 byte: unlockDoor, the difficulty of unlocking a door on this map
    # 1 byte: unlockBox, the difficulty of unlocking a chest on this map
    # 1 byte: bashDoor, the difficulty of bashing through a door
    # 1 byte: bashGrate, the difficulty of bashing through a grate
    # 1 byte: bashWall, the difficulty of bashing through a wall (note that there are other requirements to bash through a wall, even if the party is strong enough)
    # 1 byte: chanceToRun, the difficulty of running from a fight
    # 1 byte: runY, the Y coordinate the party will land at if they run from a fight
    # 1 byte: trapDamage, the level of damage the party will receive from traps on this map
    # 1 byte: wallKind, the type of walls, used in a lookup table
    # 1 byte: tavernTips, lookup table for the text file used by the tavern, if any
    # 32 bytes: 16x16 bit array indicating which tiles have been "seen"
    # 32 bytes: 16x16 bit array indicating which tiles have been "stepped on"


def load_sprite_file(maze_dat: RawFile,
                     maze_mob: RawFile,
                     pal: PalFile,
                     ver: MAMVersion,
                     platform: Platform,
                     map_width = 16,
                     map_height = 16
                     ) -> MapFile:
    total_tiles = map_width * map_height

    mm5_surface_lut, mm4_surface_lut, env_lut = get_luts()
    if ver == MAMVersion.CLOUDS:
        surface_lut = mm4_surface_lut
    elif ver == MAMVersion.DARKSIDE:
        surface_lut = mm5_surface_lut
    else:
        raise MAMFileParseError(0,"", "Unsupported MAM version for maps")

    f = io.BytesIO(bytearray(maze_dat.data))
    # from: https://xeen.fandom.com/wiki/MAZExxxx.DAT_File_Format
    # 512 bytes: WallData, 16x16 uint16 values comprising the visual map data (floors, walls, etc...)
    map_data = sh.read_uint16_array(f, total_tiles)

    # 256 bytes: CellFlag, 16x16 bytes, each byte holding the flags for one tile
    map_flags = sh.read_byte_array(f, total_tiles)

    # Read the rest of the file
    maze_slug, joining_map_slugs, restricted_spells, \
        can_rest, can_save, is_dark, is_outside, \
        wall_type_lut, surface_type_lut, default_floor_type = read_map_meta_data(f)

    the_map = Map(map_width, map_height)

    # create the map
    for y in range(map_height):
        for x in range(map_width):
            index = (y * map_width) + x
            m_data = map_data[index]
            m_flag = map_flags[index]

            base = surface_type_lut[m_data & 0x0f]
            middle = wall_type_lut[(m_data>>4) & 0x0f]
            map_top =  (m_data>>8) & 0x0f
            map_overlay = (m_data>>12) & 0x0f

            #5 flags and a 3 bit int.
            has_grate = (m_flag & 0x80) != 0
            no_rest = (m_flag & 0x40) != 0
            has_drain = (m_flag & 0x20) != 0
            has_event = (m_flag & 0x10) != 0
            has_object = (m_flag & 0x08) != 0
            _ = (m_flag & 0x07)  # number of monsters, unused

            tile = Tile(base, middle, map_top, map_overlay)
            the_map[x, map_height - y - 1] = tile