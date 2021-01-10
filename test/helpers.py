import functools


def temps(opener):
    def wrapper(fn):
        @functools.wraps(fn)
        def wrapped(self):
            fn(self, opener)
            self.tearDown()
            self.setUp()
            fn(self, functools.partial(opener, temp_file=True))

        return wrapped

    def temps_class(cls):
        for k, v in vars(cls).items():
            if k.startswith('test_') and callable(v):
                setattr(cls, k, wrapper(v))
        return cls

    return temps_class


class socket:
    def __init__(self):
        self.items = []

    def send(self, item):
        self.items.append(item)

    def recv(self):
        pass
