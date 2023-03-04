"""
Transparently load variables from environment or JSON/YAML file.
"""
import errno
import json
import logging
import os
import sys
from io import StringIO
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, cast

from pydantic import BaseModel, BaseSettings, PrivateAttr
from pydantic.env_settings import SettingsSourceCallable
from pydantic.fields import ModelField, Undefined

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
    initial = ""  # Default value
    try:
        if not callable(info.extra["initial"]):
            raise ValueError(f"Initial value for `{name}` must be a callable.")
        initial = info.extra["initial"]()
    except KeyError:
        if info.default is not Undefined and info.default is not ...:
            initial = info.default
        if info.default_factory is not None:
            initial = info.default_factory()

    # If initial is a BaseModel generate the dictionary representation using pydantic
    #  built-in method
    if isinstance(initial, BaseModel):
        return initial.dict()
    # If initial is a list, concatenate the result in an output list
    elif isinstance(initial, list):
        # If it contains a list of BaseModel, invoke dict on each of them
        if any(isinstance(element, BaseModel) for element in initial):
            return [element.dict() for element in initial]
        else:
            # If they are basic types, simply concatenate them
            return [inner for inner in initial]
    if field.allow_none:
        return None
    return initial


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
    def get_initial(cls, **override) -> dict[str, Any]:
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

        def create_item(field: ModelField, initial_value: Any) -> Item:
            """Recursively traverse the input field,
            building the appropriate TOML Item while descending the hierarchy.
            Stop when find a basic type is encountered, created as a basic TOML Item"""
            # Check to see if the initial_value is a complex type
            if isinstance(initial_value, dict):
                # If this field contains sub-fields inside,
                # create them inside a TOML table
                table = tomlkit.table()
                # Invoke recursively on each subfield
                for name, field in field.type_.__fields__.items():
                    item = create_item(field, initial_value[name])
                    # Add the item to the table
                    table[name] = item
                return table
            # Che if the initial_value is a list of object
            elif isinstance(initial_value, list):
                # Check to see if the list of sub-fields contains any complex type.
                # In that case, an array of table (aot) is required
                if getattr(field, "sub_fields") and any(
                    sub_field.is_complex() for sub_field in field.sub_fields
                ):
                    array = tomlkit.aot()
                else:
                    # The sub-fields are basic types
                    array = tomlkit.array()

                for index, _ in enumerate(initial_value):
                    # Invoke recursively on each element
                    if getattr(field, "sub_fields"):
                        # We have a complex type in the sub_fields
                        item = create_item(field.sub_fields[0], initial_value[index])
                    else:
                        # We have a simple type
                        item = create_item(field, initial_value[index])
                    # Append each item to the array
                    array.append(item)

                return array
            # Base of the recursion: the initial_value is a simple type
            else:
                # Create a base TOML item
                item = tomlkit.item(initial_value)

                # Add description to the item, if present
                if field.field_info.description:
                    description = cast(str, field.field_info.description)
                    item.comment(description)

                return item

        for k, initial_value in dict_from_toml.unwrap().items():
            item = create_item(cls.__fields__[k], initial_value)
            document.add(k, item)

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
                lines[-1] = lines[-1] + "_REQUIRED_  "
            if v.field_info.description:
                lines.append(f"  {v.field_info.description}  ")
            type_ = v.type_ == v.type_.__name__ if v.outer_type_ else v.outer_type_
            lines.append(f"  type: `{type_}`  ")
            if v.default is not None:
                lines.append(f"  default: `{v.default}`  ")
        return "\n".join(lines)

    def django_manage(self, args: Optional[List[str]] = None):
        args = args or sys.argv
        from .contrib.django import execute_from_command_line_with_config

        execute_from_command_line_with_config(self, args)
