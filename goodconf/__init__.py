"""
Transparently load variables from environment or JSON/YAML file.
"""
# Note: the following line is included to ensure Python3.9 compatibility.
from __future__ import annotations

import errno
import json
import logging
import os
import sys
from io import StringIO
from typing import (
    Any,
    List,
    Optional,
    Tuple,
    Type,
    cast,
    get_origin,
    get_args,
    Union,
)

from pydantic import PrivateAttr
from pydantic.fields import (  # noqa
    Field,
    FieldInfo,
    ModelPrivateAttr,
    PydanticUndefined,
)
from pydantic.main import _object_setattr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

log = logging.getLogger(__name__)


class GoodConfConfigDict(SettingsConfigDict):
    # configuration file to load
    file_env_var: str | None
    # if no file is given, try to load a configuration from these files in order
    default_files: list[str] | None


def _load_config(path: str) -> dict[str, Any]:
    """
    Given a file path, parse it based on its extension (YAML, TOML or JSON)
    and return the values as a Python dictionary. JSON is the default if an
    extension can't be determined.
    """
    __, ext = os.path.splitext(path)
    if ext in [".yaml", ".yml"]:
        import ruamel.yaml

        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        loader = yaml.load
    elif ext == ".toml":
        import tomlkit

        def load(stream):
            return tomlkit.load(f).unwrap()

        loader = load

    else:
        loader = json.load
    with open(path) as f:
        config = loader(f)
    return config or {}


def _find_file(filename: str, require: bool = True) -> str | None:
    if not os.path.exists(filename):
        if not require:
            return None
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
    return os.path.abspath(filename)


def initial_for_field(name: str, field_info: FieldInfo) -> Any:
    try:
        json_schema_extra = field_info.json_schema_extra or {}
        if not callable(json_schema_extra["initial"]):
            raise ValueError(f"Initial value for `{name}` must be a callable.")
        return field_info.json_schema_extra["initial"]()
    except KeyError:
        if (
            field_info.default is not PydanticUndefined
            and field_info.default is not ...
        ):
            return field_info.default
        if field_info.default_factory is not None:
            return field_info.default_factory()
    if type(None) in get_args(field_info.annotation):
        return None
    return ""


class FileConfigSettingsSource(PydanticBaseSettingsSource):
    """
    Source class for loading values provided during settings class initialization.
    """

    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        # Nothing to do here. Only implement the return statement to make mypy happy
        return None, "", False

    def __call__(self) -> dict[str, Any]:
        settings = cast(GoodConf, self.settings_cls)
        selected_config_file = None
        # already loaded from a file
        if not isinstance(settings._config_file, ModelPrivateAttr):
            return {}
        elif (
            settings.model_config.get("file_env_var")
            and settings.model_config["file_env_var"] in os.environ
        ):
            selected_config_file = _find_file(
                os.environ[settings.model_config["file_env_var"]]
            )
        else:
            for filename in settings.model_config.get("default_files") or []:
                selected_config_file = _find_file(filename, require=False)
                if selected_config_file:
                    break
        if selected_config_file:
            values = _load_config(selected_config_file)
            log.info("Loading config from %s", selected_config_file)
            settings._config_file = selected_config_file
        else:
            values = {}
            log.info("No config file specified. Loading with environment variables.")
            settings._config_file = None
        return values

    def __repr__(self) -> str:
        return "FileConfigSettingsSource()"


def type_to_str(tp: type[Any]) -> str:
    """String representation of a type."""
    origin = get_origin(tp)
    if origin is None:  # Simple type or a specific value in Literal
        if hasattr(tp, "__name__"):
            return tp.__name__
        return repr(
            tp
        )  # Use repr for values to get their string representation properly

    args = get_args(tp)

    if (
        origin is Union and len(args) == 2 and type(None) in args
    ):  # Handle Optional as a special case
        non_none_args = [arg for arg in args if arg is not type(None)]
        return f"Optional[{type_to_str(non_none_args[0])}]"

    if origin:  # Generic or special type like Union, Literal, etc.
        # Python 3.9 compatibility
        if hasattr(origin, "__name__"):
            type_name = origin.__name__
        else:
            # Attempt to get a readable name for special forms
            type_name = repr(origin).replace("typing.", "")

        args_str = ", ".join(type_to_str(arg) for arg in args)
        return f"{type_name}[{args_str}]"
    return str(tp)  # Fallback for any other type


class GoodConf(BaseSettings):
    _config_file: str = PrivateAttr(None)

    def __init__(self, load: bool = False, config_file: str | None = None, **kwargs):
        """
        :param load: load config file on instantiation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        # At this point __pydantic_private__ is None, so setting self.config_file
        # raises an error. To avoid this error, explicitly set
        # __pydantic_private__ to {} prior to setting self._config_file.
        _object_setattr(self, "__pydantic_private__", {})
        self._config_file = config_file

        # Emulate Pydantic behavior, load immediately
        if kwargs:
            return super().__init__(**kwargs)
        elif load:
            return self.load()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Load environment variables before init"""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            FileConfigSettingsSource(settings_cls),
            file_secret_settings,
        )

    model_config = GoodConfConfigDict()

    def load(self, filename: str | None = None) -> None:
        """Find config file and set values"""
        if filename:
            values = _load_config(filename)
            log.info("Loading config from %s", filename)
        else:
            values = {}
        super().__init__(**values)
        if filename:
            _object_setattr(self, "_config_file", filename)

    @classmethod
    def get_initial(cls, **override) -> dict:
        return {
            k: override.get(k, initial_for_field(k, v))
            for k, v in cls.model_fields.items()
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
            if cls.model_fields[k].description:
                description = cast(str, cls.model_fields[k].description)
                dict_from_yaml.yaml_set_comment_before_after_key(
                    k, before="\n" + description
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
    def generate_toml(cls, **override) -> str:
        """
        Dumps initial config in TOML
        """
        import tomlkit
        from tomlkit.items import Item

        toml_str = tomlkit.dumps(cls.get_initial(**override))
        dict_from_toml = tomlkit.loads(toml_str)
        document = tomlkit.document()
        if cls.__doc__:
            document.add(tomlkit.comment(cls.__doc__))
        for k, v in dict_from_toml.unwrap().items():
            document.add(k, v)
            if cls.model_fields[k].description:
                description = cast(str, cls.model_fields[k].description)
                cast(Item, document[k]).comment(description)
        return tomlkit.dumps(document)

    @classmethod
    def generate_markdown(cls) -> str:
        """
        Documents values in markdown
        """
        lines = []
        if cls.__doc__:
            lines.extend([f"# {cls.__doc__}", ""])

        for k, field_info in cls.model_fields.items():
            lines.append(f"* **{k}**")
            if field_info.is_required():
                lines[-1] = f"{lines[-1]} _REQUIRED_"
            if field_info.description:
                lines.append(f"  * description: {field_info.description}")
            lines.append(f"  * type: `{field_info.annotation}`")
            if field_info.default is not None:
                lines.append(f"  * default: `{field_info.default}`")
        return "\n".join(lines)

    def django_manage(self, args: list[str] | None = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config

        execute_from_command_line_with_config(self, args)
