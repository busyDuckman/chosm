from unittest import TestCase

from helpers.misc import is_continuous_integers


class Test(TestCase):
    def test_is_continuous_integers(self):
        self.assertTrue(is_continuous_integers([2, 3, 4, 5]))
        self.assertFalse(is_continuous_integers([2, 4, 5]))
        self.assertTrue(is_continuous_integers([-1, 0, 1, 2, 3]))
        self.assertFalse(is_continuous_integers([5, 4, 3, 2, 1]))
