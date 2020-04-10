from __future__ import print_function
from unittest import TestCase
import os
import safer


class TestSafer(TestCase):
    def test_simple(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.open(filename, 'w') as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_no_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.open(filename, 'a') as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')
            with safer.open(filename, 'a') as fp:
                fp.write('hello')
            assert read_text(filename) == 'chello'

    def test_error(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'w') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'hello'

    def test_create_parents(self):
        with TemporaryDirectory() as td:
            filename = td + '/foo/test.txt'
            with self.assertRaises(ValueError) as m:
                with safer.open(filename, 'w'):
                    pass
            assert 'does not exist' in m.exception.args[0]

            with safer.open(filename, 'w', create_parents=True) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_two_errors(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'w', delete_failures=False) as fp:
                    fp.write('GONE')
                    raise ValueError
            assert read_text(filename) == 'hello'

            with self.assertRaises(IOError) as m:
                with safer.open(filename, 'w') as fp:
                    fp.write('OK!')
            assert 'Tempfile' in m.exception.args[0]
            assert 'exists' in m.exception.args[0]
            assert read_text(filename) == 'hello'

    def test_read(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')
            with safer.open(filename, 'r') as fp:
                assert fp.read() == 'c'

    def test_read2(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')
            with safer.open(filename, 'r+') as fp:
                assert fp.read() == 'c'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'a') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'c'

    def test_printer(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.printer(filename) as print:
                print('hello')
            assert read_text(filename) == 'hello\n'

    def test_printer_errors(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.printer(filename, 'w'):
                pass
            with self.assertRaises(ValueError) as m:
                with safer.printer(filename, 'r'):
                    pass
            assert 'read-only' in m.exception.args[0]

            with self.assertRaises(ValueError) as m:
                with safer.printer(filename, 'rb'):
                    pass
            assert 'binary' in m.exception.args[0]


def read_text(filename):
    with open(filename) as fp:
        return fp.read()


def write_text(filename, text):
    with open(filename, 'w') as fp:
        fp.write(text)


try:
    from tempfile import TemporaryDirectory

except ImportError:
    # Python 2.7 doesn't have TemporaryDirectory, so make a simple replacement.
    # Will not work if tests are run in parallel threads or cores!

    from contextlib import contextmanager
    import shutil

    @contextmanager
    def TemporaryDirectory():
        name = '/tmp/.safer.python27.testdir'
        os.mkdir(name)
        try:
            yield name
        finally:
            try:
                shutil.rmtree(name)
            except Exception:
                pass
