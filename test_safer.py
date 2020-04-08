from pathlib import Path
from safer import safe_printer, safe_writer
from tempfile import TemporaryDirectory
from unittest import TestCase


class TestSafer(TestCase):
    def test_simple(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safe_writer(filename) as fp:
                fp.write('hello')
            assert filename.read_text() == 'hello'

    def test_no_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safe_writer(filename, 'a') as fp:
                fp.write('hello')
            assert filename.read_text() == 'hello'

    def test_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('c')
            with safe_writer(filename, 'a') as fp:
                fp.write('hello')
            assert filename.read_text() == 'chello'

    def test_error(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('hello')

            with self.assertRaises(ValueError):
                with safe_writer(filename) as fp:
                    fp.write('GONE')
                    raise ValueError

            assert filename.read_text() == 'hello'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            filename.write_text('c')

            with self.assertRaises(ValueError):
                with safe_writer(filename, 'a') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert filename.read_text() == 'c'

    def test_printer(self):
        print = __builtins__['print']
        with TemporaryDirectory() as td:
            filename = Path(td) / 'test.txt'
            with safe_printer(filename, print=print) as print:
                print('hello')
            assert filename.read_text() == 'hello\n'
