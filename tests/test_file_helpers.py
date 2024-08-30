import os
import sys
import pytest

from goodconf import _find_file, _load_config


def test_json(tmpdir):
    conf = tmpdir.join("conf.json")
    conf.write('{"a": "b", "c": 3}')
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_toml(tmpdir):
    if sys.version_info < (3, 11):
        pytest.importorskip("tomlkit")
    conf = tmpdir.join("conf.toml")
    conf.write('a = "b"\nc = 3')
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_empty_toml(tmpdir):
    if sys.version_info < (3, 11):
        pytest.importorskip("tomlkit")
    conf = tmpdir.join("conf.toml")
    conf.write("")
    assert _load_config(str(conf)) == {}


def test_yaml(tmpdir):
    pytest.importorskip("ruamel.yaml")
    conf = tmpdir.join("conf.yaml")
    conf.write("a: b\nc: 3")
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_empty_yaml(tmpdir):
    pytest.importorskip("ruamel.yaml")
    conf = tmpdir.join("conf.yaml")
    conf.write("")
    assert _load_config(str(conf)) == {}


def test_missing(tmpdir):
    conf = tmpdir.join("test.yml")
    assert _find_file(str(conf), require=False) is None


def test_missing_strict(tmpdir):
    conf = tmpdir.join("test.yml")
    with pytest.raises(FileNotFoundError):
        _find_file(str(conf))


def test_abspath(tmpdir):
    conf = tmpdir.join("test.yml")
    conf.write("")
    path = _find_file(str(conf))
    assert path == str(conf)


def test_relative(tmpdir):
    conf = tmpdir.join("test.yml")
    conf.write("")
    os.chdir(conf.dirname)
    assert _find_file("test.yml") == str(conf)
