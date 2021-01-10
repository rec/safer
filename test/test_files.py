from . import helpers
import os
import safer


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
