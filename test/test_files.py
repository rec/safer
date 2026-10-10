import os
import shutil
import unittest
from pathlib import Path

import pytest
import tdir

import safer

FILENAME = Path('one')


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_explicit_failure_flag_aborts_normal_exit(temp_file):
    FILENAME.write_text('original')
    with safer.open(FILENAME, 'w', temp_file=temp_file) as fp:
        fp.write('replacement')
        fp.safer_failed = True
    assert FILENAME.read_text() == 'original'
    assert list(Path('.').iterdir()) == [FILENAME]


@tdir
def test_failed_stream_construction_removes_scratch():
    with pytest.raises(LookupError):
        safer.open(FILENAME, 'w', encoding='no-such-codec', temp_file=True)
    assert list(Path('.').iterdir()) == []


@tdir
def test_failed_snapshot_copy_removes_scratch(monkeypatch):
    FILENAME.write_text('original')

    def fail(source, target):
        Path(target).write_text('partial')
        raise OSError('disk full')

    monkeypatch.setattr(shutil, 'copy2', fail)
    with pytest.raises(OSError, match='disk full'):
        safer.open(FILENAME, 'a', temp_file=True)
    assert FILENAME.read_text() == 'original'
    assert list(Path('.').iterdir()) == [FILENAME]


@tdir
def test_successful_file_dry_run_removes_scratch():
    values = []
    for dry_run in (True, values.append):
        with safer.open(
            FILENAME,
            'w',
            temp_file='scratch',
            dry_run=dry_run,
            delete_failures=False,
        ) as fp:
            fp.write('payload')
        assert not Path('scratch').exists()
        assert not FILENAME.exists()
    assert values == ['payload']


@tdir
def test_truncating_update_starts_empty():
    FILENAME.write_text('original')
    with safer.open(FILENAME, 'w+', temp_file=True) as fp:
        assert fp.read() == ''
        fp.write('replacement')
    assert FILENAME.read_text() == 'replacement'


@tdir
def test_update_requires_existing_target():
    for mode in ('r+', 'r+b'):
        with pytest.raises(FileNotFoundError):
            safer.open(FILENAME, mode, temp_file=True)
        assert list(Path('.').iterdir()) == []


@tdir
def test_temporary_path_must_be_unoccupied():
    FILENAME.write_text('original')
    scratch = Path('scratch')
    scratch.write_text('unrelated')
    with pytest.raises(FileExistsError):
        safer.open(FILENAME, 'w', temp_file=scratch)
    assert scratch.read_text() == 'unrelated'
    with pytest.raises(ValueError, match='differ'):
        safer.open(FILENAME, 'w', temp_file=FILENAME)
    alias = Path('alias')
    os.link(FILENAME, alias)
    with pytest.raises(FileExistsError):
        safer.open(FILENAME, 'w', temp_file=alias)
    assert FILENAME.read_text() == 'original'
    assert alias.read_text() == 'original'


@tdir
def test_memory_encoding_failure_preserves_original():
    FILENAME.write_text('original')
    before = set(Path('.').iterdir())
    with pytest.raises(UnicodeEncodeError):
        with safer.open(FILENAME, 'w', encoding='ascii') as fp:
            fp.write('é')
    assert FILENAME.read_text() == 'original'
    assert set(Path('.').iterdir()) == before


@tdir
def test_memory_replacement_failure_preserves_original(monkeypatch):
    FILENAME.write_text('original')
    before = set(Path('.').iterdir())

    def fail(source, target):
        raise OSError('replacement failed')

    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError, match='replacement failed'):
        with safer.open(FILENAME, 'w') as fp:
            fp.write('replacement')
    assert FILENAME.read_text() == 'original'
    assert set(Path('.').iterdir()) == before


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

    def test_close_is_idempotent(self):
        fp = safer.open(FILENAME, 'w')
        fp.write('hello')
        fp.close()
        fp.close()
        assert FILENAME.read_text() == 'hello'

    def test_unique_temporary_files(self):
        first = safer.open(FILENAME, 'w', temp_file=True)
        second = safer.open(FILENAME, 'w', temp_file=True)
        assert first.safer_closer.temp_file != second.safer_closer.temp_file
        first.close()
        second.close()

    def test_dry_run_uses_requested_encoding(self):
        results = []
        with safer.open(
            FILENAME,
            'w',
            encoding='latin-1',
            dry_run=results.append,
            temp_file=True,
        ) as fp:
            fp.write('é')
        assert results == ['é']

    def test_dry_run_matches_memory_contents(self):
        results = []
        with safer.open(
            FILENAME,
            'w',
            newline=None,
            dry_run=results.append,
            temp_file=True,
        ) as fp:
            fp.write('one\r\ntwo')
        assert results == ['one\r\ntwo']

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
        assert arg == '`name` must be path-like, not int'

    def test_path_like_filename(self):
        class Name:
            def __fspath__(self):
                return 'path-like.txt'

        with safer.open(Name(), 'w') as fp:
            fp.write('hello')
        assert Path('path-like.txt').read_text() == 'hello'

    def test_invalid_temp_file(self):
        with self.assertRaises(TypeError) as e:
            safer.open(FILENAME, 'w', temp_file=1)
        assert e.exception.args[0] == 'temp_file must be a bool, string, or Path'

    def _error(self, mode='w', **kwds):
        with self.assertRaises(ValueError) as e:
            safer.open(FILENAME, mode, temp_file=True, **kwds)
        return e.exception.args[0]

    def test_errors1(self):
        a = self._error(closefd=False)
        assert a == 'Cannot use closefd=False with file name'

    def test_errors2(self):
        a = self._error('bt')
        assert a == "can't have text and binary mode at once"

    def test_errors3(self):
        a = self._error('wb', newline=True)
        assert a == "binary mode doesn't take a newline argument"

    def test_errors4(self):
        a = self._error('wb', encoding='utf8')
        assert a == "binary mode doesn't take an encoding argument"

    def test_errors5(self):
        a = self._error('wb', errors=True)
        assert a == "binary mode doesn't take an errors argument"
