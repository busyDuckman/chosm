import enum
from enum import Enum

# building block things that need to be broadly importable without creating circular dependencies/


@enum.unique
class AssetTypes(Enum):
    BINARY = 0
    SPRITE = 1
    MAP = 2
    NPC = 3
    NPC_DATABASE = 4
    PALETTE = 5
    TEXT_DB = 6
    SOUND_FX = 7
    MUSIC = 8
    WORLD = 9

    def __str__(self):
        return self.name.lower()


@enum.unique
class SpriteRoles(Enum):
    NPC                    = 0
    WALL                   = 1
    WALL_SMASHED           = 3
    WALL_WITH_LIGHT        = 4
    WALL_WITH_STAIRS_UP    = 5
    WALL_WITH_STAIRS_DOWN  = 6
    WALL_WITH_DOOR_CLOSED  = 7
    WALL_WITH_DOOR_OPEN    = 8
    WALL_WITH_DOOR_SMASHED = 9
    WALL_ENTRANCE          = 10  # always open passage, eg: arch-way, empty door frame, walk between columns.
    WALL_SHELF             = 11  # ie: the wall holds a thing
    WALL_CUPBOARD_CLOSED   = 12  # ie: safes, things with doors
    WALL_CUPBOARD_OPEN     = 13
    WALL_DECAL             = 14

    SKY                    = 20
    ROOF                   = 22  # xeen calls this sky, I am separating the concept

    GROUND                 = 30
    WATER                  = 31
    GROUND_DECAL           = 32  # eg: drawing something on top of the ground
    GROUND_PIT             = 33
    GROUND_TRAPDOOR        = 34
    GROUND_TRAP            = 36

    def __str__(self):
        return self.name.lower()


def parse_asset_type(text: str) -> AssetTypes:
    return AssetTypes[text.strip().upper()]


def parse_sprite_role(text: str) -> SpriteRoles:
    return SpriteRoles[text.strip().upper()]


def main():
    print(str(AssetTypes.NPC))
    print(parse_asset_type('npc'))

    print([q for q in AssetTypes])


if __name__ == '__main__':
    main()

