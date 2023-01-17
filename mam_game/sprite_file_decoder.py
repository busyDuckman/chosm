import copy
import glob
import io
import json
import logging
import os.path
from typing import List, Dict, Tuple, Any
from PIL import Image

from chosm.sprite_asset import AnimLoop, SpriteAsset
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, RawFile
import helpers.stream_helpers as sh
import helpers.color as ch
from chosm.pal_asset import PalAsset


def read_cell(f, raw_file: RawFile):
    fmt = [sh.DType.U_INT_16, sh.DType.U_INT_16, sh.DType.U_INT_16, sh.DType.U_INT_16]
    x, width, y, height = [q.read(f) for q in fmt]

    # validate
    if not(0 <= x < 1024):
        raise MAMFileParseError(raw_file, f"Invalid Frame Cell: condition='0 <= x < 1024', x={x}")
    if not(0 <= y < 1024):
        raise MAMFileParseError(raw_file, f"Invalid Frame Cell: condition='0 <= y < 1024', y={y}")
    if not(0 < width < 1024):
        raise MAMFileParseError(raw_file, f"Invalid Frame Cell: condition='0 < width < 1024', width={width}")
    if not(0 < height < 1024):
        raise MAMFileParseError(raw_file, f"Invalid Frame Cell: condition='0 < height < 1024', height={height}")

    return x, y, width, height


def decode_line(f, f_end, raw_file: RawFile):
    # Note: using naming conventions consistent with the source doco
    pixels = []
    line_offset = sh.read_byte(f)

    # The pattern steps used in the pattern command
    pattern_steps = [0, 1, 1, 1, 2, 2, 3, 3, 0, -1, -1, -1, -2, -2, -3, -3]

    while f.tell() < f_end:
        opcode = sh.read_byte(f)
        cmd = (opcode & 0xE0) >> 5
        param_len = opcode & 0x1F

        match cmd:
            case 0 | 1:
                # raw byte mode
                for _ in range(opcode+1):   # yep, it's "opcode", not a typo
                    pixels.append(sh.read_byte(f))
            case 2:
                # rle mode
                p = sh.read_byte(f)
                for _ in range(param_len + 3):
                    pixels.append(p)
            case 3:
                # copy previous data (stream copy)
                opr1 = sh.read_uint16(f)
                f_here = f.tell()
                f.seek(f_here-opr1)
                for _ in range(param_len+4):
                    pixels.append(sh.read_byte(f))
                f.seek(f_here)
            case 4:
                # RLE 2 byte pattern
                opr1 = sh.read_byte(f)
                opr2 = sh.read_byte(f)
                for _ in range(param_len + 2):
                    pixels.append(opr1)
                    pixels.append(opr2)
            case 5:
                # RLE transparent run, seems redundant, because command 2, but if I recall old school
                # sprite algorithms, this removed the need for a significant amount of time in a memcpy loop.
                for _ in range(param_len + 1):
                    pixels.append(0)
            case 6 | 7:
                # pattern command (different opcode format)
                # Not 100% on what is going on. I think its using the fact that sprites tend to have shading effects
                # and those shading effects tended to use adjacent palette entries (because that's how old school
                # palettes were organised).
                cmd = (opcode >> 2) & 0x0E
                param_len = opcode & 0x07
                opr1 = sh.read_byte(f)
                for i in range(param_len + 3):
                    pixels.append(opr1)
                    opr1 += pattern_steps[cmd + (i % 2)]

    return pixels, line_offset


def decode_cell_image(f, cell, pal: PalAsset,
                      raw_file: RawFile,
                      ver: MAMVersion, platform: Platform) -> Image.Image:
    # https://github.com/busyDuckman/OpenXeen/blob/ffb78839bcdd49d8fa1fd7002b5b0f5e2146ce57/src/main/java/mamFiles/WOX/WOXSpriteFile.java#L23
    # https://xeen.fandom.com/wiki/Sprite_File_Format
    x_offset, y_offset, width, height = cell
    total_width = width + x_offset
    total_height = height + y_offset
    img = Image.new(mode="RGBA", size=(total_width, total_height))
    transparent_index = 0

    y_iter = iter(range(y_offset, total_height))
    for y_pos in y_iter:
        line_length = sh.read_byte(f)  # bytes in this (encoded) scan line.
        f_end = f.tell() + line_length

        if line_length == 0:
            # the skip line(s) command
            lines_to_skip = sh.read_byte(f)
            for _ in range(lines_to_skip):
                next(y_iter)
            continue
        else:
            pixels, line_offset = decode_line(f, f_end, raw_file)
            for i, p in enumerate(pixels):
                if p != transparent_index:
                    x_pos = x_offset + line_offset + i
                    img.putpixel((x_pos, y_pos), pal.colors_rgb[p])

            if f.tell() != f_end:
                raise MAMFileParseError(raw_file, f"Sprite line error: decoded line not of stated size.")

    return img


def ping_pong(frames):
    if len(frames) < 2:
        return frames
    return frames + frames[-2::-1]


def get_animations_in_ccfile_sprite(f_name, num_frames, ms_per_frame,
                                    ver: MAMVersion, platform: Platform) -> List[AnimLoop]:
    ext = os.path.splitext(f_name)[1].lower().strip(".")
    frame_list = list(range(num_frames))
    if ext == 'att':
        return [AnimLoop("attack", frame_list[:-1], ms_per_frame, False),
                AnimLoop("hit",    frame_list[-1:], ms_per_frame, True)]
    if ext == 'fac':
        if num_frames == 5:
            # character face
            return [AnimLoop("face",  frame_list[0:1], ms_per_frame, True),
                    AnimLoop("sick",  frame_list[1:2], ms_per_frame, True),
                    AnimLoop("weary", frame_list[2:3], ms_per_frame, True),
                    AnimLoop("sleep", frame_list[3:4], ms_per_frame, True),
                    AnimLoop("crazy", frame_list[-1:], ms_per_frame, True)]
        else:
            # talking head
            [AnimLoop("talk", frame_list, ms_per_frame, True)]
    if ext == 'mon':
        return [AnimLoop("idle", ping_pong(frame_list), ms_per_frame, True)]

    return [AnimLoop("idle", frame_list, ms_per_frame, True)]


def load_sprite_file(raw_file: RawFile, pal: PalAsset,
                     ver: MAMVersion, platform: Platform) -> SpriteAsset:
    f = io.BytesIO(bytearray(raw_file.data))

    # get the number of frames
    num_frames = sh.read_uint16(f)
    if not (0 < num_frames < 1024):
        raise MAMFileParseError(raw_file, f"Invalid sprite: condition='0 < num_frames < 1024', num_frames={num_frames}")

    # Pairs of 16bit offsets for n * 4 cells.from
    # Each frame is a combination of up to two cells - one drawn over top the other.
    # The first offset is never zero, second being zero indicates one cell in the frame.
    cell_offsets = sh.read_uint16_array(f, num_frames*2)
    unique_offsets = [x for x in sorted(list(set(cell_offsets))) if x != 0]
    if any(x > len(raw_file.data) for x in unique_offsets):
        raise MAMFileParseError(raw_file, f"Invalid sprite: cell offset after end of file.")

    # load the cells
    cell_image_lut: Dict[int, Tuple[Any, Image.Image]] = {}
    for offset in unique_offsets:
        f.seek(offset)
        cell = read_cell(f, raw_file)
        cell_image = decode_cell_image(f, cell, pal, raw_file, ver, platform)
        cell_image_lut[offset] = (cell, cell_image)

    # find the frame dimensions TODO: not sure is supposed to get min x/y
    frame_width = max(x + w for (x, y, w, h), _ in cell_image_lut.values())
    frame_height = max(y + h for ((x, y, w, h), _) in cell_image_lut.values())

    # create the frames
    frames = []
    for i in range(num_frames):
        frame_image = Image.new("RGBA", size=(frame_width, frame_height))

        cell_a, cell_b = cell_offsets[i*2], cell_offsets[i*2+1]
        if cell_a == 0:
            # raise MAMFileParseError(raw_file, f"Invalid sprite: error='first cell can't be empty', frame={i}")
            logging.warning("First frame of sprite was empty: file="+str(raw_file))
        else:
            cells = [cell_a] if cell_b == 0 else [cell_a, cell_b]
            for cell_offset in cells:
                cell, cell_image = cell_image_lut[cell_offset]
                x, y, _, _ = cell
                # frame_image.paste(cell_image, (x, 0), cell_image)
                frame_image.paste(cell_image, (0, 0), cell_image)
        frames.append(frame_image)

    animations = get_animations_in_ccfile_sprite(raw_file.file_name, len(frames), 66, ver, platform)
    return SpriteAsset(raw_file.file_id, raw_file.file_name, frames, animations)


