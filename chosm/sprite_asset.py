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
from chosm.asset import Asset


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
            frame_idx_list = list(range(num_frames)) + list(reversed(range(num_frames - 1)))
        return AnimLoop(slugify.slugify(name), frame_idx_list, ms_per_frame, loop)

    def split(self, size_left):
        left = AnimLoop(self.slug, [f for f in self.frame_idx_list if f < size_left], self.ms_per_frame, self.loop)
        right = AnimLoop(self.slug, [f - size_left for f in self.frame_idx_list if f >= size_left],
                         self.ms_per_frame, self.loop)
        return left, right


class SpriteAsset(Asset):
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

    def num_frames(self) -> int:
        return len(self.frames)

    def crop(self, x, y, width, height, new_name=None):
        if self.size == (width, height):
            return self

        x2 = x + width
        y2 = y + height
        frames = [frame.crop((x, y, x2, y2)) for frame in self.frames]
        assert frames[0].width == width
        assert frames[0].height == height
        anim = [copy.deepcopy(a) for a in self.animations.values()]
        if new_name is None:
            new_name = self.name + "_cropped"
        sprite = SpriteAsset(self.file_id, new_name, frames, anim)
        return sprite

    def split(self,
              len_left_side: int,
              left_name: str = None, right_name: str = None,
              left_id: int = None, right_id: int = None) -> Tuple:
        left_frames = self.frames[:len_left_side]
        right_frames = self.frames[len_left_side:]
        split_anims = [a.split(len_left_side) for a in self.animations.values()]
        left_anims = [q[0] for q in split_anims]
        right_anims = [q[1] for q in split_anims]

        if left_id is None:
            left_id = self.file_id + 0xffffffff1 if self.file_id is not None else None
        if right_id is None:
            right_id = self.file_id + 0xffffffff2 if self.file_id is not None else None
        if left_name is None and self.name is not None:
            left_name = str(self.name) + "_left"
        if right_name is None and self.name is not None:
            right_name = str(self.name) + "_right"

        return SpriteAsset(left_id, left_name, left_frames, left_anims), \
            SpriteAsset(right_id, right_name, right_frames, right_anims)

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
            sprite_sheet_url = f"_anim_{a.slug}.png"

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
                     to  {{ background-position:    -{num_frames * self.width}px; }}
                }}

                """

            css += textwrap.dedent(cls_txt)

        # just the sprite sheet
        for i in range(self.num_frames()):
            frame_css = f"""

            .image_{self.slug}_frame_{i:04d} {{
                width: {self.width}px;
                height: {self.height}px;
                background-image: url('{sprite_sheet_url}');
                background-position:  {-i * self.width}px;
            }}
            """
            # position: absolute;
            css += textwrap.dedent(frame_css)

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
            anim_sheet.save(join(file_path, f"_anim_{anim.slug}.png"))

            # animated gif (seems prone to issues and has no transparency)
            # with open(join(file_path, f"anim_{anim.slug}.gif"), 'wb') as f:
            #     if anim.loop:
            #         imageio.mimsave(f, frames, format='gif', fps=anim.get_fps())
            #     else:
            #         imageio.mimsave(f, frames, format='gif', fps=anim.get_fps(), loop=0)

        # sprite sheet
        sprite_sheet = pih.join_images(self.frames, mode="RGBA", bg_col=[0, 0, 0, 0])
        sprite_sheet.save(join(file_path, "_sprite_sheet.png"))

        css = self._gen_css()
        with open(join(file_path, "_animation.css"), "wt") as f:
            f.write(css)

        # pl = ffmpeg.input(os.path.join(file_path, "frame_*.png"), pattern_type='glob', framerate=self.frame_rate)
        # pl = ffmpeg.output(pl, os.path.join(file_path, "anim.webp"))
        # ffmpeg.run(pl)

        #         ffmpeg -i input.mov -c:v libwebp_anim -filter:v fps=fps=20 -lossless 1 \
        #  -loop 0 -preset default -an -vsync 0 -vf \
        #  "scale=512:512:force_original_aspect_ratio=decrease,format=rgba,pad=512:512:-1:-1:color=#00000000" \
        #  output.webp


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

    return SpriteAsset(file_id, name, frames, ms_per_frame, ping_pong, loop)