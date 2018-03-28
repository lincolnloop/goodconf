import functools
import os
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest import mock, TestCase, SkipTest

from goodconf import (Value, GoodConf, RequiredValueMissing,
                      _load_config, _find_file)
from goodconf.contrib.django import execute_from_command_line_with_config

KEY = 'GOODCONF_TEST'


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    yield
    del(os.environ[key])


class ValueTests(TestCase):
    def test_default_not_required(self):
        """Values with a default are not required"""
        v = Value(KEY, default='s')
        self.assertFalse(v.required)

    def test_no_default_required(self):
        """Values with a default are not required"""
        v = Value(KEY)
        self.assertTrue(v.required, True)

    def test_infer_cast(self):
        """If not provided, cast is type of default"""
        v = Value(KEY, default=5)
        self.assertEqual(v.cast_as, int)

    def test_default_cast(self):
        """Default cast is str"""
        v = Value(KEY)
        self.assertEqual(v.cast_as, str)

    def test_explicit_cast(self):
        v = Value(KEY, cast_as=bool)
        self.assertEqual(v.cast_as, bool)

    def test_cast_bool(self):
        v = Value(KEY, cast_as=bool)
        with env_var(KEY, 'true'):
            v.set_value()
            self.assertTrue(v.value)
        with env_var(KEY, 'false'):
            v.set_value()
            self.assertFalse(v.value)

    def test_initial(self):
        v = Value(KEY, initial=lambda: 'x')
        self.assertEqual(v.initial, 'x')

    def test_initial_bad(self):
        self.assertRaises(ValueError, Value, KEY, initial='x')

    def test_intial_default(self):
        v = Value(KEY, default='x')
        self.assertEqual(v.initial, 'x')

    def test_no_initial(self):
        v = Value(KEY)
        self.assertEqual(v.initial, '')

    def test_defined_value(self):
        v = Value(KEY)
        v.set_value('x')
        self.assertEqual(v.value, 'x')

    def test_env_var_precedence(self):
        v = Value(KEY)
        with env_var(KEY, 'y'):
            v.set_value('x')
        self.assertEqual(v.value, 'y')

    def test_required_no_value(self):
        v = Value(KEY)
        self.assertRaises(RequiredValueMissing, v.set_value)

    def test_cast_list(self):
        v = Value(KEY, cast_as=list)
        with env_var(KEY, 'a,b,c'):
            v.set_value()
        self.assertListEqual(v.value, ['a', 'b', 'c'])


def skip_if_no_yaml(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            import ruamel.yaml
            return f(*args, **kwargs)
        except ImportError:
            raise SkipTest("[yaml] extras is not installed")
    return wrapper


class TestFileHelpers(TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_json(self):
        conf = os.path.join(self.tmpdir.name, 'conf.json')
        with open(conf, 'w') as f:
            f.write('{"a": "b", "c": 3}')
        self.assertEqual({'a': 'b', 'c': 3}, _load_config(conf))

    @skip_if_no_yaml
    def test_yaml(self):
        conf = os.path.join(self.tmpdir.name, 'conf.yml')
        with open(conf, 'w') as f:
            f.write('a: b\nc: 3')
        self.assertEqual({'a': 'b', 'c': 3}, _load_config(conf))

    def test_cwd(self):
        cwd = os.getcwd()
        file = 'test.yml'
        self.assertEqual(os.path.join(cwd, file),
                         _find_file(file, verify_later=True))

    def test_abspath(self):
        path = '/etc/config.yml'
        self.assertEqual(path,
                         _find_file(path, verify_later=True))

    def test_verify(self):
        path = os.path.join(self.tmpdir.name, 'does-not-exist.yml')
        self.assertIsNone(_find_file(path))


class TestGoodConf(TestCase):
    def test_set_values(self):
        c = GoodConf()
        c.define_values(Value('a'), Value('c', default=4))
        c.set_values({'a': 'b'})
        self.assertEqual(c.a, 'b')
        self.assertEqual(c.c, 4)

    def test_initial(self):
        c = GoodConf()
        c.define_values(Value('a', initial=lambda: True))
        self.assertEqual(c.get_initial(), {'a': True})

    def test_dump_json(self):
        c = GoodConf()
        c.define_values(Value('a', initial=lambda: True))
        self.assertEqual(c.generate_json(), '{\n  "a": true\n}')

    def test_dump_yaml(self):
        c = GoodConf(description="Configuration for My App")
        c.define_values(Value('a', help="this is a"))
        self.assertEqual(c.generate_yaml(), dedent("""
            # 
            # Configuration for My App
            # 
            
            # this is a
            a: ''
            """).lstrip())

    def test_generate_markdown(self):
        description = "Configuration for My App"
        help_ = "this is a"
        c = GoodConf(description=description)
        c.define_values(Value('a', help=help_, default=5),
                        Value('b', required=True))
        mkdn = c.generate_markdown()
        # Not sure on final format, just do some basic smoke tests
        self.assertIn(description, mkdn)
        self.assertIn(help_, mkdn)


class TestGoodConfFiles(TestCase):
    def setUp(self):
        self.tmpdir = TemporaryDirectory()

    def tearDown(self):
        self.tmpdir.cleanup()

    @mock.patch('goodconf._load_config')
    def test_conf_env_var(self, mocked_load_config):
        path = Path(self.tmpdir.name) / 'myapp.json'
        path.touch()
        path = str(path)
        c = GoodConf(file_env_var='CONF')
        with env_var('CONF', path):
            c.load()
        mocked_load_config.assert_called_once_with(path)

    @mock.patch('goodconf.GoodConf.set_values')
    def test_all_env_vars(self, mocked_set_values):
        c = GoodConf()
        c.load()
        mocked_set_values.assert_called_once_with({})

    @mock.patch('goodconf._load_config')
    def test_provided_file(self, mocked_load_config):
        path = Path(self.tmpdir.name) / 'myapp.json'
        path.touch()
        path = str(path)
        c = GoodConf()
        c.load(path)
        mocked_load_config.assert_called_once_with(path)

    @mock.patch('goodconf._load_config')
    def test_default_files(self, mocked_load_config):
        path = Path(self.tmpdir.name) / 'myapp.json'
        path.touch()
        path = str(path)
        bad_path = str(Path(self.tmpdir.name) / 'does-not-exist.json')
        c = GoodConf(default_files=[bad_path, path])
        c.load()
        mocked_load_config.assert_called_once_with(path)


def skip_if_no_django(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            import django
            return f(*args, **kwargs)
        except ImportError:
            raise SkipTest("Django is not installed")
    return wrapper



class TestDjango(TestCase):

    @skip_if_no_django
    @mock.patch('django.core.management.execute_from_command_line')
    @mock.patch('goodconf._load_config')
    def test_mgmt_command(self, mocked_load_config, mocked_dj_execute):
        c = GoodConf()
        path = '/etc/config.yml'
        dj_args = ['manage.py', 'diffsettings', '-v', '2']
        execute_from_command_line_with_config(c, dj_args + ['-c', path])
        mocked_load_config.assert_called_once_with('/etc/config.yml')
        mocked_dj_execute.assert_called_once_with(dj_args)

    @skip_if_no_django
    @mock.patch('goodconf._load_config')
    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('sys.exit')
    def test_help(self, mocked_sysexit, mocked_stdout, mocked_load_config):
        path = '/etc/config.yml'
        c = GoodConf(file_env_var='MYAPP_CONF',
                     default_files=['/etc/myapp.json'])
        execute_from_command_line_with_config(c, [
            'manage.py', 'diffsettings', '-c', path,
            '--settings', 'tests.test_goodconf', '-h'])
        mocked_load_config.assert_called_once_with('/etc/config.yml')
        output = mocked_stdout.getvalue()
        self.assertIn('-c FILE, --config FILE', output)
        self.assertIn('MYAPP_CONF', output)
        self.assertIn('/etc/myapp.json', output)


# This doubles as a Django settings file for the tests
SECRET_KEY = 'abc'
