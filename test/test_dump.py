import functools
import importlib
import io
import json
import pickle
from pathlib import Path
from unittest import TestCase

import pytest
import tdir
import toml
import yaml

import safer

from . import helpers


@tdir
def test_descriptor_named_stream_defaults_to_json():
    with Path('descriptor').open('wb') as owned:
        with open(owned.fileno(), 'wb', closefd=False) as destination:
            safer.dump({'value': 1}, destination)
    assert json.loads(Path('descriptor').read_bytes()) == {'value': 1}


def test_binary_serializer_rejection_leaves_destination_unchanged():
    destination = io.BytesIO(b'original')
    with pytest.raises(TypeError, match='text serializers only'):
        safer.dump({'value': 1}, destination, dump=pickle.dump)
    assert destination.getvalue() == b'original'


@pytest.mark.parametrize(
    'error',
    [
        ImportError('internal failure'),
        ModuleNotFoundError('missing dependency', name='dependency'),
    ],
)
def test_serializer_import_keeps_internal_failure(monkeypatch, error):
    def broken(name):
        raise error

    monkeypatch.setattr(importlib, 'import_module', broken)
    with pytest.raises(type(error)) as raised:
        safer.dump(None, io.StringIO(), dump='serializer.dump')
    assert raised.value is error


@tdir
def test_dump_path_and_binary_destination_use_requested_encoding():
    value = {'letter': 'é'}
    destination = io.BytesIO()
    safer.dump(value, destination, encoding='latin-1', ensure_ascii=False)
    safer.dump(value, Path('encoded.json'), encoding='latin-1', ensure_ascii=False)
    assert Path('encoded.json').read_bytes() == destination.getvalue()


def test_existing_text_stream_keeps_its_own_encoding():
    raw = io.BytesIO()
    destination = io.TextIOWrapper(raw, encoding='latin-1')
    safer.dump('é', destination, encoding='ascii', ensure_ascii=False)
    destination.flush()
    assert raw.getvalue() == b'"\xe9"'


@pytest.mark.parametrize('encoding', ['utf-16', 'utf-8-sig', 'iso2022_jp'])
def test_fragmented_serializer_uses_one_encoder(encoding):
    destination = io.BytesIO()

    def fragments(obj, fp):
        assert fp.write('日') == 1
        assert fp.write('本') == 1
        return 'result'

    assert safer.dump(None, destination, dump=fragments, encoding=encoding) == 'result'
    assert destination.getvalue() == '日本'.encode(encoding)


def dumper(dump):
    return functools.partial(safer.dump, dump=dump)


TESTS = None, 3, 'a', {}, [], {'a': 1}, [1, 2, 3], {'a': [1, 2]}
DUMPS = safer.dump, dumper('json'), dumper('json.dump')


@tdir
class TestDump(TestCase):
    def test_in_memory_binary_destination(self):
        destination = io.BytesIO()
        safer.dump({'letter': 'é'}, destination, ensure_ascii=False)
        assert json.loads(destination.getvalue()) == {'letter': 'é'}

    def test_dump(self):
        _test()

    def test_yaml(self):
        dumps = yaml, yaml.dump, 'yaml', 'yaml.dump'
        dumps = (dumper(i) for i in dumps)

        _test(yaml.safe_load, dumps)

    def test_toml(self):
        dumps = toml, toml.dump, 'toml', 'toml.dump'
        dumps = (dumper(i) for i in dumps)
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
            safer.dump({}, dump='yoghurt')
        assert m.exception.args[0] == "No module named 'yoghurt'"

        with self.assertRaises(ModuleNotFoundError) as m:
            safer.dump({}, dump='yoghurt.frogs')
        assert m.exception.args[0] == "No module named 'yoghurt'"

    def test_socket(self):
        sock = helpers.socket()
        safer.dump({'hello': 'world!'}, sock)
        assert b''.join(sock.items) == b'{"hello": "world!"}'

    def test_binary(self):
        data = {'hello': 'world! 🧿'}
        with open('one.yml', 'wb') as fp:
            safer.dump(data, fp)
        with open('one.yml') as fp:
            actual = yaml.safe_load(fp)
        assert data == actual

    def test_binary_encoding(self):
        sock = helpers.socket()
        safer.dump({'letter': 'é'}, sock, encoding='latin-1', ensure_ascii=False)
        assert b''.join(sock.items) == b'{"letter": "\xe9"}'


def _test(load=json.load, dumps=DUMPS, tests=TESTS):
    for dump in dumps:
        for data in tests:
            dump(data, 'one')

            with open('one') as fp:
                assert load(fp) == data
