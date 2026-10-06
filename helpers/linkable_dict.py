import logging
from collections.abc import MutableMapping
from typing import Dict, List, Any, Set, Tuple


def _check_circular_lookup(_visit_trail, current_node):
    if _visit_trail is None:
        return set([id(current_node)])
    elif id(current_node) in _visit_trail:
        logging.warning("Circular lookup")
        raise KeyError("Circular Lookup")
    else:
        new_trail = set(_visit_trail)
        new_trail.add(id(current_node))
        return new_trail


class LinkableDict(MutableMapping):
    """
    LinkableDict can interact with other LinkableDict classes in two ways:
      - override: If a key not present in this dictionary, the "override" dictionaries are the queried.
                  This type of relationship make it look like one LinkableDict including all "override" dictionaries.
                    - eg: iteration will be over the set of all items including all "override" dictionaries.
      - include:  A special @ character splits the key.
                  The left of @ is the key.
                  The right of @ redirects to another LinkableDict.
                  eg: "sprite-ice-dragon-027@stock_dragons"
                  Note: if stock_dragons overrides another class, the query carries through to that class  as you would expect.
    """
    def __init__(self, *args, **kwargs):
        self._map = {}                                   # the mapping of this instance
        self.overrides: List[Dict[str, Any]] = []        # a list of LinkableDict
        self.includes: Dict[str, Dict[str, : Any]] = {}  # a map of str to LinkableDict
        self.tag: Any = None                             # extra info about as required
        self.update(dict(*args, **kwargs))

    def get_item(self,
                 key: str,
                 _visit_trail: Set = None):
        """
        Get an item according to the overrides and includes settings.
        :param key: The key to look up. A @ in the key indicates an includes based lookup.
        :param _visit_trail:
        :return: At tuple, the value and the tag of the LinkableDict that hold is.
        """
        # this trail detects circular lookups.
        new_trail = _check_circular_lookup(_visit_trail, self)

        # enforce the key is a string rule.
        if not isinstance(key, str):
            raise KeyError("Key is not a string")

        # attempt the lookup, building a list of other places to check if that's not possible.
        match key.count("@"):
            case 0:
                # regular lookup
                try:
                    return self._map[key], self.tag  # the key was found
                except KeyError:
                    pass
            case 1:
                # lookup via the includes table.
                _key, _include_name = key.split("@")
                if _include_name in self.includes:
                    try:
                        d: LinkableDict = self.includes[_include_name]
                        return d.get_item(_key, new_trail)
                    except KeyError:
                        pass
            case _:
                raise KeyError("include lookup can not include more than one @ symbol.")

        # fallback to the LinkableDict's we are overriding and see if they know what to do with the key.
        for other_dict in self.overrides:
            try:
                other_dict: LinkableDict = other_dict
                return other_dict.get_item(key, new_trail)
            except KeyError:
                pass

        # no cigar
        raise KeyError("No value found for key: " + key)


    def __getitem__(self, key):
        """
        As per get_item(...), but only the value is returned.
        :param key:
        :return:
        """
        val, _ = self.get_item(key)
        return val

    def __setitem__(self, key: str, value: any):
        """
        Sets an item in this LinkableDict.
        Will not alter a LinkableDict in the overrides or inclusions tables.
        :param key: The key, must be a string with not @ symbol,
        :param value: An item in this LinkableDict, if found.
        :return: A value, or KeyError is raised.
        """
        if not isinstance(key, str):
            raise KeyError("Keys is not a string")
        if "@" in key:
            raise KeyError("Include symbol @ is not valid for __setitem__")

        # setting only applies to current LinkableDict
        self._map[key] = value

    def __delitem__(self, key: str):
        if not isinstance(key, str):
            raise KeyError("Keys is not a string")
        if "@" in key:
            raise KeyError("Include symbol @ is not valid for __delitem__")

        del self._map[key]

    def all_keys(self, _visit_trail: Set = None) -> Set[str]:
        """
        A list af all keys, including overrides.
        """
        new_trail = _check_circular_lookup(_visit_trail, self)
        keys = set(self._map.keys())

        for override in self.overrides:
            keys.update(override.all_keys(_visit_trail=new_trail))

        return keys

    def just_my_keys(self):
        return list(self._map.keys())

    def key_info(self, key: str, _visit_trail: Set = None) -> List[Tuple[str, Any]]:
        """
        Used for getting info on a key.
        :param _visit_trail:
        :return: A set of tuples, where each tuple is the tag of the LinkableDict
                 that it came from and the value in that table.
        """
        # this trail detects circular lookups.
        new_trail = _check_circular_lookup(_visit_trail, self)

        info = []
        if key in self._map:
            info = [(self.tag, self._map[key])]

        for override in self.overrides:
            more_info = override.key_info(key, _visit_trail=new_trail)
            if len(more_info) > 0:
                info.extend(more_info)
                break

        return info

    def keys(self) -> List[str]:
        return list(self.all_keys())

    def values(self) -> List[Any]:
        return [self[k] for k in self.keys()]

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        return f"{type(self).__name__}({dict(self.items())})"

    def __eq__(self, other):
        if isinstance(other, LinkableDict):
            return dict(self.items()) == dict(other.items())
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


def main():
    d1 = LinkableDict({"cat": "meow", "dog": "woof"})
    d1.tag = "animals"

    d1_ovr = LinkableDict({"cat": "purr", "bird": "chirp"})
    d1_ovr.tag = "happy_animals"
    d1_ovr.overrides.append(d1)

    print("\n\nall keys")
    print(d1.keys())
    print(d1_ovr.keys())

    print("\n\nlookup")
    print(d1["cat"], d1["dog"])
    print(d1_ovr["cat"], d1["dog"])
    print(d1_ovr.get_item("cat"))
    print(d1_ovr.get_item("dog"))

    print(d1_ovr.key_info("cat"))
    print(d1_ovr.key_info("dog"))

    print(d1.keys())
    print(d1_ovr.keys())

    d2 = LinkableDict({"horse": "ney"})
    d2.tag = "farm_animals"
    d2.includes["animals"] = d1_ovr
    print(d2.tag)
    print(d2["horse"])
    print(d2["cat@animals"])
    print(d2["dog@animals"])

    # del d1_ovr["cat"]
    # print(d1_ovr["cat"])

    print("\n\ncircular dependencies")
    d1.overrides.append(d1_ovr)
    print(d1["dog"])
    print(d1["bird"])




if __name__ == '__main__':
    main()
