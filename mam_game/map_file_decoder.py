import io
import logging
from dataclasses import dataclass, asdict
from typing import List, Dict

from chosm.map_asset import MapAsset
from chosm.sprite_asset import SpriteAsset
from game_engine.map import Map
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, spell_slug, RawFile, Direction
import helpers.stream_helpers as sh

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

    # 8 bytes, uint16 mazes_id's to the N, E, S, W
    joining_map_ids = sh.read_uint16_array(f, 4)
    order = [Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST]
    joining_map_ids = {d: x for d, x in zip(order, joining_map_ids)}

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
    default_floor_type = sh.read_byte(f)

    return maze_id, joining_map_ids, restricted_spells, can_rest, can_save, is_dark, is_outside, \
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


class MAMMapAsset(MapAsset):
    def __init__(self, file_id,
                 name,
                 game_map: Map,
                 layers: Dict[str, SpriteAsset],
                 joining_map_ids, restricted_spells,
                 can_rest, can_save, is_dark, is_outside):
        super().__init__(file_id, name, game_map, layers)
        self.joining_map_ids = joining_map_ids
        self.restricted_spells = restricted_spells
        self.can_rest = can_rest
        self.can_save = can_save
        self.is_dark = is_dark
        self.is_outside = is_outside
        self.map_pos_x = 0
        self.map_pos_y = 0

    def pos(self):
        return self.map_pos_x, self.map_pos_y

    def is_top_left(self):
        return self.joining_map_ids[Direction.NORTH] == 0 and self.joining_map_ids[Direction.WEST] == 0

    def as_map_asset(self):
        return MapAsset(self.file_id, self.name, self.game_map, self.tile_set)

    def walk(self, joined_maps_by_id: Dict, direction: Direction):
        current = self
        next_id = "not zero"
        maps_seen = set()
        while True:
            yield current

            next_id = current.joining_map_ids[direction]
            if next_id == 0:
                break

            if next_id in maps_seen:
                raise MAMFileParseError(None, "Maps set loops infinitely")
            maps_seen.add(next_id)

            if next_id not in joined_maps_by_id:
                raise MAMFileParseError(None, f"Map id not found: id = {next_id}")
            current = joined_maps_by_id[next_id]

@dataclass
class MaMTile:
    # The CHOSM layer naming convention
    height: int
    ground: int    # iBase
    surface: int   # iMiddle
    wall: int      # iTop
    env: int       # iTop
    building: int  # iOverlay

    # MaM specific Layers
    has_grate: bool
    no_rest: bool
    has_drain: bool
    has_event: bool
    has_object: bool





def load_map_file(maze_dat: RawFile,
                  maze_mob: RawFile,
                  maze_evt: RawFile,
                  tile_sets: List[SpriteAsset],
                  ver: MAMVersion,
                  platform: Platform,
                  map_width = 16,
                  map_height = 16
                  ) -> MapAsset:
    # From the wiki: take the map_id from the filename, not the value in the file
    map_id = int("".join([c for c in maze_dat.file_name if c.isdigit()]))
    total_tiles = map_width * map_height

    mm5_surface_lut, mm4_surface_lut, env_lut = get_luts()
    if ver == MAMVersion.CLOUDS:
        surface_lut = mm4_surface_lut
    elif ver == MAMVersion.DARKSIDE:
        surface_lut = mm5_surface_lut
    else:
        raise MAMFileParseError(0, "", "Unsupported MAM version for maps")

    f = io.BytesIO(bytearray(maze_dat.data))
    # from: https://xeen.fandom.com/wiki/MAZExxxx.DAT_File_Format
    # 512 bytes: WallData, 16x16 uint16 values comprising the visual map data (floors, walls, etc...)
    map_data = sh.read_uint16_array(f, total_tiles)

    # 256 bytes: CellFlag, 16x16 bytes, each byte holding the flags for one tile
    map_flags = sh.read_byte_array(f, total_tiles)

    # Read the rest of the file
    maze_slug, joining_map_ids, restricted_spells, \
        can_rest, can_save, is_dark, is_outside, \
        wall_type_lut, surface_type_lut, default_floor_type = read_map_meta_data(f)

    layers = list(MaMTile.__annotations__.keys())
    the_map = Map(map_id, map_width, map_height, len(layers), layers)

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

            # 5 flags and a 3 bit int.
            has_grate = (m_flag & 0x80) != 0
            no_rest = (m_flag & 0x40) != 0
            has_drain = (m_flag & 0x20) != 0
            has_event = (m_flag & 0x10) != 0
            has_object = (m_flag & 0x08) != 0
            _ = (m_flag & 0x07)  # number of monsters, unused

            #     height: int
            #     ground: int    # iBase
            #     surface: int   # iMiddle
            #     wall: int      # iTop
            #     env: int       # iTop
            #     building: int  # iOverlay


            building = map_top
            if map_top == 0 and map_overlay != 0:
                building = map_overlay + 16

            if map_top != 0 and map_overlay != 0:
                logging.error("TODO: work out the map overlay stuff.")
                # print("arrrg")
                # exit(0)
            #              h  gnd   surface, w, env,    building
            tile = MaMTile(0, base, map_top, 0, middle, building,
                           has_grate, no_rest, has_drain, has_event, has_object)
            the_map[x, map_height - y - 1] = asdict(tile)

    the_map.recompress_map()
    # tileset_name = "outdoor.til"

    layers = {"ground": "outdoor_tile_ground.til",
              "env": "outdoor_tile_env.til",
              "building": "outdoor_tile_building.til"}

    layers = {k: next(t for t in tile_sets if t.name == f) for k, f in layers.items()}

    # tile_set = [t for t in tile_sets if t.name == tileset_name][0]
    map_file = MAMMapAsset(map_id, f"map_{map_id:04d}", the_map, layers,
                        joining_map_ids, restricted_spells,
                        can_rest, can_save, is_dark, is_outside
                        )
    return map_file

