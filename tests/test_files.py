import json
from pathlib import Path

from pytest_mock import MockerFixture

from goodconf import GoodConf

from .utils import env_var


def test_conf_env_var(mocker: MockerFixture, tmp_path: Path) -> None:
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmp_path / "myapp.json"
    path.write_text("")

    class G(GoodConf):
        model_config = {"file_env_var": "CONF"}

    with env_var("CONF", str(path)):
        g = G()
        g.load()
    mocked_load_config.assert_called_once_with(str(path))


def test_conflict(tmp_path: Path) -> None:
    path = tmp_path / "myapp.json"
    path.write_text(json.dumps({"A": 1, "B": 2}))

    class G(GoodConf):
        A: int
        B: int

        model_config = {"default_files": [str(path)]}

    with env_var("A", "3"):
        g = G()
        g.load()
    assert g.A == 3
    assert g.B == 2


def test_all_env_vars(mocker: MockerFixture) -> None:
    mocked_set_values = mocker.patch("goodconf.BaseSettings.__init__")
    mocked_load_config = mocker.patch("goodconf._load_config")

    class G(GoodConf):
        pass

    g = G()
    g.load()
    mocked_set_values.assert_called_once_with()
    mocked_load_config.assert_not_called()


def test_provided_file(mocker: MockerFixture, tmp_path: Path) -> None:
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmp_path / "myapp.json"
    path.write_text("")

    class G(GoodConf):
        pass

    g = G()
    g.load(str(path))
    mocked_load_config.assert_called_once_with(str(path))


def test_provided_file_from_init(mocker: MockerFixture, tmp_path: Path) -> None:
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmp_path / "myapp.json"
    path.write_text("")

    class G(GoodConf):
        pass

    g = G(config_file=str(path))
    g.load()
    mocked_load_config.assert_called_once_with(str(path))


def test_default_files(mocker: MockerFixture, tmp_path: Path) -> None:
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmp_path / "myapp.json"
    path.write_text("")
    bad_path = tmp_path / "does-not-exist.json"

    class G(GoodConf):
        model_config = {"default_files": [str(bad_path), str(path)]}

    g = G()
    g.load()
    mocked_load_config.assert_called_once_with(str(path))
