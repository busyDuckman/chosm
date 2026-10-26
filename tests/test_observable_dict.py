import unittest
from collections import Counter
from threading import Thread
from helpers.observable_dict import ObservableDict


class ObservableDictTestCase(unittest.TestCase):
    def test_basic_functionality(self):
        data = {"a": 1, "b": 2}
        od = ObservableDict(data)
        self.assertEqual(len(od), 2)
        self.assertEqual(od["a"], 1)
        self.assertEqual(od["b"], 2)
        od["c"] = 3
        self.assertEqual(len(od), 3)
        self.assertEqual(od["c"], 3)

    def test_on_change_callback(self):
        data = {"a": 1, "b": 2}
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        od = ObservableDict(data, on_change=on_change)
        self.assertEqual(counter["count"], 0)
        od["c"] = 3
        self.assertEqual(counter["count"], 1)
        od["d"] = 4
        self.assertEqual(counter["count"], 2)

    def test_bulk_change(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        od = ObservableDict({"a": 1, "b": 2}, on_change)
        with od.bulk_change() as odb:
            odb["c"] = 3
            odb["d"] = 4
            odb.pop("c")

        self.assertEqual(counter["count"], 1)
        self.assertEqual(od["d"], 4)
        with self.assertRaises(KeyError):
            _ = od['c']


        with od.bulk_change() as odb:
            odb["c"] = 3
            self.assertEqual(od["c"], 3)
            del odb['c']
            self.assertEqual(counter["count"], 1)

            odb.clear()
            self.assertEqual(counter["count"], 1)

            odb.update({"a": 1, "b": 2})
            self.assertEqual(counter["count"], 1)

            odb.setdefault("e", 100)
            self.assertEqual(counter["count"], 1)

        with self.assertRaises(KeyError):
            _ = od['c']
        self.assertEqual(counter["count"], 2)

    def test_delitem(self):
        counter = Counter()
        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1}, on_change)
        self.assertEqual(counter["count"], 0)
        del d['a']
        with self.assertRaises(KeyError):
            _ = d['a']

        self.assertEqual(counter["count"], 1)

    def test_len(self):
        d = ObservableDict({'a': 1, 'b': 2})
        self.assertEqual(len(d), 2)

    def test_contains(self):
        d = ObservableDict({'a': 1})
        self.assertIn('a', d)
        self.assertNotIn('b', d)

    def test_keys(self):
        d = ObservableDict({'a': 1, 'b': 2})
        self.assertListEqual(list(d.keys()), ['a', 'b'])

    def test_values(self):
        d = ObservableDict({'a': 1, 'b': 2})
        self.assertListEqual(list(d.values()), [1, 2])

    def test_items(self):
        d = ObservableDict({'a': 1, 'b': 2})
        self.assertListEqual(list(d.items()), [('a', 1), ('b', 2)])

    def test_clear(self):
        d = ObservableDict({'a': 1})
        d.clear()
        self.assertEqual(len(d), 0)

    def test_update(self):
        d = ObservableDict({'a': 1})
        d.update({'b': 2, 'c': 3})
        self.assertEqual(d['b'], 2)
        self.assertEqual(d['c'], 3)

    def test_copy(self):
        d = ObservableDict({'a': 1})
        d_copy = d.copy()
        self.assertEqual(d['a'], d_copy['a'])

    def test_setitem(self):
        d = ObservableDict({'a': 1, 'b': 2})
        d['a'] = 4
        self.assertEqual(d['a'], 4)

    def test_setitem_notify(self):
        d = ObservableDict({'a': 1, 'b': 2})

        counter = Counter()
        def on_change(od: ObservableDict):
            counter["count"] += 1

        d.on_change = on_change
        d['a'] = 4
        self.assertEqual(counter["count"], 1)

    def test_set_without_notify(self):
        def on_change(od: ObservableDict):
            self.fail()

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        d.set_without_notify('a', 4)
        self.assertEqual(d['a'], 4)

    def test_delitem(self):
        d = ObservableDict({'a': 1, 'b': 2})
        del d['a']
        with self.assertRaises(KeyError):
            _ = d['a']

    def test_delitem_notify(self):
        counter = Counter()
        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)

        del d['a']
        self.assertEqual(counter["count"], 1)

    def test_delitem_without_notify(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)
        d.delitem_without_notify('a')
        self.assertEqual(counter["count"], 0)

        with self.assertRaises(KeyError):
            _ = d['a']

    def test_pop(self):
        d = ObservableDict({'a': 1, 'b': 2})
        self.assertEqual(d.pop('a'), 1)
        self.assertEqual(d.pop('c', 3), 3)
        # TODO: this involves some trickery
        # with self.assertRaises(KeyError):
        #     d.pop('c')

    def test_pop_notify(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)
        d.pop('a')
        self.assertEqual(counter["count"], 1)

    def test_pop_without_notify(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)

        self.assertEqual(d.pop_without_notify('a'), 1)
        self.assertEqual(counter["count"], 0)

        self.assertEqual(d.pop_without_notify('c', 3), 3)

        # TODO: se not in the pop test case
        # with self.assertRaises(KeyError):
        #     print(d.pop_without_notify('c'))

    def test_popitem(self):
        d = ObservableDict({'a': 1, 'b': 2})
        item = d.popitem()
        self.assertIn(item[0], ('a', 'b'))
        self.assertIn(item[1], (1, 2))
        self.assertEqual(len(d), 1)

    def test_popitem_notify(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)

        d.popitem()
        self.assertEqual(counter["count"], 1)

        d.popitem()
        self.assertEqual(counter["count"], 2)

    def test_popitem_without_notify(self):
        def on_change(od: ObservableDict):
            self.fail()

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        item = d.popitem_without_notify()
        self.assertIn(item[0], ('a', 'b'))
        self.assertIn(item[1], (1, 2))
        self.assertEqual(len(d), 1)

    def test_clear(self):
        d = ObservableDict({'a': 1, 'b': 2})
        d.clear()
        self.assertEqual(len(d), 0)

    def test_clear_notify(self):
        counter = Counter()

        def on_change(od: ObservableDict):
            counter["count"] += 1

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        self.assertEqual(counter["count"], 0)
        d.clear()
        self.assertEqual(counter["count"], 1)

    def test_clear_without_notify(self):
        def on_change(od: ObservableDict):
            self.fail()

        d = ObservableDict({'a': 1, 'b': 2}, on_change)
        d.clear_without_notify()
        self.assertEqual(len(d), 0)



    # def test_thread_safety(self):
    #     data = {"a": 1, "b": 2}
    #     counter = Counter()
    #     def on_change(od):
    #         counter["count"] += 1
    #     od = ObservableDict(data, on_change=on_change)
    #
    #     def add_key():
    #         for i in range(10000):
    #             od[f"{i}"] = i
    #
    #     def remove_key():
    #         for i in range(10000):
    #             del od[f"{i}"]
    #
    #     t1 = Thread(target=add_key)
    #     t2 = Thread(target=remove_key)
    #     t1.start()
    #     t2.start()
    #     t1.join()
    #     t2.join()
    #     self.assertEqual(len(od), 2)
    #     self.assertEqual(counter["count"], 20000)


if __name__ == "__main__":
    unittest.main()
