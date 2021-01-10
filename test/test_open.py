from . import helpers
from pathlib import Path
import os
import safer
import stat
import tdir
import unittest

FILENAME = Path('one')


@helpers.temps(safer.open)
@tdir
class TestSafer(unittest.TestCase):
    def test_open(self, safer_open):
        with safer_open(FILENAME, 'w') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

    def test_no_copy(self, safer_open):
        with safer_open(FILENAME, 'a') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

    def test_copy(self, safer_open):
        FILENAME.write_text('c')
        with safer_open(FILENAME, 'a') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'chello'

    def test_open_dry(self, safer_open):
        results = []
        with safer.open(FILENAME, 'w', dry_run=results.append) as fp:
            fp.write('hello')
        assert not FILENAME.exists()
        assert results == ['hello']

    def test_no_copy_dry(self, safer_open):
        with safer_open(FILENAME, 'a', dry_run=True) as fp:
            fp.write('hello')
        assert not FILENAME.exists()

    def test_copy_dry(self, safer_open):
        FILENAME.write_text('c')
        with safer_open(FILENAME, 'a', dry_run=True) as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'c'

    def test_error(self, safer_open):
        FILENAME.write_text('hello')

        with self.assertRaises(ValueError):
            with safer_open(FILENAME, 'w') as fp:
                fp.write('GONE')
                raise ValueError

        assert FILENAME.read_text() == 'hello'

    def test_make_parents(self, safer_open):
        FILENAME = Path('foo/test.txt')
        with self.assertRaises(IOError):
            with safer.open(FILENAME, 'w'):
                pass

        with safer_open(FILENAME, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

    def test_two_errors(self, safer_open):
        uses_files = safer_open is not safer.open

        FILENAME.write_text('hello')
        if uses_files:
            before = set(os.listdir('.'))

        with self.assertRaises(ValueError):
            with safer_open(FILENAME, 'w') as fp:
                fp.write('GONE')
                raise ValueError
        assert FILENAME.read_text() == 'hello'

        if uses_files:
            after = set(os.listdir('.'))
            assert before == after

        with self.assertRaises(ValueError):
            with safer_open(FILENAME, 'w', delete_failures=False) as fp:
                fp.write('GONE')
                raise ValueError

        assert FILENAME.read_text() == 'hello'

        if uses_files:
            after = set(os.listdir('.'))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

        with safer_open(FILENAME, 'w') as fp:
            fp.write('OK!')
            if uses_files:
                after = set(os.listdir('.'))
                assert len(before) + 2 == len(after)
                assert len(after.difference(before)) == 2

        assert FILENAME.read_text() == 'OK!'

        if uses_files:
            after = set(os.listdir('.'))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

    def test_error_with_copy(self, safer_open):
        FILENAME.write_text('hello')

        with self.assertRaises(ValueError):
            with safer_open(FILENAME, 'a') as fp:
                fp.write('GONE')
                raise ValueError

        assert FILENAME.read_text() == 'hello'

    def test_file_perms(self, safer_open):
        Path('test2.txt').write_text('hello')

        with safer_open(FILENAME, 'w') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'
        mode = os.stat(FILENAME).st_mode
        assert mode in (0o100664, 0o100644), stat.filemode(mode)
        new_mode = mode & 0o100770

        os.chmod(FILENAME, new_mode)
        with safer_open(FILENAME, 'w') as fp:
            fp.write('bye')
        assert FILENAME.read_text() == 'bye'
        assert os.stat(FILENAME).st_mode == new_mode

        with safer_open(FILENAME, 'a') as fp:
            fp.write(' there')
        assert FILENAME.read_text() == 'bye there'
        assert os.stat(FILENAME).st_mode == new_mode

    def test_line_buffering(self, safer_open):
        temp_file = safer_open is not safer.open
        sp = safer.printer(FILENAME, buffering=1, temp_file=temp_file)
        with sp as print:
            print('foo')
            print('b', end='')
            print('ar')
        assert FILENAME.read_text() == 'foo\nbar\n'

    def test_binary(self, safer_open):
        with safer_open(FILENAME, 'wb') as fp:
            fp.write(b'hello')
            fp.write(b' there')
            with self.assertRaises(TypeError):
                fp.write('hello')

        with open(FILENAME, 'rb') as fp:
            assert fp.read() == b'hello there'
        with safer.open(FILENAME, 'rb') as fp:
            assert fp.read() == b'hello there'

    def test_basic_write(self, safer_open):
        with safer_open(FILENAME, 'w'):
            pass
        assert os.path.exists(FILENAME), FILENAME

    def test_mode_x(self, safer_open):
        with safer_open(FILENAME, 'x') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

        with self.assertRaises(FileExistsError):
            with safer_open(FILENAME, 'x') as fp:
                fp.write('mode x')

    def test_mode_t(self, safer_open):
        with safer_open(FILENAME, 'wt') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

    def test_symlink_file(self, safer_open):
        with safer_open(FILENAME, 'w') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

        sym_filename = FILENAME.with_suffix('.sym')
        os.symlink(FILENAME, sym_filename)
        with safer_open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert FILENAME.read_text() == 'overwritten'

    def test_symlink_directory(self, safer_open):
        FILENAME = Path('sub/test.txt')
        with safer_open(FILENAME, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'
        os.symlink(Path('sub'), Path('sub.sym'), target_is_directory=True)

        sym_filename = Path('sub.sym/test.txt')
        with safer_open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert FILENAME.read_text() == 'overwritten'

    def test_file_exists_error(self, safer_open):
        with safer_open(FILENAME, 'wt') as fp:
            fp.write('hello')
        assert FILENAME.read_text() == 'hello'

        with safer_open(FILENAME, 'wt') as fp:
            fp.write('goodbye')
        assert FILENAME.read_text() == 'goodbye'
