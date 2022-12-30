from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    def as_array(self) -> List[int]:
        return [self.r, self.g, self.b]

    def as_html(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}".upper()

def color_from_6bit_rgb(r, g, b) -> Color:
    return Color(r << 2, g << 2, b << 2)

