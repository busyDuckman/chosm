from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    def as_array(self):
        return [self.r, self.g, self.b]


def color_from_6bit_rgb(r, g, b) -> Color:
    return Color(r << 2, g << 2, b << 2)

