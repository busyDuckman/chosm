from typing import Dict


# class SliceProxy(object):
#     """
#     Creates a clicing operator
#     eg:
#         make_slice = SliceProxy()
#         slicer = make_slice[:-1]
#         frames = all_frames[slicer]
#     """
#     def __getitem__(self, item):
#         return item


def is_continuous_integers(series):
    if len(series) == 0:
        return True

    start = series[0]
    series_b = range(start, start + len(series))
    return all(a == b for a, b in zip(series, series_b))


def popo_to_dict(obj):
    """
    "Plain old Python Object" to dict
    Trivial encapsulation of selecting from __dict__ items that don't start with "_".
    I'm sticking it its own function as I may want to improve this kludge oneday.
    """
    return {k: v for k, v in obj.__dict__.items() if not k.strip().startswith("_")}


def popo_from_dict(target, info: Dict):
    for k, v in info.items():
        if not hasattr(target, k):
            raise ValueError("Target object does not have attribute: " + k)
        setattr(target, k, v)
    return target


def main():
    class Person:
        def __init__(self, name):
            self.name = name
            self.u_id = hash(name)
            self._private_info = [1, 2, 3]

        def foobar(self):
            print("foobar")

    class GundamPilot(Person):
        def __init__(self, name):
            super().__init__(name)
            self.is_new_type = False

        def load(self, d):
            popo_from_dict(self, d)

    print(popo_to_dict(Person("Bob")))

    print(popo_to_dict(GundamPilot("Setsuna F. Seiei")))

    p2 = GundamPilot("?")

    print(popo_to_dict(p2))

    p2.load(popo_to_dict(GundamPilot("Setsuna F. Seiei")))
    print(popo_to_dict(p2))


if __name__ == '__main__':
    main()
