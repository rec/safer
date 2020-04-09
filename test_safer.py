from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import safer


class TestSafer(TestCase):
    def test_simple(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safer.open(filename, 'w') as fp:
                fp.write('hello')
            assert filename.read_text() == 'hello'

    def test_no_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safer.open(filename, 'a') as fp:
                fp.write('hello')
            assert filename.read_text() == 'hello'

    def test_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('c')
            with safer.open(filename, 'a') as fp:
                fp.write('hello')
            assert filename.read_text() == 'chello'

    def test_error(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('hello')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'w') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert filename.read_text() == 'hello'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('c')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'a') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert filename.read_text() == 'c'

    def test_printer(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safer.printer(filename) as print:
                print('hello')
            assert filename.read_text() == 'hello\n'
