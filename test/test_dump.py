from pathlib import Path
from unittest import TestCase
import json
import safer
import tdir
import toml
import yaml

TESTS = None, 3, 'a', {}, [], {'a': 1}, [1, 2, 3], {'a': [1, 2]}
DUMPS = safer.dump, safer.dumper('json'), safer.dumper('json.dump')


@tdir
class TestDump(TestCase):
    def test_dump(self):
        _test()

    def test_yaml(self):
        dumps = yaml, yaml.dump, 'yaml', 'yaml.dump'
        dumps = (safer.dumper(i) for i in dumps)

        _test(yaml.safe_load, dumps)

    def test_toml(self):
        dumps = toml, toml.dump, 'toml', 'toml.dump'
        dumps = (safer.dumper(i) for i in dumps)
        tests = ({}, {'a': 1}, {'a': [1, 2]})

        _test(toml.load, dumps, tests)

    def test_error(self):
        one = Path('one')
        data = {10000 * 'a': [self]}

        assert not one.exists()
        with self.assertRaises(TypeError):
            safer.dump(data, one)

        assert not one.exists()
        with self.assertRaises(TypeError):
            json.dump(data, one.open('w'))

        assert one.exists()

    def test_error2(self):
        with self.assertRaises(ModuleNotFoundError) as m:
            safer.dumper('yoghurt')
        assert m.exception.args[0] == "No module named 'yoghurt'"

        with self.assertRaises(ModuleNotFoundError) as m:
            safer.dumper('yoghurt.frogs')
        assert m.exception.args[0] == "No module named 'yoghurt'"


def _test(load=json.load, dumps=DUMPS, tests=TESTS):
    for dump in dumps:
        for data in tests:
            dump(data, 'one')

            with open('one') as fp:
                assert load(fp) == data
