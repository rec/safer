from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import functools
import os
import pydoc
import safer

copen = functools.partial(safer.open, mode='w', temp_file=False)


class TestSafer(TestCase):
    def setUp(self):
        self.td_context = TemporaryDirectory()
        self.td = Path(self.td_context.__enter__())
        self.filename = self.td / 'test.txt'

    def tearDown(self):
        self.td_context.__exit__(None, None, None)

    def test_open(self):
        with safer.open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_open_memory(self):
        with copen(self.filename) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_no_copy(self):
        with safer.open(self.filename, 'a') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_no_copy_memory(self):
        with copen(self.filename) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_copy(self):
        self.filename.write_text('c')
        with safer.open(self.filename, 'a') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'chello'

    def test_copy_memory(self):
        self.filename.write_text('c')
        with copen(self.filename, mode='a') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'chello'

    def test_error(self):
        self.filename.write_text('hello')

        with self.assertRaises(ValueError):
            with safer.open(self.filename, 'w') as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

    def test_error_memory(self):
        self.filename.write_text('hello')

        with self.assertRaises(ValueError):
            with copen(self.filename) as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

    def test_make_parents(self):
        self.filename = self.td / 'foo/test.txt'
        with self.assertRaises(IOError):
            with safer.open(self.filename, 'w'):
                pass

        with safer.open(self.filename, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_two_errors(self):
        self.filename.write_text('hello')
        before = set(os.listdir(self.td))

        with self.assertRaises(ValueError):
            with safer.open(self.filename, 'w') as fp:
                fp.write('GONE')
                raise ValueError
        assert self.filename.read_text() == 'hello'

        after = set(os.listdir(self.td))
        assert before == after

        with self.assertRaises(ValueError):
            with safer.open(self.filename, 'w', delete_failures=False) as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'
        after = set(os.listdir(self.td))
        assert len(before) + 1 == len(after)
        assert len(after.difference(before)) == 1

        with safer.open(self.filename, 'w') as fp:
            fp.write('OK!')
            after = set(os.listdir(self.td))
            assert len(before) + 2 == len(after)
            assert len(after.difference(before)) == 2

        assert self.filename.read_text() == 'OK!'

        after = set(os.listdir(self.td))
        assert len(before) + 1 == len(after)
        assert len(after.difference(before)) == 1

    def test_explicit_close(self):
        self.filename.write_text('hello')
        assert self.filename.read_text() == 'hello'
        before = set(os.listdir(self.td))

        fp = safer.open(self.filename, 'w')
        fp.write('OK!')
        assert self.filename.read_text() == 'hello'

        after = set(os.listdir(self.td))
        assert len(before) + 1 == len(after)
        assert len(after.difference(before)) == 1

        fp.close()

        self.assertEqual(self.filename.read_text(), 'OK!')
        assert self.filename.read_text() == 'OK!'
        after = set(os.listdir(self.td))
        assert before == after

    def test_read(self):
        self.filename.write_text('hello')
        with safer.open(self.filename, 'r+') as fp:
            assert fp.read() == 'hello'

    def test_error_with_copy(self):
        self.filename.write_text('hello')

        with self.assertRaises(ValueError):
            with safer.open(self.filename, 'a') as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

    def test_file_perms(self):
        (self.td / 'test2.txt').write_text('hello')

        with safer.open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'
        mode = os.stat(self.filename).st_mode
        assert mode in (0o100664, 0o100644)
        new_mode = mode & 0o100770

        os.chmod(self.filename, new_mode)
        with safer.open(self.filename, 'w') as fp:
            fp.write('bye')
        assert self.filename.read_text() == 'bye'
        assert os.stat(self.filename).st_mode == new_mode

        with safer.open(self.filename, 'a') as fp:
            fp.write(' there')
        assert self.filename.read_text() == 'bye there'
        assert os.stat(self.filename).st_mode == new_mode

    def test_int_filename(self):
        with self.assertRaises(TypeError) as m:
            with safer.open(1, 'w') as fp:
                fp.write('hello')

        arg = m.exception.args[0]
        assert arg == '``name`` argument must be string, not int'

    def test_help(self):
        for name in safer.__all__:
            func = getattr(safer, name)
            value = pydoc.render_doc(func, title='%s')
            assert value.startswith('function %s in module safer' % name)

    def test_line_buffering(self):
        with self.assertRaises(ValueError) as m:
            safer.open(self.filename, 'wb', buffering=1)
        msg = 'buffering = 1 only allowed for text streams'
        assert m.exception.args[0] == msg

        with safer.printer(self.filename, buffering=1) as print:
            print('foo')
            print('b', end='')
            print('ar')
        assert self.filename.read_text() == 'foo\nbar\n'

    def test_binary(self):
        with safer.open(self.filename, 'wb') as fp:
            fp.write(b'hello')
            fp.write(b' there')
            with self.assertRaises(TypeError):
                fp.write('hello')

        with open(self.filename, 'rb') as fp:
            assert fp.read() == b'hello there'
        with safer.open(self.filename, 'rb') as fp:
            assert fp.read() == b'hello there'

    def test_all_modes(self):
        modes = 'w', 'r', 'a', 'r+', 'w+', 'a', 'a+'

        for m in modes:
            with safer.open(self.filename, m):
                pass
            with safer.open(self.filename, m + 'b'):
                pass

    def test_mode_x(self):
        with safer.open(self.filename, 'x') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        with self.assertRaises(FileExistsError):
            with safer.open(self.filename, 'x') as fp:
                fp.write('mode x')

    def test_mode_t(self):
        with safer.open(self.filename, 'wt') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        with self.assertRaises(ValueError) as m:
            safer.open(self.filename, 'bt')
        assert m.exception.args[0] == 'Inconsistent mode bt'

    def test_symlink_file(self):
        with safer.open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        sym_filename = self.filename.with_suffix('.sym')
        os.symlink(self.filename, sym_filename)
        with safer.open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert self.filename.read_text() == 'overwritten'

    def test_symlink_directory(self):
        self.filename = self.td / 'sub/test.txt'
        with safer.open(self.filename, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'
        os.symlink(
            self.td / 'sub', self.td / 'sub.sym', target_is_directory=True
        )

        sym_filename = self.td / 'sub.sym/test.txt'
        with safer.open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert self.filename.read_text() == 'overwritten'

    def test_file_exists_error(self):
        with safer.open(self.filename, 'wt') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        with safer.open(self.filename, 'wt') as fp:
            fp.write('goodbye')
        assert self.filename.read_text() == 'goodbye'
