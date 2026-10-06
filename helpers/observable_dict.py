from collections import UserDict
from contextlib import contextmanager
from typing import overload


class _NoNotifyProxy(UserDict):
    def __init__(self, backend):
        self.backend = backend

    def __setitem__(self, key, value):
        self.backend.set_without_notify(key, value)

    def __delitem__(self, key):
        self.backend.delitem_without_notify(key)

    def pop(self, key, default=None):
        return self.backend.pop_without_notify(key, default)

    def popitem(self):
        return self.backend.popitem_without_notify()

    def clear(self):
        self.backend.clear_without_notify()

    def update(self, other=None, **kwargs):
        self.backend.update_without_notify(other=other, **kwargs)

    def setdefault(self, key, default=None):
        self.backend.setdefault_without_notify(key, default)


class ObservableDict(UserDict):
    """
    A dict that can be observed with an on_change method.
    It is conservative with calls to on_change, eg only calling once for a clear or update operation.
    """
    def __init__(self, data=None, on_change=None):
        """
        Create a new dictionary.
        :param data: initial dictionary.
        :param on_change  "def on_update(od: ObservableDict): ..."
        """
        self.on_change = None  # do this first, otherwise it is not defined in the setter used to populate the dict.
        super().__init__(data)
        self.on_change = on_change

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if self.on_change is not None:
            self.on_change(self)

    def set_without_notify(self, key, value):
        super().__setitem__(key, value)

    def __delitem__(self, key):
        super().__delitem__(key)
        if self.on_change is not None:
            self.on_change(self)

    def delitem_without_notify(self, key):
        super().__delitem__(key)

    def clear(self):
        self.clear_without_notify()
        if self.on_change is not None:
            self.on_change(self)

    def clear_without_notify(self):
        # super().clear()  # raises a heap of On_change events

        c = self.on_change
        try:
            self.on_change = None
            super().clear()
        finally:
            self.on_change = c

    def pop(self, key, default=None):
        result = super().pop(key, default)  # causes another call tp self.on_change

        # if self.on_change is not None:
        #     self.on_change(self)
        return result

    def pop_without_notify(self, key, default=None, use_default=True):
        # super(_).pop(...) ends up calling __set_item__, which raises extra notifications.
        # So funneling all pop(...) through this.
        try:
            r = self[key]
            self.delitem_without_notify(key)
            return r
        except KeyError as e:
            if use_default:
                return default
            else:
                raise e

    def popitem(self):
        result = self.popitem_without_notify()
        if self.on_change is not None:
            self.on_change(self)
        return result

    def popitem_without_notify(self):
        c = self.on_change
        try:
            self.on_change = None
            return super().popitem()
        finally:
            self.on_change = c

    def update(self, other=None, **kwargs):
        # super().update(other, **kwargs) raises multiple on_change events.
        try:
            self.update_without_notify(other, **kwargs)
        finally:
            if self.on_change is not None:
                self.on_change(self)

    def update_without_notify(self, other=None, **kwargs):
        c = self.on_change
        try:
            self.on_change = None
            super().update(other, **kwargs)
        finally:
            self.on_change = c

    def setdefault(self, key, default=None):
        result = super().setdefault(key, default)
        if self.on_change is not None:
            self.on_change(self)
        return result

    def setdefault_without_notify(self, key, default=None):
        # super().setdefault(key, default) triggers on_change(...) events
        c = self.on_change
        try:
            self.on_change = None
            return super().setdefault(key, default)
        finally:
            self.on_change = c


    @contextmanager
    def bulk_change(self) -> _NoNotifyProxy:
        yield _NoNotifyProxy(self)
        if self.on_change is not None:
            self.on_change(self)

