import json

from goodconf import GoodConf

from .utils import env_var


def test_conf_env_var(mocker, tmpdir):
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmpdir.join("myapp.json")
    path.write("")

    class G(GoodConf):
        class Config:
            file_env_var = "CONF"

    with env_var("CONF", str(path)):
        g = G()
    mocked_load_config.assert_called_once_with(str(path))
    assert g.Config._config_file == str(path)


def test_conflict(tmpdir):
    path = tmpdir.join("myapp.json")
    path.write(json.dumps({"A": 1, "B": 2}))

    class G(GoodConf):
        A: int
        B: int

        class Config:
            default_files = [path]

    with env_var("A", "3"):
        g = G()
    assert g.A == 3
    assert g.B == 2


def test_all_env_vars(mocker):
    mocked_set_values = mocker.patch("pydantic.env_settings.EnvSettingsSource.__call__")

    class G(GoodConf):
        pass

    g = G()
    mocked_set_values.assert_called_once_with(g)
    assert g.Config._config_file is None


def test_provided_file(mocker, tmpdir):
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmpdir.join("myapp.json")
    path.write("")
    g = GoodConf()
    g.from_file(str(path))
    mocked_load_config.assert_called_once_with(str(path))
    assert g.Config._config_file == str(path)


def test_default_files(mocker, tmpdir):
    mocked_load_config = mocker.patch("goodconf._load_config")
    path = tmpdir.join("myapp.json")
    path.write("")
    bad_path = tmpdir.join("does-not-exist.json")

    class G(GoodConf):
        class Config:
            default_files = [str(bad_path), str(path)]

    g = G()
    mocked_load_config.assert_called_once_with(str(path))
    assert g.Config._config_file == str(path)
