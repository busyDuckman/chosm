from unittest import TestCase

from game_engine.map import MapInstance, load_map_from_dict
from mam_game.mam_constants import Direction

GRASS, WATER, ROAD = 0, 1, 2
NOTHING, TREE, MOUNTAIN = 0, 1, 2


def make_map(ground_rows, env_rows) -> MapInstance:
    """
    A small map from rows of ground / env indices, row 0 is y=0.
    """
    h, w = len(ground_rows), len(ground_rows[0])
    tiles = [[ground_rows[y][x], env_rows[y][x]] for y in range(h) for x in range(w)]
    base = load_map_from_dict({
        "name": "test",
        "width": w,
        "height": h,
        "layer_names": ["ground", "env"],
        "luts": [{"name": "ground", "mapping": {GRASS: "sprite-grass-srf-flat",
                                                 WATER: "sprite-water-srf-flat",
                                                 ROAD: "sprite-road-srf-flat"}},
                 {"name": "env", "mapping": {NOTHING: None,
                                              TREE: "sprite-ltree-wal",
                                              MOUNTAIN: "sprite-mount-wal"}}],
        "map": tiles,
    })
    return MapInstance(base)


class TestCanMoveTo(TestCase):
    def setUp(self):
        self.map = make_map(ground_rows=[[GRASS, WATER, ROAD],
                                         [GRASS, GRASS, GRASS]],
                            env_rows=[[NOTHING, NOTHING, NOTHING],
                                      [TREE, MOUNTAIN, NOTHING]])

    def test_open_ground(self):
        self.assertTrue(self.map.can_move_to(0, 0, Direction.NORTH))
        self.assertTrue(self.map.can_move_to(2, 0, Direction.NORTH))

    def test_trees_are_passable(self):
        self.assertTrue(self.map.can_move_to(0, 1, Direction.NORTH))

    def test_water_and_mountains_block(self):
        water = self.map.can_move_to(1, 0, Direction.NORTH)
        self.assertFalse(water)
        self.assertIn("Swimming", water.why)

        mountain = self.map.can_move_to(1, 1, Direction.NORTH)
        self.assertFalse(mountain)
        self.assertIn("Mountaineering", mountain.why)

    def test_map_edge(self):
        for x, y in [(-1, 0), (0, -1), (3, 0), (0, 2)]:
            self.assertFalse(self.map.can_move_to(x, y, Direction.NORTH), (x, y))
