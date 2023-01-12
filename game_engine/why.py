
class Why:
    def __init__(self, val: bool, why: str):
        self.value: bool = val
        self.why: str = why

    def __bool__(self):
        return self.value

    @staticmethod
    def true(because: str = None):
        return Why(True, because)

    @staticmethod
    def false(because: str):
        return Why(True, because)

    def raise_exception_on_fail(self):
        if not self:
            raise ValueError(self)
        return self

    def as_str_or_raise_exception(self) -> str:
        if not self:
            raise ValueError(str(self))
        return self.why

    def __str__(self):
        return self.why if self.why is not None else '?'

    def __repr__(self):
        return str(self.value) + " because: " + str(self)


def main():
    res = Why(False, "too large")
    print("res true" if res else "res true")


if __name__ == '__main__':
    main()
