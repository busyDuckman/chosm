from functools import lru_cache

from PIL import Image, ImageDraw
import numpy as np
from typing import List
from sympy import Point, Line

def intersection(tp_line_a, tp_line_b):
    a = Line(*tp_line_a)
    b = Line(*tp_line_b)
    q = a.intersection(b)[0]
    return (q.x, q.y)


class SingleVanishingPointPainting():
    def __init__(self, ground_images: List[Image.Image], sky_images: List[Image.Image],
                 view_dist=5,
                 size=None, horizon_screen_ratio=0.5, local_tile_ratio=0.9, bird_eye_vs_worm_eye=0):
        self.ground_images: List[Image.Image] = ground_images
        self.sky_images: List[Image.Image] = sky_images

        if size is None:
            size = (self.ground_images[0].width, self.ground_images[0].height + self.sky_images[0].height)
        self.size = size
        self.width, self.height = self.size

        self.horizon_screen_ratio = horizon_screen_ratio
        self.local_tile_ratio = local_tile_ratio
        self.bird_eye_vs_worm_eye = bird_eye_vs_worm_eye
        self.view_dist: int = view_dist

    def get_vp(self):
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        return (gnd_w / 2, horizon_y - (self.bird_eye_vs_worm_eye * gnd_h))

    def get_h_line(self, n):
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        depth = 0
        for i in range(n):
            depth += gnd_h / (2 ** (i + 1))
        return ((0, self.height - depth), (gnd_w, self.height - depth))

    def get_p_line(self, n, right):
        vp = self.get_vp()
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        local_tile_size = (gnd_w * self.local_tile_ratio) / 2
        x_middle = self.width / 2
        if right:
            return (vp, (x_middle + (local_tile_size * (2 ** n - 1)), self.height))
        else:
            return (vp, (x_middle - (local_tile_size * (2 ** n - 1)), self.height))

    def get_tile_polygon(self, steps_fwd, steps_right):
        if steps_right == 0:
            # stradele the centre line
            p_line_1 = self.get_p_line(1, True)
            p_line_2 = self.get_p_line(1, False)
        else:
            x = abs(steps_right)
            is_right = steps_right > 0
            p_line_1 = self.get_p_line(x, is_right)
            p_line_2 = self.get_p_line(x + 1, is_right)

        h_line_1 = self.get_h_line(steps_fwd)
        h_line_2 = self.get_h_line(steps_fwd + 1)
        a = intersection(p_line_1, h_line_1)
        b = intersection(p_line_2, h_line_1)
        c = intersection(p_line_2, h_line_2)
        d = intersection(p_line_1, h_line_2)
        return [a, b, c, d]

    def compose(self) -> Image.Image:
        # screen space
        horizon_y = int(self.horizon_screen_ratio * self.height)

        sky_w, sky_h = self.width, horizon_y
        sky_box = (0, 0, sky_w, sky_h)
        sky = self.sky_images[0].resize((sky_w, sky_h))

        gnd_w, gnd_h = self.width, self.height - horizon_y
        gnd_box = (0, horizon_y, gnd_w, horizon_y + gnd_h)
        gnd = self.ground_images[3].resize((gnd_w, gnd_h))

        img = Image.new(mode="RGB", size=self.size)
        img.paste(sky, (sky_box[0], sky_box[1]))
        img.paste(gnd, (gnd_box[0], gnd_box[1]))

        vp = self.get_vp()
        # vp = (gnd_w/2, horizon_y)
        local_tile_size = (gnd_w * self.local_tile_ratio) / 2

        draw = ImageDraw.Draw(img, "RGBA")
        depth = 0
        for i in range(self.view_dist):
            # drawing from nearest to furthest
            depth += gnd_h / (2 ** (i + 1))
            draw.line((0, self.height - depth, gnd_w, self.height - depth), fill=(128, 0, 255))

        x_middle = self.width / 2
        for i in range(1, 6):
            draw.line(vp + (x_middle + local_tile_size * (2 ** i - 1), self.height), fill=(0, 255, 128))
            draw.line(vp + (x_middle - local_tile_size * (2 ** i - 1), self.height), fill=(0, 255, 128))

        #         draw.line((0, horizon_y, w, horizon_y), fill=(128, 0, 255))
        draw.polygon(self.get_tile_polygon(0, 0), fill=(0, 64, 128, 64))
        draw.polygon(self.get_tile_polygon(1, 0), fill=(255, 64, 128, 64))
        draw.polygon(self.get_tile_polygon(2, 0), fill=(0, 255, 128, 64))

        #         draw.polygon(self.get_tile_polygon(2, 1), fill = (0, 64, 255, 64))
        #         draw.polygon(self.get_tile_polygon(2, -1), fill = (255, 64, 0, 64))
        del draw

        # img.paste(sky, (sky_box[0], sky_box[1]))

        return img

    def draw_mask(self, steps_fwd, steps_right, threshold=0):
        img = Image.new(mode="L", size=self.size, color=0)
        draw = ImageDraw.Draw(img, "L")
        poly = self.get_tile_polygon(steps_fwd, steps_right)
        draw.polygon(poly, fill=255)
        del draw
        if np.array(img).flatten().sum() <= threshold:
            # note: "<=" because 0 is important for detecting masks that were entirely off the image.
            return None  # this tile did not (significantly) appear on the image

        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        gnd_box = (0, horizon_y, gnd_w, horizon_y + gnd_h)
        img = img.crop(gnd_box)
        return img


@lru_cache(maxsize=64)
def get_ground_overlay(steps_fwd, steps_right,
                       view_dist=5, size=(1280, 720), horizon_screen_ratio=0.5, local_tile_ratio=0.9, bird_eye_vs_worm_eye=0):
    svp_composer = SingleVanishingPointPainting([], [], size=size,
                                                bird_eye_vs_worm_eye=bird_eye_vs_worm_eye, view_dist=view_dist,
                                                horizon_screen_ratio=horizon_screen_ratio, local_tile_ratio=local_tile_ratio)

    svp_composer.draw_mask(steps_fwd, steps_right)


