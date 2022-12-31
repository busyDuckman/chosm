from chosm.pal_asset import PalAsset
from helpers.color import Color, color_from_6bit_rgb
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, RawFile


def load_pal_file(raw_file: RawFile, ver: MAMVersion, platform: Platform) -> PalAsset:
    if len(raw_file.data) != (256 * 3):
        raise MAMFileParseError(raw_file, "Must be 768 bytes in a wox/mm3 palette")

    # load data
    colors = [tuple(raw_file.data[i*3:i*3+3]) for i in range(256)]

    # check it is a 6 bit palette
    for i, (r, g, b) in enumerate(colors):
        if any(q >= 2**6 for q in [r, g, b]):
            raise MAMFileParseError(raw_file, f"Palette was > 6bit: pos={i}, color={(r, g, b)}")

    colors = [color_from_6bit_rgb(r, g, b) for r, g, b in colors]
    return PalAsset(raw_file.file_id, raw_file.file_name, colors)


def get_default_pal(ver: MAMVersion, platform: Platform):
    if ver == MAMVersion.DARKSIDE:
        return PalAsset(0x10001, "default.pal", _get_default_pal_xeen())
    elif ver == MAMVersion.CLOUDS:
        return PalAsset(0x10001, "default.pal", _get_default_pal_xeen())
    elif ver == MAMVersion.MM3:
        return PalAsset(0x10001, "default.pal", _get_default_pal_xeen())
    else:
        return None


def _get_default_pal_xeen():
    return [Color(0, 0, 0),  Color(252, 252, 252),  Color(244, 244, 244),  Color(236, 236, 236),  Color(228, 228, 228),  Color(220, 220, 220),
            Color(212, 212, 212),  Color(204, 204, 204),  Color(196, 196, 196),  Color(188, 188, 188),  Color(180, 180, 180),  Color(172, 172, 172),
            Color(164, 164, 164),  Color(156, 156, 156),  Color(148, 148, 148),  Color(140, 140, 140),  Color(132, 132, 132),  Color(124, 124, 124),
            Color(116, 116, 116),  Color(108, 108, 108),  Color(100, 100, 100),  Color(92, 92, 92),  Color(84, 84, 84),  Color(76, 76, 76),
            Color(68, 68, 68),  Color(60, 60, 60),  Color(52, 52, 52),  Color(44, 44, 44),  Color(36, 36, 36),  Color(28, 28, 28),
            Color(20, 20, 20),  Color(12, 12, 12),  Color(224, 236, 252),  Color(204, 228, 252),  Color(180, 212, 252),  Color(156, 192, 252),
            Color(132, 172, 252),  Color(112, 148, 252),  Color(88, 124, 252),  Color(64, 96, 252),  Color(40, 64, 252),  Color(28, 48, 228),
            Color(20, 36, 208),  Color(16, 28, 184),  Color(8, 16, 164),  Color(4, 8, 140),  Color(0, 4, 120),  Color(0, 0, 96),
            Color(248, 252, 192),  Color(244, 252, 164),  Color(244, 252, 136),  Color(244, 252, 108),  Color(236, 248, 76),  Color(232, 240, 60),
            Color(224, 228, 44),  Color(216, 220, 32),  Color(200, 204, 16),  Color(188, 192, 4),  Color(176, 172, 0),  Color(156, 148, 0),
            Color(136, 128, 0),  Color(112, 104, 0),  Color(92, 84, 0),  Color(76, 64, 0),  Color(196, 232, 252),  Color(172, 220, 248),
            Color(148, 208, 244),  Color(124, 196, 244),  Color(100, 188, 240),  Color(80, 176, 236),  Color(56, 164, 236),  Color(36, 152, 232),
            Color(16, 144, 228),  Color(0, 132, 228),  Color(0, 120, 208),  Color(0, 108, 188),  Color(0, 92, 164),  Color(0, 80, 144),
            Color(0, 68, 120),  Color(0, 56, 100),  Color(212, 248, 204),  Color(192, 248, 180),  Color(172, 248, 156),  Color(152, 248, 132),
            Color(128, 244, 104),  Color(104, 236, 80),  Color(84, 224, 56),  Color(56, 216, 32),  Color(52, 208, 24),  Color(44, 192, 16),
            Color(36, 176, 12),  Color(28, 160, 8),  Color(20, 144, 4),  Color(16, 128, 0),  Color(12, 112, 0),  Color(8, 96, 0),
            Color(188, 248, 252),  Color(168, 236, 240),  Color(152, 224, 228),  Color(136, 212, 216),  Color(120, 200, 204),  Color(104, 192, 192),
            Color(92, 180, 180),  Color(80, 168, 172),  Color(68, 160, 160),  Color(60, 144, 148),  Color(56, 132, 136),  Color(48, 116, 124),
            Color(44, 104, 112),  Color(36, 92, 100),  Color(32, 80, 88),  Color(28, 68, 76),  Color(240, 216, 252),  Color(228, 184, 248),
            Color(216, 156, 244),  Color(204, 128, 240),  Color(192, 100, 240),  Color(180, 72, 236),  Color(172, 44, 232),  Color(160, 20, 228),
            Color(144, 0, 220),  Color(136, 0, 208),  Color(120, 0, 188),  Color(104, 0, 168),  Color(92, 0, 148),  Color(76, 0, 128),
            Color(64, 0, 108),  Color(52, 0, 88),  Color(252, 216, 252),  Color(248, 184, 248),  Color(244, 156, 244),  Color(240, 128, 240),
            Color(236, 100, 240),  Color(232, 72, 236),  Color(232, 44, 232),  Color(220, 20, 224),  Color(212, 0, 216),  Color(204, 0, 208),
            Color(184, 0, 188),  Color(164, 0, 168),  Color(144, 0, 148),  Color(124, 0, 128),  Color(108, 0, 108),  Color(88, 0, 88),
            Color(252, 232, 220),  Color(244, 220, 208),  Color(240, 212, 196),  Color(236, 204, 184),  Color(232, 196, 172),  Color(228, 184, 160),
            Color(220, 176, 148),  Color(216, 168, 140),  Color(212, 160, 128),  Color(208, 152, 120),  Color(204, 144, 108),  Color(196, 140, 100),
            Color(192, 132, 92),  Color(188, 124, 84),  Color(184, 116, 76),  Color(180, 112, 68),  Color(172, 108, 64),  Color(164, 104, 60),
            Color(160, 100, 56),  Color(152, 96, 56),  Color(144, 92, 52),  Color(140, 88, 48),  Color(132, 84, 48),  Color(128, 80, 44),
            Color(120, 76, 40),  Color(112, 72, 40),  Color(108, 68, 36),  Color(100, 64, 32),  Color(92, 60, 32),  Color(88, 56, 28),
            Color(80, 52, 24),  Color(76, 48, 24),  Color(252, 212, 212),  Color(244, 184, 184),  Color(236, 160, 160),  Color(232, 136, 136),
            Color(224, 112, 112),  Color(216, 92, 92),  Color(212, 68, 68),  Color(204, 48, 48),  Color(200, 32, 32),  Color(192, 20, 20),
            Color(184, 8, 8),  Color(168, 0, 0),  Color(148, 0, 0),  Color(128, 0, 0),  Color(108, 0, 0),  Color(88, 0, 0),  Color(252, 220, 188),
            Color(252, 208, 164),  Color(252, 196, 140),  Color(252, 184, 116),  Color(252, 176, 92),  Color(252, 164, 68),  Color(252, 152, 44),
            Color(248, 140, 20),  Color(236, 128, 8),  Color(220, 120, 4),  Color(204, 108, 0),  Color(180, 96, 0),  Color(156, 80, 0),
            Color(132, 68, 0),  Color(108, 56, 0),  Color(88, 44, 0),  Color(196, 248, 52),  Color(180, 232, 40),  Color(168, 220, 32),
            Color(152, 208, 20),  Color(140, 192, 12),  Color(128, 180, 8),  Color(116, 168, 0),  Color(104, 156, 0),  Color(68, 144, 0),
            Color(32, 136, 0),  Color(4, 124, 0),  Color(0, 116, 8),  Color(0, 104, 28),  Color(0, 96, 44),  Color(0, 84, 56),
            Color(0, 76, 68),  Color(64, 44, 28),  Color(48, 36, 28),  Color(88, 128, 12),  Color(36, 64, 8),  Color(24, 60, 68),
            Color(20, 52, 60),  Color(236, 232, 0),  Color(220, 208, 0),  Color(208, 188, 0),  Color(196, 168, 0),  Color(184, 152, 0),
            Color(172, 136, 0),  Color(156, 120, 0),  Color(144, 104, 0),  Color(132, 88, 0),  Color(120, 76, 0),  Color(252, 156, 0),
            Color(252, 176, 0),  Color(252, 196, 0),  Color(252, 216, 0),  Color(252, 240, 0),  Color(244, 252, 0),  Color(252, 228, 0),
            Color(252, 200, 0),  Color(252, 172, 0),  Color(252, 140, 0),  Color(252, 112, 0),  Color(252, 84, 0),  Color(252, 52, 0),
            Color(252, 24, 0),  Color(252, 0, 0),  Color(252, 252, 252)]
