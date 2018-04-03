from goodconf import GoodConf
from .utils import env_var


def test_conf_env_var(mocker, tmpdir):
    mocked_load_config = mocker.patch('goodconf._load_config')
    path = tmpdir.join('myapp.json')
    path.write('')
    with env_var('CONF', str(path)):
        c = GoodConf(file_env_var='CONF')
    mocked_load_config.assert_called_once_with(str(path))


def test_all_env_vars(mocker):
    mocked_set_values = mocker.patch('goodconf.GoodConf.set_values')
    c = GoodConf()
    mocked_set_values.assert_called_once_with({})


def test_provided_file(mocker, tmpdir):
    mocked_load_config = mocker.patch('goodconf._load_config')
    path = tmpdir.join('myapp.json')
    path.write('')
    GoodConf().load(str(path))
    mocked_load_config.assert_called_once_with(str(path))


def test_default_files(mocker, tmpdir):
    mocked_load_config = mocker.patch('goodconf._load_config')
    path = tmpdir.join('myapp.json')
    path.write('')
    bad_path = tmpdir.join('does-not-exist.json')
    GoodConf(default_files=[str(bad_path), str(path)])
    mocked_load_config.assert_called_once_with(str(path))
