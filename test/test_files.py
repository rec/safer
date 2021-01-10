from pathlib import Path
import os
import safer
import tdir
import unittest

FILENAME = Path('one')


@tdir
class TestSaferFiles(unittest.TestCase):
    def test_all_modes(self):
        modes = 'w', 'r', 'a', 'r+', 'w+', 'a', 'a+'

        for m in modes:
            with safer.open(FILENAME, m, temp_file=True):
                pass
            with safer.open(FILENAME, m + 'b', temp_file=True):
                pass

    def test_explicit_close(self):
        FILENAME.write_text('hello')
        assert FILENAME.read_text() == 'hello'
        before = set(os.listdir('.'))

        fp = safer.open(FILENAME, 'w', temp_file=True)
        fp.write('OK!')
        assert FILENAME.read_text() == 'hello'

        after = set(os.listdir('.'))
        assert len(before) + 1 == len(after)
        assert len(after.difference(before)) == 1

        fp.close()

        self.assertEqual(FILENAME.read_text(), 'OK!')
        assert FILENAME.read_text() == 'OK!'
        after = set(os.listdir('.'))
        assert before == after

    def test_temp_file1(self):
        temp_file = FILENAME.with_suffix('.temp_file')
        with safer.open(FILENAME, 'w', temp_file=temp_file) as fp:
            assert temp_file.exists()
            assert os.path.exists(temp_file)
            fp.write('hello')

        assert FILENAME.read_text() == 'hello'
        assert not temp_file.exists()

    def test_temp_file2(self):
        temp_file = FILENAME.with_suffix('.temp_file')

        with self.assertRaises(ValueError) as e:
            with safer.open(FILENAME, 'w', temp_file=temp_file) as fp:
                assert temp_file.exists()
                fp.write('hello')
                raise ValueError('Expected')
        assert e.exception.args[0] == 'Expected'

        assert not FILENAME.exists()
        assert not temp_file.exists()

    def test_temp_file3(self):
        temp_file = FILENAME.with_suffix('.temp_file')
        with safer.open(
            FILENAME, 'w', temp_file=temp_file, delete_failures=False
        ) as fp:
            assert os.path.exists(temp_file)
            fp.write('hello')

        assert FILENAME.read_text() == 'hello'
        assert not temp_file.exists()

    def test_temp_file4(self):
        temp_file = FILENAME.with_suffix('.temp_file')
        with self.assertRaises(ValueError) as e:
            with safer.open(
                FILENAME, 'w', temp_file=temp_file, delete_failures=False
            ) as fp:
                assert os.path.exists(temp_file)
                fp.write('hello')
                raise ValueError('Expected')
        assert e.exception.args[0] == 'Expected'

        assert not FILENAME.exists()
        assert temp_file.exists()

    def test_read(self):
        FILENAME.write_text('hello')
        with safer.open(FILENAME, 'r+', temp_file=True) as fp:
            assert fp.read() == 'hello'

        with self.assertRaises(ValueError):
            safer.open(FILENAME, 'r+')

    def test_int_filename(self):
        with self.assertRaises(TypeError) as m:
            with safer.open(1, 'w', temp_file=True) as fp:
                fp.write('hello')

        arg = m.exception.args[0]
        assert arg == '`name` must be string, not int'

    def _error(self, mode='w', **kwds):
        with self.assertRaises(ValueError) as e:
            safer.open(FILENAME, mode, temp_file=True, **kwds)
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
