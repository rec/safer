from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import safer


class TestWriter(TestCase):
    def setUp(self):
        self.td_context = TemporaryDirectory()
        self.td = Path(self.td_context.__enter__())
        self.filename = self.td / 'test.txt'

    def tearDown(self):
        self.td_context.__exit__(None, None, None)

    def test_callable(self):
        results = []
        with safer.writer(results.append) as fp:
            fp.write('abc')
            fp.write('d')
        assert results == ['abcd']

    def test_callable_error(self):
        results = []
        with self.assertRaises(ValueError):
            with safer.writer(results.append) as fp:
                fp.write('abc')
                fp.write('d')
                raise ValueError
        assert results == []

    def test_one_file(self):
        with safer.open(self.filename, 'w') as fp1:
            fp1.write('one')
            with safer.writer(fp1) as fp2:
                fp2.write('two')
                fp2.write('three')
            fp1.write('four')
        assert self.filename.read_text() == 'onetwothreefour'

    def test_file_error(self):
        with safer.open(self.filename, 'w') as fp1:
            fp1.write('one')
            with self.assertRaises(ValueError):
                with safer.writer(fp1) as fp2:
                    fp2.write('two')
                    fp2.write('three')
                    raise ValueError
            fp1.write('four')
        assert self.filename.read_text() == 'onefour'

    def test_socket(self):
        sock = socket()
        with safer.writer(sock) as fp:
            fp.write(b'one')
            fp.write(b'two')
        assert sock.items == [b'onetwo']

    def test_socket_error(self):
        sock = socket()
        with self.assertRaises(ValueError):
            with safer.writer(sock) as fp:
                fp.write(b'one')
                fp.write(b'two')
                raise ValueError
        assert sock.items == []

    def test_callable2(self):
        results = []
        with safer.writer(results.append) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_callable_closer(self):
        results = []
        with safer.closer(results.append, close_on_exit=True) as fp:
            fp.write('one')
            fp.write('two')
            assert results == []

        assert results == ['onetwo']

    def test_callable_closer2(self):
        class CB:
            def __call__(self, item):
                results.append(item)

            def close(self, failed=-5):
                results.append(('close', failed))

        results = []
        with safer.writer(CB(), close_on_exit=True) as fp:
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
