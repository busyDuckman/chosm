import collections.abc
import copy
from abc import abstractmethod
from typing import Dict, Any, overload, Sequence, Literal, List, Union, Tuple
import statistics

from boltons.cacheutils import LRU
from threading import Lock


# TODO: collections.ChainMap may help in future iterations of this code.
# class Difference
#
#
# class InstanceTable()

class ArchetypedTable(collections.abc.Sequence):
    def __init__(self, default_row_or_existing_table: Union[Dict[str, Any], List[Dict[str, Any]]],
                 initial_table_length=0, lru_cache_size: int = 10_000):
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

            # map each column key to an id
            self._column_to_id_lut = {key: i for i, key in enumerate(self._default_row.keys())}
            self._default_row_by_idx: Dict[int, Any] = {self._column_to_id_lut[k]: v for k, v in self._default_row.items()}
            self._table = [{} for _ in range(initial_table_length)]

        elif isinstance(default_row_or_existing_table, list):
            # Find the mode of each column to determine the best^ default key.
            #   ^ best ignoring size difference of various values.
            existing_table: List[Dict[str, Any]] = default_row_or_existing_table
            default_row = {key: [row[key] for row in existing_table] for key in existing_table[0].keys()}
            default_row = {key: statistics.mode(row) for key, row in default_row.items()}
            self._default_row = default_row

            # map each column key to an id
            self._column_to_id_lut = {key: i for i, key in enumerate(self._default_row.keys())}
            self._default_row_by_idx: Dict[int, Any] = {self._column_to_id_lut[k]: v for k, v in self._default_row.items()}
            # NOTE: the previous 2 lines are needed for self._calc_row(...) to work
            self._table = [self._calc_row_difference_indexed(row) for row in existing_table]

        self._id_to_column_lut = {i: k for k, i in self._column_to_id_lut.items()}
        self.col_headings = [self._id_to_column_lut[i] for i in range(len(self._id_to_column_lut))]

        if len(self.col_headings) != len(self._default_row):
            raise KeyError("Not all column headings in the table were unique.")

        self._lru_cache = LRU(max_size=lru_cache_size) if lru_cache_size > 0 else None
        self._lock = Lock()

    def _calc_row_difference_indexed(self, row):
        """
        return difference between row and self._default_row, with col names replaced by index values.
        """
        c_lut = self._column_to_id_lut
        return {c_lut[k]: v for k, v in row.items() if self._default_row[k] != v}

    def _get_row(self, row_index: int):
        if self._lru_cache is not None:
            row = self._lru_cache.get(row_index, None)
            if row is not None:
                return row

        this_row = self._table[row_index]
        id_2_col = self._id_to_column_lut
        num_cols = len(self._default_row)
        row = {id_2_col[q]: this_row[q] if q in this_row.keys() else self._default_row_by_idx[q]
                for q in range(num_cols)}

        if self._lru_cache is not None:
            self._lru_cache[row_index] = row
        return row

    def _get_cell(self, row_index, col_name):
        col_idx = self._column_to_id_lut[col_name]
        this_row = self._table[row_index]
        if col_idx in this_row:
            return this_row[col_idx]
        elif col_name in self._default_row:
            return self._default_row[col_name]
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
                assert isinstance(row, dict)
                # cols not in row will remain unaltered
                # self._table[row_index] = self._table[row_index] | self._calc_row_difference_indexed(row_index)
                self._table[key] = self._calc_row_difference_indexed(row)
            else:
                # set a single cell eg: table[21, "name"] = "john"
                value = row_or_value
                row_index, col_name = key
                col_idx = self._column_to_id_lut[col_name]
                if self._default_row_by_idx[col_idx] != value:
                    self._table[int(row_index)][col_idx] = value

            # remove the cached version
            if self._lru_cache is not None:
                del self._lru_cache[row_index]

    def __len__(self) -> int:
        with self._lock:
            return len(self._table)

    def append(self, row: Dict):
        with self._lock:
            self._table.append(self._calc_row_difference_indexed(row))

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



if __name__ == '__main__':
    main()

