from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

import slugify


class MAMVersion(Enum):
    CLOUDS = 4
    DARKSIDE = 5
    MM3 = 3

    def is_WOX(self):
        return self in [MAMVersion.CLOUDS, MAMVersion.DARKSIDE]

    def __str__(self):
        return self.name.lower()


class Platform(Enum):
    PC_DOS = 0

    def __str__(self):
        return self.name.lower()


@dataclass
class RawFile:
    file_id: int
    file_name: str
    data: List

    def __str__(self):
        return f"file_{self.file_id}_{self.file_name}"

    def __repr__(self):
        return str(self)


class MAMFileParseError(Exception):
    def __init__(self, raw_file: RawFile, message):
        if raw_file is None:
            self.message = f"File parse error: error='{message}'"
        else:
            self.file_id = str(raw_file.file_id)
            self.file_name = str(raw_file.file_name)
            message = str(message)
            self.message = f"File parse error: file_id={self.file_id}, file={self.file_name}, error='{message}'"
        super().__init__(self.message)


def normalise_file_name(name: str):
    """
    To assist in using file names as keys in dictionaries etc.
    """
    return name.strip().lower()


def spell_slug(spell_name: str):
    "".join(c for c in str(spell_name) if c.isalpha() or c.isspace())
    s = slugify.slugify(spell_name)
    while "--" in s:
        s = s.replace("--", "-")
    return f"spell-"


class Direction(Enum):
    NORTH = 0
    EAST  = 1
    SOUTH = 2
    WEST  = 3

    def other_way(self):
        return Direction((self.value+2) % 4)

    def right(self):
        return Direction((self.value+1) % 4)

    def left(self):
        return Direction((self.value-1) % 4)

    def as_vec(self):
        return [(0, 1), (1, 0), (0, -1), (-1, 0)][self.value]

    def apply(self, x: int, y: int) -> Tuple[int, int]:
        vec = self.as_vec()
        return x+vec[0], y+vec[1]

