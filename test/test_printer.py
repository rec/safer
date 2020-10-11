from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import functools
import safer

topen = functools.partial(safer.open, temp_file=True)
copen = functools.partial(safer.open, mode='w')


class TestPrinter(TestCase):
    def setUp(self):
        self.td_context = TemporaryDirectory()
        self.td = Path(self.td_context.__enter__())
        self.filename = self.td / 'test.txt'

    def tearDown(self):
        self.td_context.__exit__(None, None, None)

    def test_printer(self):
        with safer.printer(self.filename) as print:
            print('hello')
        assert self.filename.read_text() == 'hello\n'

    def test_printer_dry_run(self):
        assert not self.filename.exists()
        with safer.printer(self.filename, dry_run=True) as print:
            assert not self.filename.exists()
            print('hello')
        assert not self.filename.exists()

    def test_printer_dry_run_callable(self):
        results = []

        assert not self.filename.exists()
        with safer.printer(self.filename, dry_run=results.append) as print:
            assert not self.filename.exists()
            print('hello')
        assert not self.filename.exists()
        assert results == ['hello\n']

    def test_printer_errors(self):
        with safer.printer(self.filename):
            pass
        with self.assertRaises(IOError) as m:
            with safer.printer(self.filename, 'r'):
                pass
        assert 'not open' in m.exception.args[0].lower()

        with self.assertRaises(IOError) as m:
            with safer.printer(self.filename, 'rb'):
                pass
        assert 'not open' in m.exception.args[0].lower()

        with self.assertRaises(ValueError) as m:
            with safer.printer(self.filename, 'wb'):
                pass
        assert 'binary mode' in m.exception.args[0].lower()
