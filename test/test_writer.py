from . import helpers
import safer


@helpers.temps(safer.writer)
class TestWriter(helpers.TestCase):
    def test_callable(self, safer_writer):
        results = []
        with safer_writer(results.append) as fp:
            fp.write('abc')
            fp.write('d')
        assert results == ['abcd']

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

    def test_callable2(self, safer_writer):
        results = []
        with safer_writer(results.append) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_callable_closer(self, safer_writer):
        results = []
        with safer_writer(results.append, close_on_exit=True) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_callable_closer2(self, safer_writer):
        class CB:
            def __call__(self, item):
                results.append(item)

            def close(self, failed=-5):
                results.append(('close', failed))

        results = []
        with safer_writer(CB(), close_on_exit=True) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo', ('close', False)]


class socket:
    def __init__(self):
        self.items = []

    def send(self, item):
        self.items.append(item)

    def recv(self):
        pass
