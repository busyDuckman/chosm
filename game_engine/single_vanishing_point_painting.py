from functools import lru_cache

from PIL import Image, ImageDraw
import numpy as np
from typing import List
from sympy import Point, Line

def intersection(tp_line_a, tp_line_b):
    a = Line(*tp_line_a)
    b = Line(*tp_line_b)
    q = a.intersection(b)[0]
    # without the float(...), this returns sympy.core.numbers.something
    return float(q.x), float(q.y)


class SingleVanishingPointPainting:
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

        # how many steps away from the center line are tiles visible
        self.fov_table = [0] * (self.view_dist + 1)
        for step_f in range(self.view_dist):
            step_r = 0
            while True:
                mask = self.draw_mask(step_f, step_r, threshold=0)
                if mask is None:
                    break
                self.fov_table[step_f] = step_r
                step_r += 1


    def get_vp(self):
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        return (gnd_w / 2, horizon_y - (self.bird_eye_vs_worm_eye * gnd_h))

    def get_h_line(self, n):
        """
        Returns the horizontal lines.
        :param n: How many tiles forward.
        :return: A line as two points ((x1, y1), (x2, y2))
        """
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        depth = 0
        for i in range(n):
            depth += gnd_h / (2 ** (i + 1))
        return (0, self.height - depth), (gnd_w, self.height - depth)

    def get_p_line(self, n, right):
        """
        The line running from the base to the vanishing point.
        :param n: How many tiles across.
        :param right: True for the lines right of center, False for the lines left of center.
        :return: A line as two points ((x1, y1), (x2, y2))
        """
        vp = self.get_vp()
        horizon_y = int(self.horizon_screen_ratio * self.height)
        gnd_w, gnd_h = self.width, self.height - horizon_y
        local_tile_size = (gnd_w * self.local_tile_ratio) / 2
        x_middle = self.width / 2
        if right:
            p2 = (x_middle + (local_tile_size * (2 ** n - 1)), self.height)
        else:
            p2 = (x_middle - (local_tile_size * (2 ** n - 1)), self.height)

        return vp, p2

    @lru_cache()
    def get_tile_polygon(self, steps_fwd, steps_right):
        # TODO: This takes a unexpectedly long time to compute, I may need to change intersection library.
        #       For now, as there are only a few possible calls, the output is memoized.
        if steps_right == 0:
            # straddle the centre line
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

    def get_sprite_scale(self, steps_fwd: float) -> float:
        """
        Gets the sprite scale for a sprite according to its distance.
        :param steps_fwd: eg: For the middle of a tile2 steps forward use 2.5
        :return: A scale, assuming 100% to mean the sprite is directly in front of the camera.
        """
        local_tile_size = (self.width * self.local_tile_ratio) / 2
        vp_dist = self.get_vp()[1]

        # TODO: I have to thing about getting this right, the movable vanishing point complicates things.

        # for now
        return 1 / 2 ** steps_fwd


    def compose(self) -> Image.Image:
        """
        This is a helper to draw the image.
        used for debug/investigation purposes only.
        :return:
        """
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


