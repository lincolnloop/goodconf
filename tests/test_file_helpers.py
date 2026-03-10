import os
import sys
from pathlib import Path

import pytest

from goodconf import _find_file, _load_config


def test_json(tmp_path: Path) -> None:
    conf = tmp_path / "conf.json"
    conf.write_text('{"a": "b", "c": 3}')
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_toml(tmp_path: Path) -> None:
    if sys.version_info < (3, 11):
        pytest.importorskip("tomlkit")
    conf = tmp_path / "conf.toml"
    conf.write_text('a = "b"\nc = 3')
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_empty_toml(tmp_path: Path) -> None:
    if sys.version_info < (3, 11):
        pytest.importorskip("tomlkit")
    conf = tmp_path / "conf.toml"
    conf.write_text("")
    assert _load_config(str(conf)) == {}


def test_yaml(tmp_path: Path) -> None:
    pytest.importorskip("ruamel.yaml")
    conf = tmp_path / "conf.yaml"
    conf.write_text("a: b\nc: 3")
    assert _load_config(str(conf)) == {"a": "b", "c": 3}


def test_load_empty_yaml(tmp_path: Path) -> None:
    pytest.importorskip("ruamel.yaml")
    conf = tmp_path / "conf.yaml"
    conf.write_text("")
    assert _load_config(str(conf)) == {}


def test_missing(tmp_path: Path) -> None:
    conf = tmp_path / "test.yml"
    assert _find_file(str(conf), require=False) is None


def test_missing_strict(tmp_path: Path) -> None:
    conf = tmp_path / "test.yml"
    with pytest.raises(FileNotFoundError):
        _find_file(str(conf))


def test_abspath(tmp_path: Path) -> None:
    conf = tmp_path / "test.yml"
    conf.write_text("")
    path = _find_file(str(conf))
    assert path == str(conf)


def test_relative(tmp_path: Path) -> None:
    conf = tmp_path / "test.yml"
    conf.write_text("")
    os.chdir(conf.parent)
    assert _find_file("test.yml") == str(conf)
