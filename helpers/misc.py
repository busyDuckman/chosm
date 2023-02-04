import inspect
import json
from typing import Dict, Any


class _SlicerMeta(type):
    def __getitem__(self, item: slice):
        return item


class Slicer(object, metaclass=_SlicerMeta):
    """
    Creates a slicing operator, that can be passed to functions etc.
    eg:
        slicer = Slicer[:-1]
        frames = all_frames[slicer]
    """
    pass


class _SliceDescriberMeta(type):
    def __getitem__(self, item: slice):
        if isinstance(item, int):
            return f"at {item+1}"

        if not isinstance(item, slice):
            return "unknown"

        if any((q is not None) and not isinstance(q, int) for q in [item.start, item.stop, item.step]):
            return "indexed or invalid"

        single_step = item.step is None or abs(item.step) == 1
        desc = ""
        safe_step = 1 if item.step is None else item.step

        if safe_step == 0:
            return "invalid"

        # the none edge case
        if (item.stop == 0 and item.start in [None, 0]) or \
            ((item.stop == item.start) and (item.start is not None)):
            # logic not complete, eg: [1:-1:-1] is none
            return "none"

        # formulate a description
        if item.start is None or item.start == 0:
            # start at beginning
            if item.stop is None:
                desc = "all" if single_step else "step"
            else:
                desc = f"first {item.stop}" if single_step else f"less than {item.stop}"
        else:
            if item.stop is None:
                desc = f"from {item.start+1}"
            else:
                desc = f"from {item.start+1} to {item.stop-1}"

        if not single_step:
            desc += f" by {abs(safe_step)}"

        if safe_step < 0:
            desc += " in reverse"

        return desc


class SliceDescriber(object, metaclass=_SliceDescriberMeta):
    """
    Describes a slice.
    eg:
        SliceDescriber[2:4] == "from 2 to 4"
        SliceDescriber[2:4:2] == "from 2 to 4_by 2"
        SliceDescriber[2] == "at 2"
    """

def main2():
    print(SliceDescriber[2:5])
    print(SliceDescriber[5])
    print(SliceDescriber[::2])
    print(SliceDescriber[-1:])
    print(SliceDescriber[:])
    print(SliceDescriber[:5:2])
    print(SliceDescriber[:0])
    print(SliceDescriber[1: -1: -1])  # error: it will print "from 2 to -2 in reverse"
    print(SliceDescriber[:[]])

    

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


def prune_kwargs(func, kwargs: Dict[str, Any]):
    """
    Reduces a dictionary to only the members matching a functions argument list.
    :param func:    A function
    :param kwargs:  A dictionary that could be a **kwargs to func, but has too many entries.
    :return: kwargs suitable for calling func.
    """
    args = list(inspect.getargs(func.__code__).args)
    args = set([a for a in args if a not in ["self", "args", "kwargs"]])
    return {k: v for k, v in kwargs.items() if k in args}


def my_json_dumps(what) -> str:
    """
    I have to dump json with large arrays, but the python thing puts every element on a new line.
    So I ended up with a hacky script to post process that into something more readable.
    """
    def is_simple_array_element(t):
        return all(q not in t for q in ":[]{}")


    jsn = json.dumps(what, indent = 2)
    # print(jsn)
    # print("\n----------------\n")
    next_jsn = jsn.splitlines()
    next_jsn.append("")
    next_jsn.pop(0)

    output_txt = ""
    for line, next_line in zip(jsn.splitlines(), next_jsn):
        ls = line.strip()
        nls = next_line.strip()
        if is_simple_array_element(ls):
            output_txt += ls + " "
        elif ls.endswith("["):
            output_txt += line + " "  # keep first line indent
        elif ls.startswith("]"):
            output_txt += ls + "\n"  # last item in array
        else:
            output_txt += line + "\n"

    return output_txt



def main():
    print(Slicer[2:5])


    f = {"n": "Bob", "age": 31, "data": [1,2,3,4,5], "sub_data": {"a": 1, "b": 2} }
    print(my_json_dumps(f))

    # exit(0)

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

    print(prune_kwargs(popo_from_dict, {"foo": "bar", "name": "Bob"}))
    print(prune_kwargs(main, {"foo": "bar", "name": "Bob"}))
    print(prune_kwargs(Person.__init__, {"foo": "bar", "name": "Bob"}))
    Person(**prune_kwargs(Person.__init__, {"foo": "bar", "name": "Bob"}))

    print("\n--------------------------------------\n")

    print(popo_to_dict(Person("Bob")))

    print(popo_to_dict(GundamPilot("Setsuna F. Seiei")))

    p2 = GundamPilot("?")

    print(popo_to_dict(p2))

    p2.load(popo_to_dict(GundamPilot("Setsuna F. Seiei")))
    print(popo_to_dict(p2))


if __name__ == '__main__':
    main2()
