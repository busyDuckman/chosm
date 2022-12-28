from dataclasses import dataclass
from enum import Enum
from typing import List

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


def map_slug(maze_id: int):
    maze_id = int(maze_id)
    return f"map_{maze_id:08}"


def spell_slug(spell_name: str):
    "".join(c for c in str(spell_name) if c.isalpha() or c.isspace())
    s = slugify.slugify(spell_name)
    while "--" in s:
        s = s.replace("--", "-")
    return f"spell-"

