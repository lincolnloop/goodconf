"""
Transparently load variables from environment or JSON/YAML file.
"""
import json
import logging
import os

from decimal import Decimal
from distutils.util import strtobool
from io import StringIO
from typing import TypeVar, List, Callable

log = logging.getLogger(__name__)

CASTS = [int, str, float, list, bool, Decimal]
CastTypes = TypeVar('CastTypes', *CASTS)


class RequiredValueMissing(Exception):
    pass


def _load_config(path: str) -> dict:
    """
    Given a file path, parse it based on its extension (YAML or JSON)
    and return the values as a Python dictionary. JSON is the default if an
    extension can't be determined.
    """
    __, ext = os.path.splitext(path)
    if ext in ['.yaml', '.yml']:
        import ruamel.yaml
        loader = ruamel.yaml.safe_load
    else:
        loader = json.load
    with open(path) as f:
        config = loader(f)
    log.info("Loaded config from %s", path)
    return config


def _find_file(file: str, verify_later: bool = False) -> str:
    if os.path.isabs(file):
        config_file = file
    else:
        config_file = os.path.join(os.getcwd(), file)
    if not verify_later and not os.path.exists(config_file):
        return None
    return config_file


class Value:
    def __init__(self, key: str, default=None, required: bool = None,
                 initial: Callable[[], CastTypes] = None,
                 cast_as: CastTypes = None, help: str = ""):
        """

        :param key:      Name of the value used in file or environment variable
        :param default:  Default value if none is provided.
        :param required: Loading a config will fail if a value is not provided.
                         Defaults to True if no default is provided otherwise
                         False.
        :param initial:  Initial value to use when generating a config
        :param cast_as:  Python type to cast variable as. Defaults to type of
                         default (if provided) or str.
        :param help:     Plain-text description of the value.
        """
        self.key = key
        self.default = default
        if default is not None:
            self.value = default
        self.required = bool(default is None or required)
        if initial and not callable(initial):
            raise ValueError("Initial value must be a callable.")
        self._initial = initial
        self.help = help
        if cast_as:
            self.cast_as = cast_as
        elif default is not None:
            self.cast_as = type(default)
        else:
            self.cast_as = str

    @property
    def initial(self):
        if callable(self._initial):
            return self._initial()
        elif self.default is not None:
            return self.default
        return ''

    def set_value(self, defined: CastTypes = None):
        if self.key in os.environ:
            self.value = self.cast(os.environ[self.key])
        elif defined is not None:
            assert(type(defined) == self.cast_as)
            self.value = defined
        elif self.required:
            raise RequiredValueMissing(self.key)

    def cast(self, val: str):
        """converts string to type requested by `cast_as`"""
        try:
            return getattr(self, 'cast_as_{}'.format(
                self.cast_as.__name__.lower()))(val)
        except AttributeError:
            return self.cast_as(val)

    def cast_as_list(self, val: str) -> list:
        """Convert a comma-separated string to a list"""
        return val.split(',')

    def cast_as_bool(self, val: str) -> bool:
        """
        True values are y, yes, t, true, on and 1
        False values are n, no, f, false, off and 0
        Raises ValueError if val is anything else.
        """
        return bool(strtobool(val))


class GoodConf:
    def __init__(self, description: str = '',
                 file_env_var: str = None,
                 default_files: List[str] = None):
        """

        :param description: a plain-text description used as a header when
                            generating the file
        :param file_env_var: the name of an environment variable which can be
                             used for the name of the configuration file to
                             load
        :param default_files: if no file is given, try to load a configuration
                              from these files in order
        """
        self.description = description
        self.file_env_var = file_env_var
        self.config_file = None
        self.default_files = default_files
        self._values = {}

    def __getattr__(self, key: str):
        return self._values[key].value

    def load(self, file: str = None):
        """Find config file and set values"""
        self.config_file = self.determine_file(file)
        if self.config_file:
            config = _load_config(self.config_file)
        else:
            config = {}
        self.set_values(config)

    def determine_file(self, file: str = None):
        """
        Return absolute path to the config file or None if it does not exist.
        Relative paths will be resolved relative to the working directory
        Will return the first file of:
        1. os.environ[self.config_file_env_var] (if defined)
        2. config file passed as arg
        3. first default file found
        """
        if self.file_env_var and self.file_env_var in os.environ:
            return _find_file(os.environ[self.file_env_var],
                              verify_later=True)
        if file:
            return _find_file(file, verify_later=True)
        if self.default_files:
            for f in self.default_files:
                default_file = _find_file(f)
                if default_file:
                    return default_file

    def define_values(self, *args: Value):
        """Sets up internal dict used to track values"""
        for val in args:
            self._values[val.key] = val

    def set_values(self, config: dict):
        for k, v in self._values.items():
            v.set_value(config.get(k))

    def get_initial(self):
        return {k: v.initial for k, v in self._values.items()}

    def generate_yaml(self):
        """
        Dumps initial config in YAML
        """
        import ruamel.yaml
        yaml = ruamel.yaml.YAML()
        yaml_str = StringIO()
        yaml.dump(self.get_initial(), stream=yaml_str)
        yaml_str.seek(0)
        dict_from_yaml = yaml.load(yaml_str)
        if self.description:
            dict_from_yaml.yaml_set_start_comment(
                '\n' + self.description + '\n\n')
        for k in dict_from_yaml.keys():
            if self._values[k].help:
                dict_from_yaml.yaml_set_comment_before_after_key(
                    k, before='\n' + self._values[k].help)
        yaml_str = StringIO()
        yaml.dump(dict_from_yaml, yaml_str)
        yaml_str.seek(0)
        return yaml_str.read()

    def generate_json(self):
        """
        Dumps initial config in JSON
        """
        return json.dumps(self.get_initial(), indent=2)

    def generate_markdown(self):
        """
        Documents values in markdown
        """
        lines = []
        if self.description:
            lines.extend(['# {}'.format(self.description), ''])
        for k, v in self._values.items():
            lines.append('* **{}**  '.format(k))
            if v.required:
                lines[-1] = lines[-1] + '_REQUIRED_  '
            if v.help:
                lines.append('  {}  '.format(v.help))
            lines.append('  type: `{}`  '.format(v.cast_as.__name__))
            if v.default:
                lines.append('  default: `{}`  '.format(v.default))
        return '\n'.join(lines)
