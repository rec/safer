from __future__ import print_function
from unittest import TestCase, skipIf
import doc_safer
import os
import platform
import pydoc
import safer
import warnings


class TestSafer(TestCase):
    def test_open(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.open(filename, 'w') as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_simple_writer(self):
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            with TemporaryDirectory() as td:
                filename = td + '/test.txt'
                with safer.writer(filename) as fp:
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

    def test_make_parents(self):
        with TemporaryDirectory() as td:
            filename = td + '/foo/test.txt'
            with self.assertRaises(IOError):
                with safer.open(filename, 'w'):
                    pass

            with safer.open(filename, 'w', make_parents=True) as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'

    def test_two_errors(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')
            before = set(os.listdir(td))

            with self.assertRaises(ValueError):
                with safer.open(filename, 'w') as fp:
                    fp.write('GONE')
                    raise ValueError
            assert read_text(filename) == 'hello'

            after = set(os.listdir(td))
            assert before == after

            with self.assertRaises(ValueError):
                with safer.open(filename, 'w', delete_failures=False) as fp:
                    fp.write('GONE')
                    raise ValueError

            assert read_text(filename) == 'hello'
            after = set(os.listdir(td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

            with safer.open(filename, 'w') as fp:
                fp.write('OK!')
                after = set(os.listdir(td))
                assert len(before) + 2 == len(after)
                assert len(after.difference(before)) == 2

            assert read_text(filename) == 'OK!'

            after = set(os.listdir(td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

    def test_explicit_close(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')
            assert read_text(filename) == 'hello'
            before = set(os.listdir(td))

            fp = safer.open(filename, 'w')
            fp.write('OK!')
            assert read_text(filename) == 'hello'

            after = set(os.listdir(td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

            fp.close()

            self.assertEqual(read_text(filename), 'OK!')
            assert read_text(filename) == 'OK!'
            after = set(os.listdir(td))
            assert before == after

    def test_read(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')
            with safer.open(filename, 'r+') as fp:
                assert fp.read() == 'hello'

    def test_error_with_copy(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            write_text(filename, 'hello')

            with self.assertRaises(ValueError):
                with safer.open(filename, 'a') as fp:
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

            with self.assertRaises(ValueError) as m:
                with safer.printer(filename, 'wb'):
                    pass
            assert 'binary mode' in m.exception.args[0].lower()

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

            with safer.open(filename, 'w') as fp:
                fp.write('hello')
            assert read_text(filename) == 'hello'
            mode = os.stat(filename).st_mode
            assert mode in (0o100664, 0o100644)
            new_mode = mode & 0o100770

            os.chmod(filename, new_mode)
            with safer.open(filename, 'w') as fp:
                fp.write('bye')
            assert read_text(filename) == 'bye'
            assert os.stat(filename).st_mode == new_mode

            with safer.open(filename, 'a') as fp:
                fp.write(' there')
            assert read_text(filename) == 'bye there'
            assert os.stat(filename).st_mode == new_mode

    def test_int_filename(self):
        with self.assertRaises(TypeError) as m:
            with safer.open(1, 'w') as fp:
                fp.write('hello')

        assert m.exception.args[0] == '`name` argument must be string, not int'

    @skipIf(safer.IS_PY2, 'Needs Python 3')
    def test_help(self):
        for name in safer.__all__:
            func = getattr(safer, name)
            value = pydoc.render_doc(func, title='%s')
            assert value.startswith('function %s in module safer' % name)

    def test_line_buffering(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with self.assertRaises(ValueError) as m:
                safer.open(filename, 'wb', buffering=1)
            msg = 'buffering = 1 only allowed for text streams'
            assert m.exception.args[0] == msg

            with safer.printer(filename, buffering=1) as print:
                print('foo')
                print('b', end='')
                print('ar')
            assert read_text(filename) == 'foo\nbar\n'

    @skipIf(safer.IS_PY2, 'Needs Python 3')
    def test_binary(self):
        with TemporaryDirectory() as td:
            filename = td + '/test.txt'
            with safer.open(filename, 'wb') as fp:
                fp.write(b'hello')
                fp.write(b' there')
                with self.assertRaises(TypeError):
                    fp.write('hello')

            with open(filename, 'rb') as fp:
                assert fp.read() == b'hello there'
            with safer.open(filename, 'rb') as fp:
                assert fp.read() == b'hello there'


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
