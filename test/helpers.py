from pathlib import Path
from tempfile import TemporaryDirectory
import functools
import unittest


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


class TestCase(unittest.TestCase):
    def setUp(self):
        self.td_context = TemporaryDirectory()
        self.td = Path(self.td_context.__enter__())
        self.filename = self.td / 'test.txt'

    def tearDown(self):
        self.td_context.__exit__(None, None, None)
