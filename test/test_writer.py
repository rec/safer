import io
import os
import sys
import unittest
from pathlib import Path

import pytest
import tdir

import safer

from . import helpers

FILENAME = Path('one')


@helpers.temps(safer.writer)
@tdir
class TestWriter(unittest.TestCase):
    def test_callable(self, safer_writer):
        results = []
        with safer_writer(results.append) as fp:
            fp.write('abc')
            fp.write('d')
        assert results == ['abcd']

    def test_callable_dry_run(self, safer_writer):
        results = []
        with safer_writer(results.append, dry_run=True) as fp:
            fp.write('abc')
            fp.write('d')
        assert results == []

    def test_callable_error(self, safer_writer):
        results = []
        with self.assertRaises(ValueError):
            with safer_writer(results.append) as fp:
                fp.write('abc')
                fp.write('d')
                raise ValueError
        assert results == []

    def test_nested_writers(self, safer_writer):
        with safer.open(FILENAME, 'w') as fp1:
            fp1.write('one')
            with safer_writer(fp1) as fp2:
                fp2.write('two')
                fp2.write('three')
            fp1.write('four')
        assert FILENAME.read_text() == 'onetwothreefour'

    def test_nested_writers_dry_run(self, safer_writer):
        assert not FILENAME.exists()
        with safer.open(FILENAME, 'w', dry_run=True) as fp1:
            assert not FILENAME.exists()
            fp1.write('one')
            with safer_writer(fp1, dry_run=True) as fp2:
                assert not FILENAME.exists()
                fp2.write('two')
                fp2.write('three')
            assert not FILENAME.exists()
            fp1.write('four')
        assert not FILENAME.exists()

    def test_dry_run(self, safer_writer):
        assert not FILENAME.exists()
        with safer.open(FILENAME, 'w', dry_run=True) as fp1:
            assert not FILENAME.exists()
            fp1.write('one')
            assert not FILENAME.exists()
        assert not FILENAME.exists()

    def test_dry_run_callable(self, safer_writer):
        results = []
        assert not FILENAME.exists()

        with safer_writer(dry_run=results.append) as fp:
            fp.write('one')
        assert results == ['one']

    def test_std_error(self, safer_writer):
        for file in (sys.stdout, sys.stderr, None):
            with safer_writer(file) as fp:
                fp.write('boo')
            with self.assertRaises(ValueError) as m:
                safer.writer(file, close_on_exit=True)
            assert m.exception.args[0] == 'You cannot close stdout or stderr'

    def test_file_error(self, safer_writer):
        with safer.open(FILENAME, 'w') as fp1:
            fp1.write('one')
            with self.assertRaises(ValueError):
                with safer_writer(fp1) as fp2:
                    fp2.write('two')
                    fp2.write('three')
                    raise ValueError
            fp1.write('four')
        assert FILENAME.read_text() == 'onefour'

    def test_mode_error1(self, safer_writer):
        with safer.open(FILENAME, 'w') as fp:
            pass
        with open(FILENAME) as fp:
            with self.assertRaises(ValueError) as e:
                safer_writer(fp)
            assert e.exception.args[0] == 'Stream mode "r" is not a write mode'

    def test_mode_error2(self, safer_writer):
        with open(FILENAME, 'w') as fp:
            with self.assertRaises(ValueError) as e:
                safer_writer(fp, is_binary=True)
            a = e.exception.args[0]
            assert a == 'is_binary is inconsistent with the file stream'

    def test_mode_error3(self, safer_writer):
        with open(FILENAME, 'wb') as fp:
            with self.assertRaises(ValueError) as e:
                safer_writer(fp, is_binary=False)
            a = e.exception.args[0]
            assert a == 'is_binary is inconsistent with the file stream'

    def test_unknown_type(self, safer_writer):
        with self.assertRaises(ValueError) as e:
            safer_writer(3)
        a = e.exception.args[0]
        assert a == 'Stream is not a file, a socket, or callable'

    def test_none(self, safer_writer):
        with safer_writer() as fp:
            fp.write('to stdout!\n')

    def test_falsey_stream(self, safer_writer):
        class FalseyWriter:
            def __init__(self):
                self.values = []

            def __bool__(self):
                return False

            def write(self, value):
                self.values.append(value)

        writer = FalseyWriter()
        with safer_writer(writer) as fp:
            fp.write('one')
        assert writer.values == ['one']

    def test_str(self, safer_writer):
        for file in (FILENAME, str(FILENAME)):
            with safer_writer(file) as fp:
                fp.write('one ')
                fp.write('two')
            assert FILENAME.read_text() == 'one two'
            FILENAME.write_text('')
            assert FILENAME.read_text() == ''

    def test_path_temporary_file(self, safer_writer):
        with safer_writer(FILENAME, temp_file=True) as fp:
            assert Path(fp.safer_closer.temp_file).exists()
            fp.write('one')
        assert FILENAME.read_text() == 'one'

    def test_path_chunk_size(self, safer_writer):
        with self.assertRaises(ValueError) as e:
            safer_writer(FILENAME, chunk_size=1)
        assert e.exception.args[0] == 'chunk_size only applies to streams'

    def test_invalid_temp_file(self, safer_writer):
        with self.assertRaises(TypeError) as e:
            safer_writer([], temp_file=1)
        assert e.exception.args[0] == 'temp_file must be a bool, string, or Path'

    def test_socket(self, safer_writer):
        sock = helpers.socket()
        with safer_writer(sock) as fp:
            fp.write(b'one')
            fp.write(b'two')
        assert sock.items == [b'onetwo']

    def test_socket_error(self, safer_writer):
        sock = helpers.socket()
        with self.assertRaises(ValueError):
            with safer_writer(sock) as fp:
                fp.write(b'one')
                fp.write(b'two')
                raise ValueError
        assert sock.items == []

    def test_socket_send_is_buffered(self, safer_writer):
        sock = helpers.socket()
        with safer_writer(sock) as fp:
            assert fp.send(b'one') == 3
            assert sock.items == []
        assert sock.items == [b'one']

        with self.assertRaises(ValueError):
            with safer_writer(sock) as fp:
                fp.send(b'two')
                raise ValueError
        assert sock.items == [b'one']

    def test_socket_binary_error(self, safer_writer):
        sock = helpers.socket()
        with self.assertRaises(ValueError) as m:
            safer_writer(sock, is_binary=False)
        a = m.exception.args[0]
        assert a == 'is_binary=False is inconsistent with a socket'

    def test_callable2(self, safer_writer):
        results = []
        with safer_writer(results.append) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_partial_writes(self, safer_writer):
        results = []

        def callback(s):
            accepted = min(len(s), 2)
            results.append(s[:accepted])
            return accepted

        with safer_writer(callback) as fp:
            fp.write('one')
            fp.write('two')
            fp.write('!')

        assert ''.join(results) == 'onetwo!'

    def test_zero_length_write_result(self, safer_writer):
        with self.assertRaises(BlockingIOError):
            with safer_writer(lambda value: 0) as fp:
                fp.write('one')


@tdir
def test_wrapper_bug():
    with safer.writer(FILENAME) as fp:
        fp.write('hello, world')
    assert FILENAME.read_text() == 'hello, world'


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_nonblocking_stream_none_is_no_progress(temp_file):
    class Destination(io.RawIOBase):
        def write(self, value):
            return None

    with pytest.raises(BlockingIOError):
        with safer.writer(Destination(), temp_file=temp_file) as fp:
            fp.write('payload')


@tdir
def test_callback_write_count_must_not_exceed_input():
    with pytest.raises(ValueError, match='invalid write count'):
        with safer.writer(lambda value: len(value) + 1) as fp:
            fp.write('payload')


@pytest.mark.parametrize(
    'size, error',
    [(0, ValueError), (-1, ValueError), (1.5, TypeError), (True, TypeError)],
)
@tdir
def test_invalid_chunk_size_fails_before_allocating(size, error):
    values = []
    with pytest.raises(error, match='positive integer'):
        safer.writer(values.append, temp_file='scratch', chunk_size=size)
    assert list(Path('.').iterdir()) == []


@tdir
def test_successful_stream_replay_removes_scratch():
    values = []
    with safer.writer(values.append, temp_file='scratch') as fp:
        fp.write('payload')
    assert values == ['payload']
    assert not Path('scratch').exists()


@pytest.mark.parametrize('error', [KeyboardInterrupt, SystemExit])
@tdir
def test_interrupted_replay_removes_scratch(error):
    def interrupt(value):
        raise error

    with pytest.raises(error):
        with safer.writer(interrupt, temp_file='scratch') as fp:
            fp.write('payload')
    assert not Path('scratch').exists()


@tdir
def test_cleanup_failure_preserves_delivery_error(monkeypatch, capsys):
    calls = []

    def fail_delivery(value):
        raise OSError('delivery failed')

    def fail_cleanup(path, **kwargs):
        calls.append(path)
        raise PermissionError('cleanup denied')

    fp = safer.writer(fail_delivery, temp_file='scratch')
    monkeypatch.setattr(Path, 'unlink', fail_cleanup)
    with pytest.raises(OSError, match='delivery failed'):
        with fp:
            fp.write('payload')
    assert calls == [Path('scratch')]
    assert capsys.readouterr().err == 'safer cleanup failed: cleanup denied\n'


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_delivery_failure_closes_owned_destination(temp_file):
    class Destination:
        closed = False

        def write(self, value):
            raise OSError('delivery failed')

        def close(self):
            self.closed = True
            raise OSError('close failed too')

    destination = Destination()
    with pytest.raises(OSError, match='delivery failed'):
        with safer.closer(destination, temp_file=temp_file) as fp:
            fp.write('payload')
    assert destination.closed


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_owned_socket_closes_on_success_and_failure(temp_file):
    sock = helpers.socket()
    with safer.closer(sock, temp_file=temp_file) as fp:
        fp.write(b'payload')
    assert sock.closed
    assert sock.items == [b'payload']

    sock = helpers.socket()
    with pytest.raises(ValueError):
        with safer.closer(sock, temp_file=temp_file) as fp:
            fp.write(b'payload')
            raise ValueError
    assert sock.closed
    assert sock.items == []


@tdir
def test_close_writable_without_context_manager():
    class Writer:
        def __init__(self):
            self.values = []
            self.closed = False

        def write(self, value):
            self.values.append(value)

        def close(self):
            self.closed = True

    writer = Writer()
    with safer.writer(writer, close_on_exit=True) as fp:
        fp.write('hello')
    assert writer.values == ['hello']
    assert writer.closed


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_owned_destination_closes_once(temp_file):
    class Destination:
        calls = 0

        def write(self, value):
            return len(value)

        def close(self):
            self.calls += 1

    destination = Destination()
    fp = safer.closer(destination, temp_file=temp_file)
    fp.write('payload')
    fp.close()
    fp.close()
    assert destination.calls == 1


@pytest.mark.parametrize('temp_file', [False, True])
@tdir
def test_inner_owned_failure_aborts_outer_file(temp_file):
    FILENAME.write_text('original')
    with safer.open(FILENAME, 'w') as outer:
        outer.write('header')
        with pytest.raises(ValueError):
            with safer.closer(outer, temp_file=temp_file) as inner:
                inner.write('body')
                raise ValueError
    assert FILENAME.read_text() == 'original'


@tdir
def test_stream_failure_cleans_temporary_file():
    def fail(value):
        raise OSError('expected')

    fp = safer.writer(fail, temp_file=True)
    temp_file = fp.safer_closer.temp_file
    with pytest.raises(OSError, match='expected'):
        with fp:
            fp.write('one')
    assert not os.path.exists(temp_file)

    fp = open(FILENAME, 'w')
    with safer.writer(fp, close_on_exit=True):
        fp.write('hello, world')
    assert FILENAME.read_text() == 'hello, world'


@tdir
def test_temp_file_closer():
    fp = open(FILENAME, 'w')
    with safer.writer(fp, close_on_exit=True, temp_file=True) as writer:
        writer.write('hello, world')
    assert fp.closed
    assert FILENAME.read_text() == 'hello, world'


@helpers.temps(safer.closer)
class TestCloser(unittest.TestCase):
    def test_callable_closer(self, safer_closer):
        results = []
        with safer_closer(results.append) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_callable_closer2(self, safer_closer):
        class CB:
            def __call__(self, item):
                results.append(item)

            def close(self, failed):
                results.append(('close', failed))

        results = []
        with safer_closer(CB()) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo', ('close', False)]

    def test_callable_closer3(self, safer_closer):
        class CB:
            def __call__(self, item):
                results.append(item)

            def close(self, failed):
                raise ValueError('closer3')

        results = []
        fp = safer_closer(CB())
        fp.__enter__()
        fp.write('one')
        fp.write('two')

        with self.assertRaises(ValueError) as e:
            fp.__exit__(None, None, None)

        assert e.exception.args == ('closer3',)
        assert results == ['onetwo']
