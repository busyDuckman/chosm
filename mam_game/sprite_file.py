import copy
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
from helpers.misc import is_continuous_integers
from mam_game.mam_constants import MAMVersion, Platform, MAMFileParseError, RawFile
from mam_game.mam_file import MAMFile
import helpers.stream_helpers as sh
import helpers.color as ch
from mam_game.pal_file import PalFile
import ffmpeg


@dataclass
class AnimLoop:
    slug: str
    frame_idx_list: List[int]
    ms_per_frame: float
    loop: bool

    def get_fps(self):
        frame_rate = 1_000 / self.ms_per_frame
        return frame_rate

    def get_seconds_per_loop(self):
        return (self.ms_per_frame * len(self.frame_idx_list)) / 1_000

    @staticmethod
    def make_simple(name: str, num_frames: int, ms_per_frame, loop: bool = True, ping_pong: bool = False):
        frame_idx_list = list(range(num_frames))
        if ping_pong:
            frame_idx_list = list(range(num_frames)) + list(reversed(range(num_frames-1)))
        return AnimLoop(slugify.slugify(name), frame_idx_list, ms_per_frame, loop)


class SpriteFile(MAMFile):
    def __init__(self, file_id, name,
                 frames: List[Image.Image],
                 animations: List[AnimLoop]
                 ):
        super().__init__(file_id, name)
        self.frames = frames
        self.width = frames[0].width
        self.height = frames[0].height

        self.size = (self.width, self.height)

        self.animations: Dict[str, AnimLoop] = {a.slug: a for a in animations}

        # uncomment to enable debug annotation of frames
        # self.frames = [pih.annotate(frame, f"frame: {i}") for i, frame in enumerate(frames)]

        for i, frame in enumerate(frames):
            if (frame.width, frame.height) != (self.width, self.height):
                raise ValueError(f"Sprite had inconsistent frame sizes: file_id={self.file_id}, frame_num={i}")

    def __str__(self):
        return f"sprite_file File: id={self.file_id} num_cols={len(self.colors)}"

    def get_type_name(self):
        return "sprite"

    def crop(self, x, y, width, height):
        if self.size == (width, height):
            return self

        x2 = x + width
        y2 = y + height
        frames = [frame.crop((x, y, x2, y2)) for frame in self.frames]
        assert frames[0].width == width
        assert frames[0].height == height
        anim = [copy.deepcopy(a) for a in self.animations.values()]
        sprite = SpriteFile(self.file_id, self.name+"_cropped", frames, anim)
        return sprite

    def _get_bake_dict(self):
        info = super()._get_bake_dict()
        info["width"] = self.width
        info["height"] = self.height
        info["num_frames"] = len(self.frames)

        def anim_dict(a: AnimLoop):
            d = asdict(a)
            d["fps"] = a.get_fps()
            d["seconds_per_loop"] = a.get_seconds_per_loop()
            return d

        info["animations"] = [anim_dict(a) for a in self.animations.values()]
        return info

    def _gen_preview_image(self, preview_size) -> Image.Image:
        img = self.frames[0]
        bounds = pih.image_bounds_transparent_background(img)
        img = img.crop(bounds)

        tn = pih.pad_image_to_make_square(img)
        if type(tn) == Tuple:
            print("?")
        tn = tn.resize((preview_size, preview_size))

        preview_img = Image.new(mode="RGB", size=(preview_size, preview_size), color=(0, 0, 0))
        preview_img.paste(tn, (0, 0), mask=tn)
        return preview_img

    def _gen_css(self):
        """
        I'm not that HTML savy, but it looks like a reliable cross browser animation is possible via css.
        Over animated compression formats, this approach seems to enable layered composition, sfx, and is
        performant (enough) without being taxing on client resources.

        So let's create a css file to animate the sprite-sheet, with a view to that being generally useful
        in early stage development.
        """
        total_w = self.width * len(self.frames)

        scale = 1

        css = ""
        for a in self.animations.values():
            loop_token = "infinite" if a.loop else "1"
            num_frames = len(a.frame_idx_list)
            sprite_sheet_url = f"anim_{a.slug}.png"

            cls_txt = f"""
                .anim_{self.slug}_{a.slug} {{
                    width: {self.width}px;
                    height: {self.height}px;
                    position: absolute;
                    background-image: url('{sprite_sheet_url}');
                    transform: scale({scale});
                    background-repeat: repeat-x;
                    animation-name: play_{self.slug}_{a.slug};
                    animation-duration: {a.get_seconds_per_loop()}s;
                    animation-timing-function: steps({num_frames});
                    animation-iteration-count: {loop_token};
                }}
                
                @keyframes play_{self.slug}_{a.slug} {{
                   from  {{ background-position:    0px; }}
                     to  {{ background-position:    -{num_frames*self.width}px; }}
                }}
                
                """

            css += textwrap.dedent(cls_txt)

        return css

    def bake(self, file_path):
        super().bake(file_path)

        # dump frames
        for i, frame in enumerate(self.frames):
            file = join(file_path, f"frame_{i:02d}.png")
            frame.save(file)

        # animations saved in various formats
        for anim in self.animations.values():
            frames = [self.frames[idx] for idx in anim.frame_idx_list]

            # frames to match the css animation
            anim_sheet = pih.join_images(frames, mode="RGBA", bg_col=[0, 0, 0, 0])
            anim_sheet.save(join(file_path, f"anim_{anim.slug}.png"))

            # animated gif (seems prone to issues and has no transparency)
            # with open(join(file_path, f"anim_{anim.slug}.gif"), 'wb') as f:
            #     if anim.loop:
            #         imageio.mimsave(f, frames, format='gif', fps=anim.get_fps())
            #     else:
            #         imageio.mimsave(f, frames, format='gif', fps=anim.get_fps(), loop=0)

        # sprite sheet
        sprite_sheet = pih.join_images(self.frames, mode="RGBA", bg_col=[0, 0, 0, 0])
        sprite_sheet.save(join(file_path, "sprite_sheet.png"))

        css = self._gen_css()
        with open(join(file_path, "animation.css"), "wt") as f:
            f.write(css)

        # pl = ffmpeg.input(os.path.join(file_path, "frame_*.png"), pattern_type='glob', framerate=self.frame_rate)
        # pl = ffmpeg.output(pl, os.path.join(file_path, "anim.webp"))
        # ffmpeg.run(pl)

        #         ffmpeg -i input.mov -c:v libwebp_anim -filter:v fps=fps=20 -lossless 1 \
        #  -loop 0 -preset default -an -vsync 0 -vf \
        #  "scale=512:512:force_original_aspect_ratio=decrease,format=rgba,pad=512:512:-1:-1:color=#00000000" \
        #  output.webp


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


def decode_cell_image(f, cell, pal: PalFile,
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




    # lineLength, byteCount = 0, 0 #  total bytes/bytes read in this scan line
    # opcode, cmd, len, opr1, opr2,  = 0, 0, 0, 0       # Used to decode the drawing commands



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


def load_sprite_file(raw_file: RawFile, pal: PalFile,
                  ver: MAMVersion, platform: Platform) -> SpriteFile:
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
        cell_a, cell_b = cell_offsets[i*2], cell_offsets[i*2+1]
        if cell_a == 0:
            raise MAMFileParseError(f"Invalid sprite: error='first cell can't be empty', frame={i}")

        frame_image = Image.new("RGBA", size=(frame_width, frame_height))
        cells = [cell_a] if cell_b == 0 else [cell_a, cell_b]
        for cell_offset in cells:
            cell, cell_image = cell_image_lut[cell_offset]
            x, y, _, _ = cell
            # frame_image.paste(cell_image, (x, 0), cell_image)
            frame_image.paste(cell_image, (0, 0), cell_image)
        frames.append(frame_image)

    animations = get_animations_in_ccfile_sprite(raw_file.file_name, len(frames), 66, ver, platform)
    return SpriteFile(raw_file.file_id, raw_file.file_name, frames, animations)


def sprite_from_baked_folder(folder: str):
    with open(os.path.join(folder, "info.json"), "r") as f:
        info = json.load(f)

    ms_per_frame = int(info["ms_per_frame"])
    ping_pong = bool(info["ping_pong"])
    loop = bool(info["loop"])
    width = int(info["width"])
    height = int(info["height"])
    file_id = int(info["id"])
    name = str(info["name"])
    t = str(info["type"])

    frame_files = sorted(glob.glob(os.path.join(folder, "frame_*.png")))
    print(frame_files)
    frames = [Image.load(f) for f in frame_files]

    return SpriteFile(file_id, name, frames, ms_per_frame, ping_pong, loop)
