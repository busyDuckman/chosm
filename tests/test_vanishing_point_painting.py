from unittest import TestCase

import numpy as np

from game_engine.single_vanishing_point_painting import SingleVanishingPointPainting, intersection

W, H = 1920, 1024


def make_svp(**kwargs) -> SingleVanishingPointPainting:
    settings = dict(size=(W, H), view_dist=6, horizon_screen_ratio=0.5, local_tile_ratio=0.9, bird_eye_vs_worm_eye=0)
    settings.update(kwargs)
    return SingleVanishingPointPainting([], [], **settings)


def assert_points_equal(test: TestCase, p, q):
    test.assertAlmostEqual(p[0], q[0], places=6)
    test.assertAlmostEqual(p[1], q[1], places=6)


class TestIntersection(TestCase):
    def test_crossing_lines(self):
        assert_points_equal(self, intersection(((0, 0), (2, 2)), ((0, 2), (2, 0))), (1, 1))
        # lines are infinite, so they can meet outside the given points
        assert_points_equal(self, intersection(((0, 0), (1, 0)), ((5, -1), (5, 1))), (5, 0))

    def test_parallel_lines(self):
        with self.assertRaises(ValueError):
            intersection(((0, 0), (1, 1)), ((0, 1), (1, 2)))


class TestTileGeometry(TestCase):
    def setUp(self):
        self.svp = make_svp()

    def test_vanishing_point_is_centred_on_the_horizon(self):
        assert_points_equal(self, self.svp.get_vp(), (W / 2, H / 2))

    def test_tile_in_front_is_symmetric(self):
        a, b, c, d = self.svp.get_tile_polygon(0, 0)
        self.assertAlmostEqual(a[0] - W / 2, W / 2 - b[0])
        self.assertAlmostEqual(d[0] - W / 2, W / 2 - c[0])

    def test_rows_get_narrower_and_closer_to_the_horizon(self):
        widths, tops = [], []
        for f in range(self.svp.view_dist):
            a, b, c, d = self.svp.get_tile_polygon(f, 0)
            widths.append(abs(a[0] - b[0]))
            tops.append(min(p[1] for p in (a, b, c, d)))
        self.assertEqual(widths, sorted(widths, reverse=True))
        self.assertEqual(tops, sorted(tops, reverse=True))
        self.assertTrue(all(t > H / 2 for t in tops), "the ground should never reach the horizon")

    def test_neighbouring_tiles_share_edges(self):
        for f in range(4):
            here = self.svp.get_tile_polygon(f, 0)
            right = self.svp.get_tile_polygon(f, 1)
            further = self.svp.get_tile_polygon(f + 1, 0)
            # the right edge of the centre tile is the left edge of the tile to its right
            assert_points_equal(self, here[0], right[0])
            assert_points_equal(self, here[3], right[3])
            # the far edge of a tile is the near edge of the tile beyond it
            assert_points_equal(self, here[2], further[1])
            assert_points_equal(self, here[3], further[0])

    def test_field_of_view_widens_with_distance(self):
        fov = self.svp.fov_table[:self.svp.view_dist]
        self.assertEqual(fov, sorted(fov))
        self.assertGreater(fov[-1], fov[0])

    def test_sprites_halve_in_size_each_step(self):
        for f in range(1, 5):
            self.assertAlmostEqual(self.svp.get_sprite_scale(f), self.svp.get_sprite_scale(f - 1) / 2)


class TestGroundMasks(TestCase):
    def setUp(self):
        self.svp = make_svp()

    def test_mask_covers_the_ground_half_of_the_screen(self):
        mask = self.svp.draw_mask(0, 0)
        self.assertEqual(mask.mode, "L")
        self.assertEqual(mask.size, (W, H // 2))

    def test_masks_in_a_row_do_not_overlap(self):
        left, centre, right = [self.svp.draw_mask(1, r) for r in (-1, 0, 1)]
        for a, b in [(left, centre), (centre, right)]:
            overlap = np.logical_and(np.array(a) > 0, np.array(b) > 0).sum()
            # polygons drawn separately share their boundary pixels, but no more than that
            self.assertLess(overlap, H)

    def test_off_screen_tile_has_no_mask(self):
        self.assertIsNone(self.svp.draw_mask(0, 50))
