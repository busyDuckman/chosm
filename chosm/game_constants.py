from enum import Enum

# building block things that need to be broadly importable without creating circular dependencies/


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


def parse_asset_type(text: str):
    return AssetTypes[text.strip().upper()]


def main():
    print(str(AssetTypes.NPC))
    print(parse_asset_type('npc'))

    print([q for q in AssetTypes])


if __name__ == '__main__':
    main()

