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

import pydantic

from goodconf.values import Value, _default_for_initial  # noqa

log = logging.getLogger(__name__)


def _load_config(path: str) -> dict:
    """
    Given a file path, parse it based on its extension (YAML or JSON)
    and return the values as a Python dictionary. JSON is the default if an
    extension can't be determined.
    """
    __, ext = os.path.splitext(path)
    if ext in [".yaml", ".yml"]:
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
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
    return os.path.abspath(filename)


class GoodConf(pydantic.BaseSettings):
    def __init__(self, load: bool = False):
        """
        :param file_env_var: the name of an environment variable which can be
                             used for the name of the configuration file to
                             load
        :param load: load config file on instantiation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        if load:
            self.load()

    class Config:
        file_env_var: str = None
        # if no file is given, try to load a configuration from these files in order
        default_files: List[str] = None
        load: bool = False


    def load(self, filename: str = None):
        """Find config file and set values"""
        selected_config_file = None
        if filename:
            selected_config_file = _find_file(filename)
        else:
            if (
                self.__config__.file_env_var
                and self.__config__.file_env_var in os.environ
            ):
                selected_config_file = _find_file(
                    os.environ[self.__config__.file_env_var]
                )
            else:
                for filename in self.__config__.default_files or []:
                    selected_config_file = _find_file(filename, require=False)
                    if selected_config_file:
                        break
        if selected_config_file:
            config = _load_config(selected_config_file)
            log.info("Loading config from %s", selected_config_file)
        else:
            config = {}
            log.info("No config file specified. " "Loading with environment variables.")
        super().__init__(**config)

    @classmethod
    def get_initial(cls, **override):
        initial = {}
        for k, v in cls.__fields__.items():
            # values defined with a simple type annotation won't have an `initial`
            try:
                i = v.field_info.initial
            except AttributeError:
                i = _default_for_initial(v.field_info)

            initial[k] = override.get(k, i)
        return initial

    @classmethod
    def generate_yaml(cls, **override):
        """
        Dumps initial config in YAML
        """
        import ruamel.yaml

        yaml = ruamel.yaml.YAML()
        yaml_str = StringIO()
        yaml.dump(cls.get_initial(**override), stream=yaml_str)
        yaml_str.seek(0)
        dict_from_yaml = yaml.load(yaml_str)
        if cls.__doc__:
            dict_from_yaml.yaml_set_start_comment("\n" + cls.__doc__ + "\n\n")
        for k in dict_from_yaml.keys():
            if cls.__fields__[k].field_info.description:
                dict_from_yaml.yaml_set_comment_before_after_key(
                    k, before="\n" + cls.__fields__[k].field_info.description
                )
        yaml_str = StringIO()
        yaml.dump(dict_from_yaml, yaml_str)
        yaml_str.seek(0)
        return yaml_str.read()

    @classmethod
    def generate_json(cls, **override):
        """
        Dumps initial config in JSON
        """
        return json.dumps(cls.get_initial(**override), indent=2)

    @classmethod
    def generate_markdown(cls):
        """
        Documents values in markdown
        """
        lines = []
        if cls.__doc__:
            lines.extend(["# {}".format(cls.__doc__), ""])
        for k, v in cls.__fields__.items():
            lines.append("* **{}**  ".format(k))
            if v.required:
                lines[-1] = lines[-1] + "_REQUIRED_  "
            if v.field_info.description:
                lines.append("  {}  ".format(v.field_info.description))
            lines.append("  type: `{}`  ".format(v.type_.__name__))
            if v.default is not None:
                lines.append("  default: `{}`  ".format(v.default))
        return "\n".join(lines)

    def django_manage(self, args: List[str] = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config

        execute_from_command_line_with_config(self, args)
