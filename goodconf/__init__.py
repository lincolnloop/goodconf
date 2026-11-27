"""
Transparently load variables from environment or JSON/YAML file.
"""

import errno
import json
import logging
import os
import re
import sys
import tomllib
import typing as t
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from io import StringIO
from pathlib import Path
from types import GenericAlias

if t.TYPE_CHECKING:
    from pydantic.fields import _FromFieldInfoInputs

import pydantic
from pydantic import AliasChoices
from pydantic._internal._config import config_keys
from pydantic.fields import FieldInfo
from pydantic.main import _object_setattr
from pydantic_core import PydanticUndefined
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing_extensions import override

__all__ = ["Field", "GoodConf", "GoodConfConfigDict"]

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _Initial:
    """Field metadata: a callable producing the placeholder value used when
    generating a config template. Set via :func:`Field`'s ``initial=`` argument
    and stored in ``FieldInfo.metadata`` so it never leaks into JSON schema."""

    factory: Callable[[], t.Any]


def Field(  # noqa: N802
    default: t.Any = PydanticUndefined,
    *,
    initial: Callable[[], t.Any] | None = None,
    **kwargs: "t.Unpack[_FromFieldInfoInputs]",
) -> t.Any:
    # pydantic.Field's overloads reject an unpacked TypedDict; a plain dict
    # still matches them while callers keep the typed signature above.
    field_kwargs: dict[str, t.Any] = dict(kwargs)
    field_info = pydantic.Field(default, **field_kwargs)
    if initial is not None:
        # Store as field metadata rather than json_schema_extra so the callable
        # never leaks into (and breaks) JSON schema generation.
        field_info.metadata.append(_Initial(initial))
    return field_info


class GoodConfConfigDict(SettingsConfigDict):
    # configuration file to load
    file_env_var: t.NotRequired[str | None]
    # if no file is given, try to load a configuration from these files in order
    default_files: t.NotRequired[list[str] | None]


# Note: code from pydantic-settings/pydantic_settings/main.py:
# Extend `config_keys` by pydantic settings config keys to
# support setting config through class kwargs.
# Pydantic uses `config_keys` in `pydantic._internal._config.ConfigWrapper.for_model`
# to extract config keys from model kwargs, So, by adding pydantic settings keys to
# `config_keys`, they will be considered as valid config keys and will be collected
# by Pydantic.
config_keys |= set(GoodConfConfigDict.__annotations__.keys())


def _load_config(path: str) -> dict[str, t.Any]:
    """
    Given a file path, parse it based on its extension (YAML, TOML or JSON)
    and return the values as a Python dictionary. JSON is the default if an
    extension can't be determined.
    """
    loader: Callable[..., t.Any]
    ext = Path(path).suffix
    if ext in [".yaml", ".yml"]:
        import ruamel.yaml  # noqa: PLC0415

        yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        loader = yaml.load
    elif ext == ".toml":
        loader = load_toml
    else:
        loader = json.load
    with Path(path).open() as f:
        config = loader(f)
    return config or {}


def load_toml(stream: t.TextIO) -> dict[str, t.Any]:
    return tomllib.loads(stream.read())


def _find_file(filename: str, require: bool = True) -> str | None:  # noqa: FBT001, FBT002
    if not Path(filename).exists():
        if not require:
            return None
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filename)
    return str(Path(filename).resolve())


def _fieldinfo_to_str(field_info: FieldInfo) -> str:
    """
    Return the string representation of a pydantic.fields.FieldInfo.
    """
    if isinstance(field_info.annotation, type) and not isinstance(
        field_info.annotation, GenericAlias
    ):
        # For annotation like <class 'int'>, we use its name ("int").
        field_type = field_info.annotation.__name__
    elif str(field_info.annotation).startswith("typing."):
        # For annotation like typing.Literal['a', 'b'], we use
        # its string representation, but without "typing." ("Literal['a', 'b']").
        field_type = str(field_info.annotation)[len("typing.") :]
    else:
        # For annotation like list[str], we use its string
        # representation ("list[str]").
        field_type = str(field_info.annotation)
    return field_type


def initial_for_field(name: str, field_info: FieldInfo) -> t.Any:
    for meta in field_info.metadata:
        if isinstance(meta, _Initial):
            if not callable(meta.factory):
                msg = f"Initial value for `{name}` must be a callable."
                raise TypeError(msg)
            return meta.factory()
    if field_info.default is not PydanticUndefined and field_info.default is not ...:
        return field_info.default
    if field_info.default_factory is not None:
        return field_info.default_factory()  # type: ignore[call-arg]
    if type(None) in t.get_args(field_info.annotation):
        return None
    return ""


class FileConfigSettingsSource(PydanticBaseSettingsSource):
    """
    Source class for loading values provided during settings class initialization.
    """

    def __init__(self, settings_cls: type[BaseSettings]) -> None:
        super().__init__(settings_cls)

    @override
    def get_field_value(
        self,
        field: FieldInfo,
        field_name: str,
    ) -> tuple[t.Any, str, bool]:
        # Nothing to do here. Only implement the return statement to make mypy happy
        return None, "", False

    def __call__(self) -> dict[str, t.Any]:
        settings = t.cast("GoodConf", self.settings_cls)
        selected_config_file = None
        if cfg_file := self.current_state.get("_config_file"):
            selected_config_file = cfg_file
        elif cfg_file := os.environ.get(get_file_env_var(self.settings_cls)):
            selected_config_file = _find_file(cfg_file)
        else:
            for filename in settings.model_config.get("default_files") or []:
                selected_config_file = _find_file(filename, require=False)
                if selected_config_file:
                    break
        if selected_config_file:
            values = _load_config(selected_config_file)
            if Path(selected_config_file).suffix == ".toml":
                values = add_toml_nulls(self.settings_cls, values)
            log.info("Loading config from %s", selected_config_file)
        else:
            values = {}
            log.info("No config file specified. Loading with environment variables.")
        return values

    def __repr__(self) -> str:
        return "FileConfigSettingsSource()"


def get_file_env_var(settings_cls: type[BaseSettings]) -> str:
    """Name of the env var holding the config file path.

    ``model_config["file_env_var"]`` when declared, else derived from the
    class's import path, e.g. ``GOODCONF_MYPROJECT_CONF_APPCONFIG_FILE``.
    """
    if file_env_var := settings_cls.model_config.get("file_env_var"):
        return t.cast("str", file_env_var)
    path = f"{settings_cls.__module__}.{settings_cls.__qualname__}".upper()
    return f"GOODCONF_{re.sub(r'[^A-Z0-9]', '_', path)}_FILE"


def add_toml_nulls(
    settings_cls: type[BaseSettings], values: dict[str, t.Any]
) -> dict[str, t.Any]:
    """TOML has no null; absence is how it says None for a required nullable field.

    https://github.com/lincolnloop/goodconf/issues/148
    """
    nulls: dict[str, None] = {}
    for name, field_info in settings_cls.model_fields.items():
        if not field_info.is_required():
            continue
        if type(None) not in t.get_args(field_info.annotation):
            continue
        keys = get_validation_keys(name, field_info)
        if keys and not any(key in values for key in keys):
            nulls[keys[0]] = None
    return {**values, **nulls}


def get_validation_keys(name: str, field_info: FieldInfo) -> list[str]:
    validation_alias = field_info.validation_alias
    if validation_alias is None:
        return [name]
    if isinstance(validation_alias, str):
        return [validation_alias]
    if isinstance(validation_alias, AliasChoices):
        return [
            choice for choice in validation_alias.choices if isinstance(choice, str)
        ]
    # An AliasPath reaches into nested data, which a missing key can't express.
    return []


class GoodConf(BaseSettings):
    _is_loaded: bool = False

    def __init__(
        self,
        load: bool = False,  # noqa: FBT001, FBT002 — documented public-API positional
        config_file: str | None = None,
        **kwargs: t.Any,
    ) -> None:
        """
        :param load: load config file on instantiation [default: False].

        A docstring defined on the class should be a plain-text description
        used as a header when generating a configuration file.
        """
        if config_file:
            warnings.warn(
                f"{type(self).__name__}(config_file=...) is deprecated and will be "
                "removed in a future release. List the file in "
                "model_config['default_files'] or pass it to load() instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        if kwargs or load:  # Emulate Pydantic behavior, load immediately
            self._load(_init_config_file=config_file, **kwargs)
        elif config_file:
            _object_setattr(
                self, "_load", partial(self._load, _init_config_file=config_file)
            )

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

    @classmethod
    def _settings_build_values(
        cls,
        sources: tuple[PydanticBaseSettingsSource, ...],
        init_kwargs: dict[str, t.Any],
    ) -> dict[str, t.Any]:
        state = super()._settings_build_values(
            sources,
            init_kwargs,
        )
        state.pop("_config_file", None)
        return state

    def _load(
        self,
        _config_file: str | None = None,
        _init_config_file: str | None = None,
        **kwargs: t.Any,
    ) -> None:
        if config_file := _config_file or _init_config_file:
            kwargs["_config_file"] = config_file
        super().__init__(**kwargs)
        self._is_loaded = True

    def load(self, filename: str | None = None) -> None:
        self._load(_config_file=filename)

    @property
    def is_loaded(self) -> bool:
        # Pydantic sets up private attributes on the first load; until then the
        # class default above isn't reachable through the instance.
        return getattr(self, "_is_loaded", False)

    @classmethod
    def get_initial(cls, **override: t.Any) -> dict[str, t.Any]:
        return {
            k: override.get(k, initial_for_field(k, v))
            for k, v in cls.model_fields.items()
        }

    @classmethod
    def generate_yaml(cls, **override: t.Any) -> str:
        """
        Dumps initial config in YAML
        """
        import ruamel.yaml  # noqa: PLC0415

        yaml = ruamel.yaml.YAML()
        yaml.representer.add_representer(
            type(None),
            lambda self, d: self.represent_scalar("tag:yaml.org,2002:null", "~"),  # noqa: ARG005
        )
        yaml_str = StringIO()
        yaml.dump(cls.get_initial(**override), stream=yaml_str)
        yaml_str.seek(0)
        dict_from_yaml = yaml.load(yaml_str)
        if cls.__doc__:
            dict_from_yaml.yaml_set_start_comment("\n" + cls.__doc__ + "\n\n")
        for k in dict_from_yaml:
            if cls.model_fields[k].description:
                description = t.cast("str", cls.model_fields[k].description)
                dict_from_yaml.yaml_set_comment_before_after_key(
                    k, before="\n" + description
                )
        yaml_str = StringIO()
        yaml.dump(dict_from_yaml, yaml_str)
        yaml_str.seek(0)
        return yaml_str.read()

    @classmethod
    def generate_json(cls, **override: t.Any) -> str:
        """
        Dumps initial config in JSON
        """
        return json.dumps(cls.get_initial(**override), indent=2)

    @classmethod
    def generate_toml(cls, **override: t.Any) -> str:
        """
        Dumps initial config in TOML
        """
        import tomlkit  # noqa: PLC0415

        initial = cls.get_initial(**override)
        toml_str = tomlkit.dumps({k: v for k, v in initial.items() if v is not None})
        dict_from_toml = tomlkit.loads(toml_str)
        document = tomlkit.document()
        if cls.__doc__:
            document.add(tomlkit.comment(cls.__doc__))
        for k, v in dict_from_toml.unwrap().items():
            item = tomlkit.item(v)
            if cls.model_fields[k].description:
                description = t.cast("str", cls.model_fields[k].description)
                item.comment(description)
            document.add(k, item)
        # TOML has no null, so None fields are listed rather than written.
        # https://github.com/lincolnloop/goodconf/issues/148
        if null_keys := [k for k, v in initial.items() if v is None]:
            document.add(tomlkit.nl())
            document.add(tomlkit.comment("Not set, defaults to None:"))
            for k in null_keys:
                null_description = cls.model_fields[k].description
                entry = f"- {k}: {null_description}" if null_description else f"- {k}"
                document.add(tomlkit.comment(entry))
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
            # We want to append a line with the field_info type, and sometimes
            # field_info.annotation looks the way we want, like 'list[str]', but
            # other times, it includes some extra text, like '<class 'bool'>'.
            # Therefore, we have some logic to make the type show up the way we want.
            field_type = _fieldinfo_to_str(field_info)
            lines.append(f"  * type: `{field_type}`")
            if field_info.default not in [None, PydanticUndefined]:
                lines.append(f"  * default: `{field_info.default}`")
        return "\n".join(lines)

    def django_manage(self, args: list[str] | None = None) -> None:
        args = args or sys.argv
        from goodconf.contrib.django import (  # noqa: PLC0415
            execute_from_command_line_with_config,
        )

        execute_from_command_line_with_config(self, args)
