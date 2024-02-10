"""
Transparently load variables from environment or JSON/YAML file.
"""
import errno
import json
import logging
import os
import sys
from io import StringIO
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    cast,
    get_origin,
    get_args,
    Union,
)

from pydantic import BaseSettings, PrivateAttr
from pydantic.env_settings import SettingsSourceCallable
from pydantic.fields import Field, FieldInfo, ModelField, Undefined  # noqa

log = logging.getLogger(__name__)


def _load_config(path: str) -> dict:
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


def _find_file(filename: str, require: bool = True) -> Optional[str]:
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


def file_config_settings_source(settings: BaseSettings) -> Dict[str, Any]:
    """Find config file and get values"""
    settings = cast(GoodConf, settings)
    selected_config_file = None
    if settings._config_file:
        selected_config_file = settings._config_file
    elif (
        settings.__config__.file_env_var
        and settings.__config__.file_env_var in os.environ
    ):
        selected_config_file = _find_file(os.environ[settings.__config__.file_env_var])
    else:
        for filename in settings.__config__.default_files or []:
            selected_config_file = _find_file(filename, require=False)
            if selected_config_file:
                break
    if selected_config_file:
        values = _load_config(selected_config_file)
        log.info("Loading config from %s", selected_config_file)
        settings.__config__._config_file = selected_config_file
    else:
        values = {}
        log.info("No config file specified. Loading with environment variables.")
    return values


def type_to_str(tp: Type[Any]) -> str:
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
        type_name = origin.__name__
        args_str = ", ".join(type_to_str(arg) for arg in args)
        return f"{type_name}[{args_str}]"
    return str(tp)  # Fallback for any other type


class GoodConf(BaseSettings):
    def __init__(self, load: bool = False, **kwargs):
        """
        :param load: load config file on instantiation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        self._config_file = None
        # Emulate Pydantic behavior, load immediately
        if kwargs:
            return super().__init__(**kwargs)
        elif load:
            return self.load()

    _config_file: Optional[str] = PrivateAttr()

    class Config:
        # the name of an environment variable which can be used for the name of the
        # configuration file to load
        file_env_var: Optional[str] = None
        # if no file is given, try to load a configuration from these files in order
        default_files: Optional[List[str]] = None
        # actual file used for configuration on load
        _config_file: Optional[str] = None

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> Tuple[SettingsSourceCallable, ...]:
            """Load environment variables before init"""
            return (
                init_settings,
                env_settings,
                file_config_settings_source,
                file_secret_settings,
            )

    # populated by the metaclass using the Config class defined above,
    # annotated here to help IDEs only
    __config__: ClassVar[Type[Config]]

    def load(self, filename: Optional[str] = None) -> None:
        """Find config file and set values"""
        self._config_file = filename
        super().__init__()

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
                description = cast(str, cls.__fields__[k].field_info.description)
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
            if cls.__fields__[k].field_info.description:
                description = cast(str, cls.__fields__[k].field_info.description)
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
        for k, v in cls.__fields__.items():
            lines.append(f"* **{k}**  ")
            if v.required:
                lines[-1] = lines[-1] + "_REQUIRED_"
            if v.field_info.description:
                lines.append(f"  * description: {v.field_info.description}")
            lines.append(f"  * type: `{type_to_str(v.outer_type_)}`")
            if v.default is not None:
                lines.append(f"  * default: `{v.default}`")
        return "\n".join(lines)

    def django_manage(self, args: Optional[List[str]] = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config

        execute_from_command_line_with_config(self, args)
