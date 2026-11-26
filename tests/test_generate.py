import typing as t
from pathlib import Path

import pytest
import tomlkit.exceptions

from goodconf import Field, GoodConf


def test_get_initial() -> None:
    class AppConfig(GoodConf):
        debug: bool = False
        secret_key: str = Field(initial=lambda: "generated")
        port: int = Field(gt=0, initial=lambda: 8000)
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        database_url: str
        sentry_dsn: str | None

    assert AppConfig.get_initial() == {
        "debug": False,
        "secret_key": "generated",
        "port": 8000,
        "hosts": ["localhost"],
        "database_url": "",
        "sentry_dsn": None,
    }


def test_get_initial_prefers_initial_over_default() -> None:
    class AppConfig(GoodConf):
        secret_key: str = Field(default="default", initial=lambda: "generated")

    assert AppConfig.get_initial() == {"secret_key": "generated"}


def test_get_initial_override() -> None:
    class AppConfig(GoodConf):
        debug: bool = False
        database_url: str

    assert AppConfig.get_initial(database_url="postgres://", unknown="ignored") == {
        "debug": False,
        "database_url": "postgres://",
    }


def test_get_initial_non_callable_initial() -> None:
    class AppConfig(GoodConf):
        secret_key: str = Field(initial="generated")  # type: ignore[arg-type]

    with pytest.raises(TypeError) as exc_info:
        AppConfig.get_initial()

    assert str(exc_info.value) == "Initial value for `secret_key` must be a callable."


def test_json_schema_excludes_initial() -> None:
    class AppConfig(GoodConf):
        secret_key: str = Field(default="default", initial=lambda: "generated")

    assert AppConfig.model_json_schema() == {
        "additionalProperties": False,
        "properties": {
            "secret_key": {
                "default": "default",
                "title": "Secret Key",
                "type": "string",
            }
        },
        "title": "AppConfig",
        "type": "object",
    }


def test_generate_json() -> None:
    class AppConfig(GoodConf):
        """Configuration for My App"""

        debug: bool = Field(default=False, description="Enable debug mode")
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        database_url: str
        sentry_dsn: str | None

    assert AppConfig.generate_json(database_url="postgres://", unknown="x") == (
        "{\n"
        '  "debug": false,\n'
        '  "hosts": [\n'
        '    "localhost"\n'
        "  ],\n"
        '  "database_url": "postgres://",\n'
        '  "sentry_dsn": null\n'
        "}"
    )


def test_generate_yaml() -> None:
    class AppConfig(GoodConf):
        """Configuration for My App"""

        debug: bool = Field(default=False, description="Enable debug mode")
        secret_key: str = Field(initial=lambda: "generated", description="Signing key")
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        mode: t.Literal["dev", "prod"] = "dev"
        database_url: str
        sentry_dsn: str | None

    assert AppConfig.generate_yaml() == (
        "\n"
        "# Configuration for My App\n"
        "\n"
        "\n"
        "# Enable debug mode\n"
        "debug: false\n"
        "\n"
        "# Signing key\n"
        "secret_key: generated\n"
        "hosts:\n"
        "- localhost\n"
        "mode: dev\n"
        "database_url: ''\n"
        "sentry_dsn: ~\n"
    )


def test_generate_yaml_without_docstring() -> None:
    class AppConfig(GoodConf):
        debug: bool = Field(default=False, description="Enable debug mode")
        database_url: str

    assert AppConfig.generate_yaml() == (
        "\n# Enable debug mode\ndebug: false\ndatabase_url: ''\n"
    )


def test_generate_yaml_override() -> None:
    class AppConfig(GoodConf):
        debug: bool = False
        database_url: str

    assert AppConfig.generate_yaml(database_url="postgres://", unknown="x") == (
        "debug: false\ndatabase_url: postgres://\n"
    )


def test_generate_toml() -> None:
    class AppConfig(GoodConf):
        """Configuration for My App"""

        debug: bool = False
        secret_key: str = Field(initial=lambda: "generated", description="Signing key")
        port: int = Field(default=8000, description="Listen port")
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        mode: t.Literal["dev", "prod"] = "dev"
        database_url: str

    assert AppConfig.generate_toml() == (
        "# Configuration for My App\n"
        "debug = false\n"
        'secret_key = "generated" # Signing key\n'
        "port = 8000 # Listen port\n"
        'hosts = ["localhost"]\n'
        'mode = "dev"\n'
        'database_url = ""\n'
    )


def test_generate_toml_without_docstring() -> None:
    class AppConfig(GoodConf):
        database_url: str = Field(description="Database DSN")

    assert AppConfig.generate_toml() == 'database_url = "" # Database DSN\n'


def test_generate_toml_override() -> None:
    class AppConfig(GoodConf):
        debug: bool = False
        database_url: str

    assert AppConfig.generate_toml(database_url="postgres://", unknown="x") == (
        'debug = false\ndatabase_url = "postgres://"\n'
    )


@pytest.mark.xfail(
    raises=AttributeError,
    reason="generate_toml crashes on bool descriptions",
    strict=True,
)
def test_generate_toml_bool_description() -> None:
    class AppConfig(GoodConf):
        debug: bool = Field(default=False, description="Enable debug mode")

    assert AppConfig.generate_toml() == "debug = false # Enable debug mode\n"


@pytest.mark.xfail(
    raises=tomlkit.exceptions.ConvertError,
    reason="generate_toml crashes on None values",
    strict=True,
)
def test_generate_toml_none_loads(tmp_path: Path) -> None:
    class AppConfig(GoodConf):
        sentry_dsn: str | None = None
        database_url: str

    path = tmp_path / "app.toml"
    path.write_text(AppConfig.generate_toml(database_url="postgres://"))
    config = AppConfig()
    config.load(str(path))

    assert config.model_dump() == {"sentry_dsn": None, "database_url": "postgres://"}


@pytest.mark.parametrize(
    ("filename", "method_name"),
    [
        pytest.param("app.json", "generate_json", id="json"),
        pytest.param("app.toml", "generate_toml", id="toml"),
        pytest.param("app.yaml", "generate_yaml", id="yaml"),
    ],
)
def test_generated_file_loads(filename: str, method_name: str, tmp_path: Path) -> None:
    class AppConfig(GoodConf):
        """Configuration for My App"""

        debug: bool = False
        secret_key: str = Field(initial=lambda: "generated", description="Signing key")
        port: int = Field(default=8000, description="Listen port")
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        database_url: str

    path = tmp_path / filename
    path.write_text(getattr(AppConfig, method_name)(database_url="postgres://"))
    config = AppConfig()
    config.load(str(path))

    assert config.model_dump() == {
        "debug": False,
        "secret_key": "generated",
        "port": 8000,
        "hosts": ["localhost"],
        "database_url": "postgres://",
    }


def test_generate_markdown() -> None:
    class AppConfig(GoodConf):
        """Configuration for My App"""

        debug: bool = Field(default=False, description="Enable debug mode")
        secret_key: str = Field(initial=lambda: "generated", description="Signing key")
        hosts: list[str] = Field(default_factory=lambda: ["localhost"])
        mode: t.Literal["dev", "prod"] = "dev"
        sentry_dsn: str | None = None
        database_url: str

    assert AppConfig.generate_markdown() == (
        "# Configuration for My App\n"
        "\n"
        "* **debug**\n"
        "  * description: Enable debug mode\n"
        "  * type: `bool`\n"
        "  * default: `False`\n"
        "* **secret_key** _REQUIRED_\n"
        "  * description: Signing key\n"
        "  * type: `str`\n"
        "* **hosts**\n"
        "  * type: `list[str]`\n"
        "* **mode**\n"
        "  * type: `Literal['dev', 'prod']`\n"
        "  * default: `dev`\n"
        "* **sentry_dsn**\n"
        "  * type: `str | None`\n"
        "* **database_url** _REQUIRED_\n"
        "  * type: `str`"
    )


def test_generate_markdown_without_docstring() -> None:
    class AppConfig(GoodConf):
        port: int = 8000

    assert AppConfig.generate_markdown() == (
        "* **port**\n  * type: `int`\n  * default: `8000`"
    )
