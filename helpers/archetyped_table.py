import collections.abc
import copy
from abc import abstractmethod
from typing import Dict, Any, overload, Sequence, Literal, List, Union, Tuple
import statistics

from boltons.cacheutils import LRU
from threading import Lock
from abc import ABC, abstractmethod


# TODO: collections.ChainMap may help in future iterations of this code.
class DifferenceTable(ABC, collections.abc.Sequence):
    def __init__(self, col_headings: List[str], lru_cache_size: int = 10_000):
        self._lru_cache = LRU(max_size=lru_cache_size) if lru_cache_size > 0 else None
        self._num_cols = len(col_headings)
        self._table = []
        self.col_headings = col_headings

        self._column_to_id_lut = {key: i for i, key in enumerate(self.col_headings)}
        self._id_to_column_lut = {i: k for k, i in self._column_to_id_lut.items()}

        self._lock = Lock()

    @abstractmethod
    def get_reference_row_by_idx(self, row_index):
        pass

    @abstractmethod
    def get_reference_row(self, row_index):
        pass

    def _calc_row_difference_indexed(self, row, row_index):
        """
        return difference between row and self.get_reference_row, with col names replaced by index values.
        """
        reference_row = self.get_reference_row(row_index)
        c_lut = self._column_to_id_lut
        return {c_lut[k]: v for k, v in row.items() if reference_row[k] != v}

    def _get_row(self, row_index: int):
        if self._lru_cache is not None:
            row = self._lru_cache.get(row_index, None)
            if row is not None:
                return row

        this_row = self._table[row_index]
        reference_row_by_idx = self.get_reference_row_by_idx(row_index)
        id_2_col = self._id_to_column_lut
        row = {id_2_col[q]: this_row[q] if q in this_row.keys() else reference_row_by_idx[q]
                for q in range(self._num_cols)}

        if self._lru_cache is not None:
            self._lru_cache[row_index] = row
        return row

    def _get_cell(self, row_index, col_name):
        col_idx = self._column_to_id_lut[col_name]
        this_row = self._table[row_index]
        if col_idx in this_row:
            return this_row[col_idx]

        reference_row = self.get_reference_row(row_index)
        if col_name in reference_row:
            return reference_row[col_name]
        raise KeyError()

    def __getitem__(self, key: Union[int, Tuple]):
        """
        Gets a row, or value from a row.
        :param key:
            table[21] returns {...row 21's data...}
            table[21, "height"] returns the height col for row 21. (for a cache miss, faster than table[21]["height"])
        """
        with self._lock:
            if isinstance(key, slice):
                # get multiple rows
                return [self._get_row(idx) for idx in range(len(self._table))[key]]
            if isinstance(key, int):
                # get the whole row
                row_index = int(key)
                return self._get_row(row_index)
            else:
                # get a specific column in the row
                try:
                    row_index, col_name = key  # does it quack like a two value tuple?
                    return self._get_cell(row_index, col_name)
                except ValueError or TypeError:
                    raise KeyError()

    def __setitem__(self, key: Union[int, Tuple], row_or_value: Dict):
        with self._lock:
            if isinstance(key, int):
                # set multiple (or all) columns in a row eg: table[21] = {name: "john", age: 21, height: 186}
                row = row_or_value
                row_index = key
                assert isinstance(row, dict)
                # cols not in row will remain unaltered
                # self._table[row_index] = self._table[row_index] | self._calc_row_difference_indexed(row_index)
                self._table[row_index] = self._calc_row_difference_indexed(row, row_index)
            else:
                # set a single cell eg: table[21, "name"] = "john"
                value = row_or_value
                row_index, col_name = key
                col_idx = self._column_to_id_lut[col_name]
                if self.get_reference_row_by_idx(row_index)[col_idx] != value:
                    self._table[int(row_index)][col_idx] = value

            # remove the cached version
            if self._lru_cache is not None:
                del self._lru_cache[row_index]

    def __len__(self) -> int:
        with self._lock:
            return len(self._table)

    def print(self, max_rows=10):
        print(", ".join(self.col_headings)) # col headings is in index order.
        for i_row in range(min(max_rows-1, len(self))):
            row = self[i_row]
            print(", ".join([str(row[h]).rjust(len(h)) for h in self.col_headings]))

        if len(self) > max_rows:
            print("...")
        if len(self) >= max_rows:
            row = self[-1]
            print(", ".join([str(row[h]).rjust(len(h)) for h in self.col_headings]))

    def get_difference_table(self):
        return [{self._id_to_column_lut[k_idx]: val for k_idx, val in row.items()} for row in self._table]


class InstanceTable(DifferenceTable):
    def __init__(self, reference_table: List[Dict[str, Any]], lru_cache_size: int = 1_000):
        # TODO: internalise with an list of lists, not a list of dicts.
        self._reference_table = reference_table
        col_names = []
        if len(reference_table) > 0:
            col_names = list(reference_table[0].keys())
        super().__init__(col_names)
        self._table = [{} for _ in range(len(reference_table))]

    def get_reference_row_by_idx(self, row_index):
        row = self._reference_table[row_index]
        return {self._column_to_id_lut[c]: v for c, v in row.items()}

    def get_reference_row(self, row_index):
        return self._reference_table[row_index]


class ArchetypedTable(DifferenceTable):
    def __init__(self, default_row_or_existing_table: Union[Dict[str, Any], List[Dict[str, Any]]],
                 initial_table_length=0, lru_cache_size: int = 1_000):
        """
        Memory efficient storage for a table with a lot of values that remain the same.
        It stores every row as its alterations from a single default row.
        :param default_row_or_existing_table:
                A) the default row. Only alterations from this default are stored.
                B) an existing table List[Dict[str, Any]]
        :param initial_table_length: The initial length of the table. Only applicable if providing a "default row"
        :param lru_cache_size: size of lru cache (prevents re-merging rows with default). 0 to disable.
        """
        if isinstance(default_row_or_existing_table, dict):
            default_row: Dict[str, Any] = default_row_or_existing_table
            self._default_row: Dict[str, Any] = copy.deepcopy(default_row)

            super().__init__(list(self._default_row.keys()), lru_cache_size)
            self._default_row_by_idx: Dict[int, Any] = {self._column_to_id_lut[k]: v for k, v in
                                                        self._default_row.items()}
            self._table = [{} for _ in range(initial_table_length)]

        elif isinstance(default_row_or_existing_table, list):
            # Find the mode of each column to determine the best^ default key.
            #   ^ best ignoring size difference of various values.
            existing_table: List[Dict[str, Any]] = default_row_or_existing_table
            default_row = {key: [row[key] for row in existing_table] for key in existing_table[0].keys()}
            default_row = {key: statistics.mode(row) for key, row in default_row.items()}
            self._default_row = default_row

            # NOTE: the next 3 lines need to be in this order to work
            super().__init__(list(self._default_row.keys()), lru_cache_size)
            self._default_row_by_idx: Dict[int, Any] = {self._column_to_id_lut[k]: v for k, v in
                                                        self._default_row.items()}
            self._table = [self._calc_row_difference_indexed(row, 0) for row in existing_table]
        else:
            raise ValueError("Bad value for default_row_or_existing_table")

        if len(self.col_headings) != len(self._default_row):
            raise KeyError("Not all column headings in the table were unique.")

    def get_reference_row_by_idx(self, row_index):
        return self._default_row_by_idx

    def get_reference_row(self, row_index):
        return self._default_row

    def append(self, row: Dict):
        with self._lock:
            self._table.append(self._calc_row_difference_indexed(row, 0))


def main():
    tbl = ArchetypedTable({"height": -1, "surface": 0, "is_water": False}, 3, lru_cache_size=0)
    tbl[1] = {"height": 10, "surface": 3}
    tbl[-1, "is_water"] = True
    tbl.append({"surface": 2})
    tbl.append({"surface": 1})

    print("tbl[0]:", tbl[0])
    print("tbl[-1, height]:", tbl[-1, "height"])
    # print(len(tbl))
    print("attempting list")
    print(list(tbl[2:4]))

    print()
    tbl.print()

    import numpy as np

    def gen_person():
        return {"age": np.random.choice([21, 21, 23], p=[.80, .10, .10]),
                "name": np.random.choice(["Bob", "Jane", "Waxillium"], p=[.55, .40, .05]),
                "height": np.random.choice([170, 180, 190], p=[.10, .80, .10]),
                "can_swim": np.random.choice([True, False], p=[.95, .05]),
                }

    ppl_array = [gen_person() for _ in range(10)]
    ppl_arch_array = ArchetypedTable(ppl_array)
    ppl_arch_array.print()
    print(ppl_arch_array.get_difference_table())

    print()
    print("Testing instance table")
    ppl_inst_array = InstanceTable(ppl_array)
    print(ppl_inst_array[3])
    ppl_inst_array[3, "age"] = 27
    print(ppl_inst_array[3])
    print(ppl_inst_array.get_difference_table())



if __name__ == '__main__':
    main()

