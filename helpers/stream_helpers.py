from enum import Enum
from typing import Literal, List, Tuple, NamedTuple


def read_int(f,
             bytes_per_int: int = 2,
             signed: bool = False,
             byteorder: Literal['little', 'big'] = 'little'):
    return int.from_bytes(f.read(bytes_per_int), byteorder=byteorder, signed=signed)


def read_int_array(f,
                   n: int,
                   bytes_per_int: int = 2,
                   signed: bool = False,
                   byteorder: Literal['little', 'big'] = 'little'):
    """
    Read integer(s) from a stream
    :param f: stream
    :param n: number of integers
    :param bytes_per_int: size of each int
    :param signed: are the integers signed?
    :param byteorder: big/little byte order
    :return: an integer, or an array of ints if n > 0
    """
    if n == 0:
        return []
    else:
        return [int.from_bytes(f.read(bytes_per_int), byteorder=byteorder, signed=signed) for _ in range(n)]


def read_uint16(f, byteorder: Literal['little', 'big'] = 'little'):
    return read_int(f, bytes_per_int=2, signed=False, byteorder=byteorder)


def read_uint24(f, byteorder: Literal['little', 'big'] = 'little'):
    return read_int(f, bytes_per_int=3, signed=False, byteorder=byteorder)


def read_uint32(f, byteorder: Literal['little', 'big'] = 'little'):
    return read_int(f, bytes_per_int=4, signed=False, byteorder=byteorder)


def read_byte(f):
    return read_int(f, bytes_per_int=1, signed=False)


def read_uint16_array(f, n: int,
                byteorder: Literal['little', 'big'] = 'little'):
    return read_int_array(f, n, bytes_per_int=2, signed=False, byteorder=byteorder)


def read_uint24_array(f, n: int,
                byteorder: Literal['little', 'big'] = 'little'):
    return read_int_array(f, n, bytes_per_int=3, signed=False, byteorder=byteorder)


def read_uint32_array(f, n: int,
                byteorder: Literal['little', 'big'] = 'little'):
    return read_int_array(f, n, bytes_per_int=4, signed=False, byteorder=byteorder)


def read_byte_array(f, n: int):
    return read_int_array(f, n, bytes_per_int=1, signed=False)


def read_string(f, size: int = None):
    if size is not None:
        s = read_byte_array(f, size)
    else:
        s = []
        while (c := read_byte(f)) != 0:
            s += c

    # parse ascii string (note a fixed length string may nulls, we skip these)
    return "".join([chr(c) for c in s if c != 0])


class DType(Enum):
    BYTE = 1
    U_INT_16 = 2
    U_INT_24 = 3
    U_INT_32 = 4
    U_INT_16_MSB = 5
    U_INT_24_MSB = 6
    U_INT_32_MSB = 7

    def read(self, f):
        match self:
            case DType.BYTE:
                return read_int(f, bytes_per_int=1, signed=False)
            case DType.U_INT_16:
                return read_int(f, bytes_per_int=2, signed=False)
            case DType.U_INT_24:
                return read_int(f, bytes_per_int=3, signed=False)
            case DType.U_INT_32:
                return read_int(f, bytes_per_int=4, signed=False)
            case DType.U_INT_16_MSB:
                return read_int(f, bytes_per_int=2, signed=False, byteorder="big")
            case DType.U_INT_24_MSB:
                return read_int(f, bytes_per_int=3, signed=False, byteorder="big")
            case DType.U_INT_32_MSB:
                return read_int(f, bytes_per_int=4, signed=False, byteorder="big")
            case _:
                raise ValueError("Unknown data type in DType.read(...)")


def read_dict(f,
              record_format: List[Tuple[str, str]],
              n=None) -> NamedTuple:
    global _data_readers
    _n = n if n is not None else 1
    if _n < 1:
        return []

    res_list = []
    for i in range(_n):
        res = {}
        for name, data_type in record_format:
            if data_type not in _data_readers:
                raise ValueError(f"unknown data format: {data_type}")
            if name in res:
                raise ValueError(f"named data item listed more than once: {data_type}")
            value = _data_readers[data_type](f)
            if name != '_':
                res[name] = value
        res_list.append(res)

    return res_list if n is not None else res_list[0]


def read_list(f,
              values: List[str],
              n=None) -> NamedTuple:
    """

    :param f:
    :param values:
    :param n:
    :return: An array if n is not None (iven if n = 1)
    """
    if type(values) == str:
        values = [s.strip() for s in values.split(",")]
    global _data_readers
    _n = n if n is not None else 1
    if _n < 1:
        return []

    res_list = []
    for i in range(_n):
        res = []
        for data_type in values:
            if data_type not in _data_readers:
                raise ValueError(f"unknown data format: {data_type}")
            value = _data_readers[data_type](f)
            res.append(value)

        res_list.append(res)

    return res_list if n is not None else res_list[0]


_data_readers = {
          "byte": lambda f: read_int(f, bytes_per_int=1, signed=False),
        "uint16": lambda f: read_int(f, bytes_per_int=2, signed=False),
        "uint24": lambda f: read_int(f, bytes_per_int=3, signed=False),
        "uint32": lambda f: read_int(f, bytes_per_int=4, signed=False),
        # "str":          lambda f: read_string(f)
    }
