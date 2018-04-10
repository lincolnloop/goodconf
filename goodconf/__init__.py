"""
Transparently load variables from environment or JSON/YAML file.
"""
import json
import logging
import os
import sys
import errno
from io import StringIO
from typing import List

from goodconf.base import DeclarativeValuesMetaclass

log = logging.getLogger(__name__)


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
    return config


def _find_file(filename: str, require: bool = True) -> str:
    if not os.path.exists(filename):
        if not require:
            return None
        raise FileNotFoundError(
            errno.ENOENT, os.strerror(errno.ENOENT), filename)
    return os.path.abspath(filename)


class GoodConf(metaclass=DeclarativeValuesMetaclass):
    def __init__(self,
                 file_env_var: str = None,
                 default_files: List[str] = None,
                 load: bool = False):
        """
        :param file_env_var: the name of an environment variable which can be
                             used for the name of the configuration file to
                             load
        :param default_files: if no file is given, try to load a configuration
                              from these files in order
        :param load: load config file on instanciation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        self.file_env_var = file_env_var
        self.config_file = None
        self.default_files = default_files or []
        if load:
            self.load()

    def load(self, filename: str = None):
        """Find config file and set values"""
        if filename:
            self.config_file = _find_file(filename)
        else:
            if self.file_env_var and self.file_env_var in os.environ:
                self.config_file = _find_file(os.environ[self.file_env_var])
            if not self.config_file:
                for filename in self.default_files:
                    self.config_file = _find_file(filename, require=False)
                    if self.config_file:
                        break
        if self.config_file:
            config = _load_config(self.config_file)
            log.info("Loading config from %s", self.config_file)
        else:
            config = {}
            log.info("No config file specified. "
                     "Loading with environment variables.")
        self.set_values(config)

    def set_values(self, config: dict):
        for k in self._values:
            if k in config:
                setattr(self, k, config.get(k))
            else:
                setattr(self, k, self._values[k].value)

    @classmethod
    def get_initial(cls):
        return {k: getattr(cls, k) for k in cls._values}

    @classmethod
    def generate_yaml(cls):
        """
        Dumps initial config in YAML
        """
        import ruamel.yaml
        yaml = ruamel.yaml.YAML()
        yaml_str = StringIO()
        yaml.dump(cls.get_initial(), stream=yaml_str)
        yaml_str.seek(0)
        dict_from_yaml = yaml.load(yaml_str)
        if cls.__doc__:
            dict_from_yaml.yaml_set_start_comment(
                '\n' + cls.__doc__ + '\n\n')
        for k in dict_from_yaml.keys():
            if cls._values[k].help:
                dict_from_yaml.yaml_set_comment_before_after_key(
                    k, before='\n' + cls._values[k].help)
        yaml_str = StringIO()
        yaml.dump(dict_from_yaml, yaml_str)
        yaml_str.seek(0)
        return yaml_str.read()

    @classmethod
    def generate_json(cls):
        """
        Dumps initial config in JSON
        """
        return json.dumps(cls.get_initial(), indent=2)

    @classmethod
    def generate_markdown(cls):
        """
        Documents values in markdown
        """
        lines = []
        if cls.__doc__:
            lines.extend(['# {}'.format(cls.__doc__), ''])
        for k, v in cls._values.items():
            lines.append('* **{}**  '.format(k))
            if v.required:
                lines[-1] = lines[-1] + '_REQUIRED_  '
            if v.help:
                lines.append('  {}  '.format(v.help))
            lines.append('  type: `{}`  '.format(v.cast_as.__name__))
            if v.default:
                lines.append('  default: `{}`  '.format(v.default))
        return '\n'.join(lines)

    def django_manage(self, args: List[str] = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config
        execute_from_command_line_with_config(self, args)
