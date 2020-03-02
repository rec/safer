from pathlib import Path
from safe_writer import safe_writer
from tempfile import TemporaryDirectory
from unittest import TestCase


class TestSafeWriter(TestCase):
    def test_simple(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safe_writer(filename) as fp:
                fp.write('hello')
            assert filename.read_text() == 'hello'

    def test_error(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('hello')

            with self.assertRaises(ValueError):
                with safe_writer(filename) as fp:
                    fp.write('GONE')
                    raise ValueError

            assert filename.read_text() == 'hello'
