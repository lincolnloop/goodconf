"""
Transparently load variables from environment or JSON/YAML file.
"""
import errno
import json
import logging
import os
import sys
from io import StringIO
from typing import Any, List, Tuple

from pydantic import BaseSettings, FilePath
from pydantic.env_settings import SettingsSourceCallable
from pydantic.fields import Field, FieldInfo, ModelField, Undefined  # noqa

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
    return config or {}


def _find_file(filename: str, require: bool = True) -> str:
    if not os.path.exists(filename):
        if not require:
            return None
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
    return os.path.abspath(filename)


def initial_for_field(name: str, field: ModelField) -> Any:
    info = field.field_info
    try:
        if not callable(info.extra["initial"]):
            raise ValueError(f"Initial value for `{name}` must be a callable.")
        return info.extra["initial"]()
    except KeyError:
        if info.default is not Undefined and info.default is not ...:
            return info.default
        if info.default_factory is not None:
            return info.default_factory()
    if field.allow_none:
        return None
    return ""


class GoodConf(BaseSettings):
    def __init__(self, load: bool = False):
        """
        :param load: load config file on instantiation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        if load:
            self.load()

    class Config:
        # the name of an environment variable which can be used for the name of the
        # configuration file to load
        file_env_var: str = None
        # if no file is given, try to load a configuration from these files in order
        default_files: List[str] = None
        # actual file used for configuration on load
        _config_file: FilePath = None
        load: bool = False

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            """Load environment variables before init"""
            return env_settings, init_settings, file_secret_settings

    def load(self, filename: str = None) -> None:
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
            self.Config._config_file = selected_config_file
        else:
            config = {}
            log.info("No config file specified. Loading with environment variables.")
        super().__init__(**config)

    @classmethod
    def get_initial(cls, **override) -> dict:
        return {
            k: override.get(k, initial_for_field(k, v))
            for k, v in cls.__fields__.items()
        }

    @classmethod
    def generate_yaml(cls, **override) -> str:
        """
        Dumps initial config in YAML
        """
        import ruamel.yaml

        yaml = ruamel.yaml.YAML()
        yaml.representer.add_representer(
            type(None),
            lambda self, d: self.represent_scalar("tag:yaml.org,2002:null", "~"),
        )
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
    def generate_json(cls, **override) -> str:
        """
        Dumps initial config in JSON
        """
        return json.dumps(cls.get_initial(**override), indent=2)

    @classmethod
    def generate_markdown(cls) -> str:
        """
        Documents values in markdown
        """
        lines = []
        if cls.__doc__:
            lines.extend([f"# {cls.__doc__}", ""])
        for k, v in cls.__fields__.items():
            lines.append(f"* **{k}**  ")
            if v.required:
                lines[-1] = lines[-1] + "_REQUIRED_  "
            if v.field_info.description:
                lines.append(f"  {v.field_info.description}  ")
            type_ = v.type_ == v.type_.__name__ if v.outer_type_ else v.outer_type_
            lines.append(f"  type: `{type_}`  ")
            if v.default is not None:
                lines.append(f"  default: `{v.default}`  ")
        return "\n".join(lines)

    def django_manage(self, args: List[str] = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config

        execute_from_command_line_with_config(self, args)
