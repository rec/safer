from __future__ import print_function
from unittest import TestCase, skipIf
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

    def test_create_parent(self):
        with TemporaryDirectory() as td:
            filename = td + '/foo/test.txt'
            with self.assertRaises(OSError):
                with safer.writer(filename):
                    pass

            with safer.writer(filename, create_parent=True) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_two_errors(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')
            before = set(os.listdir(td))

            with self.assertRaises(ValueError):
                with safer.writer(filename) as fp:
                    fp.write('GONE')
                    raise ValueError
            assert read_text(filename) == 'hello'

            after = set(os.listdir(td))
            assert before == after

            with self.assertRaises(ValueError):
                with safer.writer(filename, delete_failures=False) as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'hello'
            after = set(os.listdir(td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

            with safer.writer(filename) as fp:
                fp.write('OK!')
                after = set(os.listdir(td))
                assert len(before) + 2 == len(after)
                assert len(after.difference(before)) == 2

            assert read_text(filename) == 'OK!'

            after = set(os.listdir(td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

    def test_read(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')
            with safer.writer(filename, 'r+') as fp:
                assert fp.read() == 'hello'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.writer(filename, 'a') as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'hello'

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

    @skipIf(platform.python_version() < '3.6', 'Needs Python 3.6 or greater')
    def test_make_doc(self):
        with TemporaryDirectory() as td:
            filename = td + '/README.rst'
            with safer.printer(filename) as print:
                doc_safer.make_doc(print)
            actual = read_text(filename)
            in_repo = read_text(doc_safer.README_FILE)
            assert actual == in_repo

    def test_file_perms(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'

            write_text(td + '/test2.txt', 'hello')

            with safer.writer(filename) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'
            mode = os.stat(filename).st_mode
            assert mode in (0o100664, 0o100644)
            new_mode = mode & 0o100770

            os.chmod(filename, new_mode)
            with safer.writer(filename) as fp:
                fp.write('bye')
            assert read_text(filename) == 'bye'
            assert os.stat(filename).st_mode == new_mode

            with safer.writer(filename, 'a') as fp:
                fp.write(' there')
            assert read_text(filename) == 'bye there'
            assert os.stat(filename).st_mode == new_mode


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

    import contextlib
    import itertools
    import shutil
    import tempfile
    import threading

    @contextlib.contextmanager
    def TemporaryDirectory():
        td = tempfile.gettempdir()
        root = '%s/safer-%d' % (td, threading.current_thread().ident)
        names = ('%s.%d' % (root, i) for i in itertools.count())
        name = next(n for n in names if not os.path.exists(n))
        os.mkdir(name)
        try:
            yield name
        finally:
            try:
                shutil.rmtree(name)
            except Exception:
                pass
