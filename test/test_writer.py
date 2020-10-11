from . import helpers
import safer
import sys


@helpers.temps(safer.writer)
class TestWriter(helpers.TestCase):
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
        with safer.open(self.filename, 'w') as fp1:
            fp1.write('one')
            with safer_writer(fp1) as fp2:
                fp2.write('two')
                fp2.write('three')
            fp1.write('four')
        assert self.filename.read_text() == 'onetwothreefour'

    def test_nested_writers_dry_run(self, safer_writer):
        assert not self.filename.exists()
        with safer.open(self.filename, 'w', dry_run=True) as fp1:
            assert not self.filename.exists()
            fp1.write('one')
            with safer_writer(fp1, dry_run=True) as fp2:
                assert not self.filename.exists()
                fp2.write('two')
                fp2.write('three')
            assert not self.filename.exists()
            fp1.write('four')
        assert not self.filename.exists()

    def test_dry_run(self, safer_writer):
        assert not self.filename.exists()
        with safer.open(self.filename, 'w', dry_run=True) as fp1:
            assert not self.filename.exists()
            fp1.write('one')
            assert not self.filename.exists()
        assert not self.filename.exists()

    def test_dry_run_callable(self, safer_writer):
        results = []
        assert not self.filename.exists()

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
        with safer.open(self.filename, 'w') as fp1:
            fp1.write('one')
            with self.assertRaises(ValueError):
                with safer_writer(fp1) as fp2:
                    fp2.write('two')
                    fp2.write('three')
                    raise ValueError
            fp1.write('four')
        assert self.filename.read_text() == 'onefour'

    def test_mode_error1(self, safer_writer):
        with safer.open(self.filename, 'w') as fp:
            pass
        with open(self.filename) as fp:
            with self.assertRaises(ValueError) as e:
                safer_writer(fp)
            assert e.exception.args[0] == 'Stream mode "r" is not a write mode'

    def test_mode_error2(self, safer_writer):
        with open(self.filename, 'w') as fp:
            with self.assertRaises(ValueError) as e:
                safer_writer(fp, is_binary=True)
            a = e.exception.args[0]
            assert a == 'is_binary is inconsistent with the file stream'

    def test_mode_error3(self, safer_writer):
        with open(self.filename, 'wb') as fp:
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

    def test_str(self, safer_writer):
        for file in (self.filename, str(self.filename)):
            with safer_writer(file) as fp:
                fp.write('one ')
                fp.write('two')
            assert self.filename.read_text() == 'one two'
            self.filename.write_text('')
            assert self.filename.read_text() == ''

    def test_socket(self, safer_writer):
        sock = socket()
        with safer_writer(sock) as fp:
            fp.write(b'one')
            fp.write(b'two')
        assert sock.items == [b'onetwo']

    def test_socket_error(self, safer_writer):
        sock = socket()
        with self.assertRaises(ValueError):
            with safer_writer(sock) as fp:
                fp.write(b'one')
                fp.write(b'two')
                raise ValueError
        assert sock.items == []

    def test_socket_binary_error(self, safer_writer):
        sock = socket()
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
            results.append(s)
            return min(len(s), 2)

        with safer_writer(callback) as fp:
            fp.write('one')
            fp.write('two')
            fp.write('!')

        assert results == ['onetwo!', 'etwo!', 'wo!', '!']


@helpers.temps(safer.closer)
class TestCloser(helpers.TestCase):
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


class socket:
    def __init__(self):
        self.items = []

    def send(self, item):
        self.items.append(item)

    def recv(self):
        pass
