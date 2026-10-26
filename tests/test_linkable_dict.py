import unittest
from helpers.linkable_dict import LinkableDict


class TestLinkableDict(unittest.TestCase):
    def test_basic_functionality(self):
        d = LinkableDict({'a': 1, 'b': 2})
        self.assertEqual(d['a'], 1)
        self.assertEqual(d['b'], 2)
        d['c'] = 3
        self.assertEqual(d['c'], 3)
        del d['b']
        self.assertNotIn('b', d)

    def test_override_relationship(self):
        d1 = LinkableDict({'a': 1, 'b': 2})
        d2 = LinkableDict({'b': 3, 'c': 4})

        d3 = LinkableDict({'c': 5, 'd': 6})

        d1.overrides.extend([d2, d3])

        self.assertEqual(list(sorted(d1.keys())), ['a', 'b', 'c', 'd'])
        for _ in range(10):
            self.assertEqual(d1['a'], 1)
            self.assertEqual(d1['b'], 2)
            self.assertEqual(d1['c'], 4)
            self.assertEqual(d1['d'], 6)

        self.assertEqual(list(sorted(d1.values())), [1, 2, 4, 6])

    def test_include_relationship(self):
        d1 = LinkableDict({'a': 1, 'b': 2})
        d2 = LinkableDict({'b': 3, 'c': 4})
        d3 = LinkableDict({'c': 5, 'd': 6})

        d1.includes["d2"] = d2
        # self.assertEqual(d1['a@d2'], 1)
        self.assertEqual(d1['b@d2'], 3)