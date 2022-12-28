from unittest import TestCase

import os
from PIL import Image

import helpers.pil_image_helpers as pih


class Test(TestCase):
    def test_image_bounds_transparent_background(self):
        print(os.getcwd())
        with Image.open("test_data/example_sprite.png") as img:
            w, h = img.size
            bounds = pih.image_bounds_transparent_background(img)
            print(bounds)
            x, y, x2, y2 = bounds
            self.assertGreater(x, 10)
            self.assertGreater(y, 10)
            self.assertLess(x2, w-10)
            self.assertLess(y2, h - 10)
            img.crop(bounds).save("test_data/example_sprite_cropped_test.png")

        with Image.open("test_data/example_sprite_cropped_test.png") as img:
            w, h = img.size
            x, y, x2, y2 = pih.image_bounds_transparent_background(img)
            self.assertEqual(x, 0)
            self.assertEqual(y, 0)
            self.assertEqual(x2, w)
            self.assertEqual(y2, h)

            pih.pad_image_to_make_square(img).save("test_data/example_sprite_preview_image.png")


        # self.fail()
