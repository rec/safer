from __future__ import print_function
from unittest import TestCase
import doc_safer
import os
import platform
import safer


class TestSafer(TestCase):
    def test_simple(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.writer(filename) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_no_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.writer(filename, 'a') as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')
            with safer.writer(filename, 'a') as fp:
                fp.write('hello')
            assert read_text(filename) == 'chello'

    def test_error(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.writer(filename) as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'hello'

    def test_create_parents(self):
        with TemporaryDirectory() as td:
            filename = td + '/foo/test.txt'
            with self.assertRaises(IOError):
                with safer.writer(filename):
                    pass

            with safer.writer(filename, create_parents=True) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_two_errors(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.writer(filename, delete_failures=False) as fp:
                    fp.write('GONE')
                    raise ValueError
            assert read_text(filename) == 'hello'

            with self.assertRaises(IOError) as m:
                with safer.writer(filename) as fp:
                    fp.write('OK!')
            assert 'Tempfile' in m.exception.args[0]
            assert 'exists' in m.exception.args[0]
            assert read_text(filename) == 'hello'

    def test_read(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')
            with safer.writer(filename, 'r+') as fp:
                assert fp.read() == 'c'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'c')

            with self.assertRaises(ValueError):
                with safer.writer(filename, 'a') as fp:
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
            with safer.printer(filename):
                pass
            with self.assertRaises(IOError) as m:
                with safer.printer(filename, 'r'):
                    pass
            assert 'not open' in m.exception.args[0].lower()

            with self.assertRaises(IOError) as m:
                with safer.printer(filename, 'rb'):
                    pass
            assert 'not open' in m.exception.args[0].lower()

    def test_make_doc(self):
        if platform.python_version() < '3.6':
            return
        with TemporaryDirectory() as td:
            filename = td + '/README.rst'
            with safer.printer(filename) as print:
                doc_safer.make_doc(print)
            actual = read_text(filename)
            in_repo = read_text(doc_safer.README_FILE)
            assert actual == in_repo


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
