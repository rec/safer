import functools


def temps(opener):
    """Generate independent unittest cases, each with its own fixture lifecycle."""

    def wrapper(fn, selected):
        @functools.wraps(fn)
        def wrapped(self):
            fn(self, selected)

        return wrapped

    def temps_class(cls):
        for k, v in list(vars(cls).items()):
            if k.startswith('test_') and callable(v):
                delattr(cls, k)
                setattr(cls, k + '_memory', wrapper(v, opener))
                setattr(
                    cls,
                    k + '_disk',
                    wrapper(v, functools.partial(opener, temp_file=True)),
                )
        return cls

    return temps_class


class socket:
    def __init__(self):
        self.items = []
        self.closed = False

    def send(self, item):
        self.items.append(item)
        return len(item)

    def recv(self):
        pass

    def close(self):
        self.closed = True
