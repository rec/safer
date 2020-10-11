from . import helpers
import os
import safer
import stat


@helpers.temps(safer.open)
class TestSafer(helpers.TestCase):
    def test_open(self, safer_open):
        with safer_open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_no_copy(self, safer_open):
        with safer_open(self.filename, 'a') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_copy(self, safer_open):
        self.filename.write_text('c')
        with safer_open(self.filename, 'a') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'chello'

    def test_open_dry(self, safer_open):
        results = []
        with safer.open(self.filename, 'w', dry_run=results.append) as fp:
            fp.write('hello')
        assert not self.filename.exists()
        assert results == ['hello']

    def test_no_copy_dry(self, safer_open):
        with safer_open(self.filename, 'a', dry_run=True) as fp:
            fp.write('hello')
        assert not self.filename.exists()

    def test_copy_dry(self, safer_open):
        self.filename.write_text('c')
        with safer_open(self.filename, 'a', dry_run=True) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'c'

    def test_error(self, safer_open):
        self.filename.write_text('hello')

        with self.assertRaises(ValueError):
            with safer_open(self.filename, 'w') as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

    def test_make_parents(self, safer_open):
        self.filename = self.td / 'foo/test.txt'
        with self.assertRaises(IOError):
            with safer.open(self.filename, 'w'):
                pass

        with safer_open(self.filename, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_two_errors(self, safer_open):
        uses_files = safer_open is not safer.open

        self.filename.write_text('hello')
        if uses_files:
            before = set(os.listdir(self.td))

        with self.assertRaises(ValueError):
            with safer_open(self.filename, 'w') as fp:
                fp.write('GONE')
                raise ValueError
        assert self.filename.read_text() == 'hello'

        if uses_files:
            after = set(os.listdir(self.td))
            assert before == after

        with self.assertRaises(ValueError):
            with safer_open(self.filename, 'w', delete_failures=False) as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

        if uses_files:
            after = set(os.listdir(self.td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

        with safer_open(self.filename, 'w') as fp:
            fp.write('OK!')
            if uses_files:
                after = set(os.listdir(self.td))
                assert len(before) + 2 == len(after)
                assert len(after.difference(before)) == 2

        assert self.filename.read_text() == 'OK!'

        if uses_files:
            after = set(os.listdir(self.td))
            assert len(before) + 1 == len(after)
            assert len(after.difference(before)) == 1

    def test_error_with_copy(self, safer_open):
        self.filename.write_text('hello')

        with self.assertRaises(ValueError):
            with safer_open(self.filename, 'a') as fp:
                fp.write('GONE')
                raise ValueError

        assert self.filename.read_text() == 'hello'

    def test_file_perms(self, safer_open):
        (self.td / 'test2.txt').write_text('hello')

        with safer_open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'
        mode = os.stat(self.filename).st_mode
        assert mode in (0o100664, 0o100644), stat.filemode(mode)
        new_mode = mode & 0o100770

        os.chmod(self.filename, new_mode)
        with safer_open(self.filename, 'w') as fp:
            fp.write('bye')
        assert self.filename.read_text() == 'bye'
        assert os.stat(self.filename).st_mode == new_mode

        with safer_open(self.filename, 'a') as fp:
            fp.write(' there')
        assert self.filename.read_text() == 'bye there'
        assert os.stat(self.filename).st_mode == new_mode

    def test_line_buffering(self, safer_open):
        temp_file = safer_open is not safer.open
        sp = safer.printer(self.filename, buffering=1, temp_file=temp_file)
        with sp as print:
            print('foo')
            print('b', end='')
            print('ar')
        assert self.filename.read_text() == 'foo\nbar\n'

    def test_binary(self, safer_open):
        with safer_open(self.filename, 'wb') as fp:
            fp.write(b'hello')
            fp.write(b' there')
            with self.assertRaises(TypeError):
                fp.write('hello')

        with open(self.filename, 'rb') as fp:
            assert fp.read() == b'hello there'
        with safer.open(self.filename, 'rb') as fp:
            assert fp.read() == b'hello there'

    def test_basic_write(self, safer_open):
        with safer_open(self.filename, 'w'):
            pass
        assert os.path.exists(self.filename), self.filename

    def test_mode_x(self, safer_open):
        with safer_open(self.filename, 'x') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        with self.assertRaises(FileExistsError):
            with safer_open(self.filename, 'x') as fp:
                fp.write('mode x')

    def test_mode_t(self, safer_open):
        with safer_open(self.filename, 'wt') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

    def test_symlink_file(self, safer_open):
        with safer_open(self.filename, 'w') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        sym_filename = self.filename.with_suffix('.sym')
        os.symlink(self.filename, sym_filename)
        with safer_open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert self.filename.read_text() == 'overwritten'

    def test_symlink_directory(self, safer_open):
        self.filename = self.td / 'sub/test.txt'
        with safer_open(self.filename, 'w', make_parents=True) as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'
        os.symlink(
            self.td / 'sub', self.td / 'sub.sym', target_is_directory=True
        )

        sym_filename = self.td / 'sub.sym/test.txt'
        with safer_open(sym_filename, 'w') as fp:
            fp.write('overwritten')
        assert self.filename.read_text() == 'overwritten'

    def test_file_exists_error(self, safer_open):
        with safer_open(self.filename, 'wt') as fp:
            fp.write('hello')
        assert self.filename.read_text() == 'hello'

        with safer_open(self.filename, 'wt') as fp:
            fp.write('goodbye')
        assert self.filename.read_text() == 'goodbye'


class TestSaferFiles(helpers.TestCase):
    def test_all_modes(self):
        modes = 'w', 'r', 'a', 'r+', 'w+', 'a', 'a+'

        for m in modes:
            with safer.open(self.filename, m, temp_file=True):
                pass
            with safer.open(self.filename, m + 'b', temp_file=True):
                pass

    def test_explicit_close(self):
        self.filename.write_text('hello')
        assert self.filename.read_text() == 'hello'
        before = set(os.listdir(self.td))

        fp = safer.open(self.filename, 'w', temp_file=True)
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

    def test_temp_file1(self):
        temp_file = self.filename.with_suffix('.temp_file')
        with safer.open(self.filename, 'w', temp_file=temp_file) as fp:
            assert temp_file.exists()
            assert os.path.exists(temp_file)
            fp.write('hello')

        assert self.filename.read_text() == 'hello'
        assert not temp_file.exists()

    def test_temp_file2(self):
        temp_file = self.filename.with_suffix('.temp_file')

        with self.assertRaises(ValueError) as e:
            with safer.open(self.filename, 'w', temp_file=temp_file) as fp:
                assert temp_file.exists()
                fp.write('hello')
                raise ValueError('Expected')
        assert e.exception.args[0] == 'Expected'

        assert not self.filename.exists()
        assert not temp_file.exists()

    def test_temp_file3(self):
        temp_file = self.filename.with_suffix('.temp_file')
        with safer.open(
            self.filename, 'w', temp_file=temp_file, delete_failures=False
        ) as fp:
            assert os.path.exists(temp_file)
            fp.write('hello')

        assert self.filename.read_text() == 'hello'
        assert not temp_file.exists()

    def test_temp_file4(self):
        temp_file = self.filename.with_suffix('.temp_file')
        with self.assertRaises(ValueError) as e:
            with safer.open(
                self.filename, 'w', temp_file=temp_file, delete_failures=False
            ) as fp:
                assert os.path.exists(temp_file)
                fp.write('hello')
                raise ValueError('Expected')
        assert e.exception.args[0] == 'Expected'

        assert not self.filename.exists()
        assert temp_file.exists()

    def test_read(self):
        self.filename.write_text('hello')
        with safer.open(self.filename, 'r+', temp_file=True) as fp:
            assert fp.read() == 'hello'

        with self.assertRaises(ValueError):
            safer.open(self.filename, 'r+')

    def test_int_filename(self):
        with self.assertRaises(TypeError) as m:
            with safer.open(1, 'w', temp_file=True) as fp:
                fp.write('hello')

        arg = m.exception.args[0]
        assert arg == '`name` must be string, not int'

    def _error(self, mode='w', **kwds):
        with self.assertRaises(ValueError) as e:
            safer.open(self.filename, mode, temp_file=True, **kwds)
        return e.exception.args[0]

    def test_errors1(self):
        a = self._error(closefd=False)
        assert a == 'Cannot use closefd=False with file name'

    def test_errors2(self):
        a = self._error('bt')
        assert a == 'can\'t have text and binary mode at once'

    def test_errors3(self):
        a = self._error('wb', newline=True)
        assert a == 'binary mode doesn\'t take a newline argument'

    def test_errors4(self):
        a = self._error('wb', encoding='utf8')
        assert a == 'binary mode doesn\'t take an encoding argument'

    def test_errors5(self):
        a = self._error('wb', errors=True)
        assert a == 'binary mode doesn\'t take an errors argument'
