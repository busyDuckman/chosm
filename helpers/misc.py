
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
