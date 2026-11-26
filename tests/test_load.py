import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from goodconf import GoodConf, GoodConfConfigDict


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        pytest.param("app.json", '{"app_name": "file", "app_port": 8000}', id="json"),
        pytest.param("app.toml", 'app_name = "file"\napp_port = 8000\n', id="toml"),
        pytest.param(
            "app.conf", '{"app_name": "file", "app_port": 8000}', id="unknown-as-json"
        ),
        pytest.param("app.yaml", "app_name: file\napp_port: 8000\n", id="yaml"),
        pytest.param("app.yml", "app_name: file\napp_port: 8000\n", id="yml"),
    ],
)
def test_load_file_by_extension(
    caplog: pytest.LogCaptureFixture, content: str, filename: str, tmp_path: Path
) -> None:
    path = tmp_path / filename
    path.write_text(content)

    class AppConfig(GoodConf):
        app_name: str
        app_port: int

    config = AppConfig()
    with caplog.at_level(logging.INFO, logger="goodconf"):
        config.load(str(path))

    assert config.model_dump() == {"app_name": "file", "app_port": 8000}
    assert caplog.record_tuples == [
        ("goodconf", logging.INFO, f"Loading config from {path}")
    ]


@pytest.mark.parametrize(
    "filename",
    [
        pytest.param("app.toml", id="toml"),
        pytest.param("app.yaml", id="yaml"),
    ],
)
def test_load_empty_file_uses_defaults(filename: str, tmp_path: Path) -> None:
    path = tmp_path / filename
    path.write_text("")

    class AppConfig(GoodConf):
        app_name: str = "default"

    config = AppConfig()
    config.load(str(path))

    assert config.model_dump() == {"app_name": "default"}


def test_load_config_file_from_init(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')

    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig(config_file=str(path))
    with caplog.at_level(logging.INFO, logger="goodconf"):
        config.load()

    assert config.model_dump() == {"app_name": "file"}
    assert caplog.record_tuples == [
        ("goodconf", logging.INFO, f"Loading config from {path}")
    ]


def test_load_config_file_from_init_with_load(tmp_path: Path) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')

    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig(load=True, config_file=str(path))

    assert config.model_dump() == {"app_name": "file"}


def test_load_explicit_file_over_init_file(tmp_path: Path) -> None:
    init_path = tmp_path / "init.json"
    init_path.write_text('{"app_name": "init-file"}')
    explicit_path = tmp_path / "explicit.json"
    explicit_path.write_text('{"app_name": "explicit-file"}')

    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig(config_file=str(init_path))
    config.load(str(explicit_path))

    assert config.model_dump() == {"app_name": "explicit-file"}


def test_load_file_env_var(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_CONFIG", "app.json")

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(file_env_var="APP_CONFIG")

        app_name: str

    config = AppConfig()
    with caplog.at_level(logging.INFO, logger="goodconf"):
        config.load()

    assert config.model_dump() == {"app_name": "file"}
    assert caplog.record_tuples == [
        ("goodconf", logging.INFO, f"Loading config from {path.resolve()}")
    ]


def test_load_file_env_var_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_CONFIG", "missing.json")

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(file_env_var="APP_CONFIG")

    config = AppConfig()
    with pytest.raises(FileNotFoundError) as exc_info:
        config.load()

    assert str(exc_info.value) == "[Errno 2] No such file or directory: 'missing.json'"


def test_load_explicit_file_over_file_env_var(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / "env.json"
    env_path.write_text('{"app_name": "env-file"}')
    explicit_path = tmp_path / "explicit.json"
    explicit_path.write_text('{"app_name": "explicit-file"}')
    monkeypatch.setenv("APP_CONFIG", str(env_path))

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(file_env_var="APP_CONFIG")

        app_name: str

    config = AppConfig()
    config.load(str(explicit_path))

    assert config.model_dump() == {"app_name": "explicit-file"}


def test_load_file_env_var_over_default_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_path = tmp_path / "env.json"
    env_path.write_text('{"app_name": "env-file"}')
    default_path = tmp_path / "default.json"
    default_path.write_text('{"app_name": "default-file"}')
    monkeypatch.setenv("APP_CONFIG", str(env_path))

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(
            file_env_var="APP_CONFIG", default_files=[str(default_path)]
        )

        app_name: str

    config = AppConfig()
    config.load()

    assert config.model_dump() == {"app_name": "env-file"}


def test_load_default_files_when_file_env_var_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    default_path = tmp_path / "default.json"
    default_path.write_text('{"app_name": "default-file"}')
    monkeypatch.delenv("APP_CONFIG", raising=False)

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(
            file_env_var="APP_CONFIG", default_files=[str(default_path)]
        )

        app_name: str

    config = AppConfig()
    config.load()

    assert config.model_dump() == {"app_name": "default-file"}


def test_load_first_existing_default_file(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    missing_path = tmp_path / "missing.json"
    first_path = tmp_path / "first.json"
    first_path.write_text('{"app_name": "first"}')
    second_path = tmp_path / "second.json"
    second_path.write_text('{"app_name": "second"}')

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(
            default_files=[str(missing_path), str(first_path), str(second_path)]
        )

        app_name: str

    config = AppConfig()
    with caplog.at_level(logging.INFO, logger="goodconf"):
        config.load()

    assert config.model_dump() == {"app_name": "first"}
    assert caplog.record_tuples == [
        ("goodconf", logging.INFO, f"Loading config from {first_path.resolve()}")
    ]


def test_load_without_file_uses_env(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APP_NAME", "env")

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(
            default_files=[str(tmp_path / "missing.json")]
        )

        app_name: str
        app_port: int = 8000

    config = AppConfig()
    with caplog.at_level(logging.INFO, logger="goodconf"):
        config.load()

    assert config.model_dump() == {"app_name": "env", "app_port": 8000}
    assert caplog.record_tuples == [
        (
            "goodconf",
            logging.INFO,
            "No config file specified. Loading with environment variables.",
        )
    ]


def test_load_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "unprefixed")
    monkeypatch.setenv("MYAPP_APP_NAME", "prefixed")

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(env_prefix="MYAPP_")

        app_name: str

    config = AppConfig(load=True)

    assert config.model_dump() == {"app_name": "prefixed"}


def test_load_precedence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "app.json"
    path.write_text(
        json.dumps({"from_init": "file", "from_env": "file", "from_file": "file"})
    )
    monkeypatch.setenv("FROM_INIT", "env")
    monkeypatch.setenv("FROM_ENV", "env")

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(default_files=[str(path)])

        from_init: str = "default"
        from_env: str = "default"
        from_file: str = "default"
        from_default: str = "default"

    config = AppConfig(from_init="init")

    assert config.model_dump() == {
        "from_init": "init",
        "from_env": "env",
        "from_file": "file",
        "from_default": "default",
    }


def test_init_without_load_defers_validation(tmp_path: Path) -> None:
    path = tmp_path / "app.json"

    class AppConfig(GoodConf):
        model_config = GoodConfConfigDict(default_files=[str(path)])

        app_name: str

    config = AppConfig()
    path.write_text('{"app_name": "file"}')
    config.load()

    assert config.model_dump() == {"app_name": "file"}


def test_load_class_keyword_config(tmp_path: Path) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')

    class AppConfig(GoodConf, default_files=[str(path)]):
        app_name: str

    config = AppConfig()
    config.load()

    assert config.model_dump() == {"app_name": "file"}


def test_load_required_missing() -> None:
    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig()
    with pytest.raises(ValidationError) as exc_info:
        config.load()

    assert exc_info.value.errors(include_url=False) == [
        {
            "type": "missing",
            "loc": ("app_name",),
            "msg": "Field required",
            "input": {},
        }
    ]


def test_init_with_load_required_missing() -> None:
    class AppConfig(GoodConf):
        app_name: str

    with pytest.raises(ValidationError) as exc_info:
        AppConfig(load=True)

    assert exc_info.value.errors(include_url=False) == [
        {
            "type": "missing",
            "loc": ("app_name",),
            "msg": "Field required",
            "input": {},
        }
    ]


def test_load_invalid_file_value(tmp_path: Path) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_port": "eighty"}')

    class AppConfig(GoodConf):
        app_port: int

    config = AppConfig()
    with pytest.raises(ValidationError) as exc_info:
        config.load(str(path))

    assert exc_info.value.errors(include_url=False) == [
        {
            "type": "int_parsing",
            "loc": ("app_port",),
            "msg": (
                "Input should be a valid integer, unable to parse string as an integer"
            ),
            "input": "eighty",
        }
    ]


def test_load_again_replaces_values(tmp_path: Path) -> None:
    first_path = tmp_path / "first.json"
    first_path.write_text('{"app_name": "first", "app_port": 1}')
    second_path = tmp_path / "second.json"
    second_path.write_text('{"app_name": "second"}')

    class AppConfig(GoodConf):
        app_name: str
        app_port: int = 8000

    config = AppConfig()
    config.load(str(first_path))
    config.load(str(second_path))

    assert config.model_dump() == {"app_name": "second", "app_port": 8000}
