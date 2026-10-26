from unittest import TestCase

import tempfile
from PIL import Image, ImageDraw

import helpers.pil_image_helpers as pih


def make_test_sprite() -> Image.Image:
    """
    A sprite-like image: a shape on a transparent background, with a margin all round.
    """
    img = Image.new("RGBA", (240, 140), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((60, 20, 180, 120), fill=(140, 40, 200, 255))
    draw.line((30, 70, 210, 70), fill=(90, 20, 140, 255), width=6)
    return img


class Test(TestCase):
    def test_image_bounds_transparent_background(self):
        out_dir = tempfile.mkdtemp()
        with make_test_sprite() as img:
            w, h = img.size
            bounds = pih.image_bounds_transparent_background(img)
            x, y, x2, y2 = bounds
            self.assertGreater(x, 10)
            self.assertGreater(y, 10)
            self.assertLess(x2, w-10)
            self.assertLess(y2, h - 10)
            img.crop(bounds).save(f"{out_dir}/example_sprite_cropped_test.png")

        with Image.open(f"{out_dir}/example_sprite_cropped_test.png") as img:
            w, h = img.size
            x, y, x2, y2 = pih.image_bounds_transparent_background(img)
            self.assertEqual(x, 0)
            self.assertEqual(y, 0)
            self.assertEqual(x2, w)
            self.assertEqual(y2, h)

            pih.pad_image_to_make_square(img).save(f"{out_dir}/example_sprite_preview_image.png")


        # self.fail()
