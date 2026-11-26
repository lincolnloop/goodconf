import sys
from pathlib import Path

import pytest
from django.core.management.base import BaseCommand, CommandError
from pydantic import ValidationError

from goodconf import GoodConf
from goodconf.contrib import django as goodconf_django


@pytest.fixture(autouse=True)
def django_settings_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "tests.django_settings")


@pytest.mark.parametrize(
    ("argv_after_config", "argv_before_config"),
    [
        pytest.param(
            [],
            ["manage.py", "shell", "--no-imports", "-c", "print('ran')"],
            id="after-subcommand",
        ),
        pytest.param(
            ["shell", "--no-imports", "-c", "print('ran')"],
            ["manage.py"],
            id="before-subcommand",
        ),
    ],
)
def test_django_manage_loads_config_and_runs_command(
    argv_after_config: list[str],
    argv_before_config: list[str],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')

    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig()
    config.django_manage([*argv_before_config, "-C", str(path), *argv_after_config])

    assert config.model_dump() == {"app_name": "file"}
    assert capsys.readouterr().out == "ran\n"


def test_django_manage_defaults_to_sys_argv(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "file"}')
    monkeypatch.setattr(
        sys,
        "argv",
        ["manage.py", "shell", "--no-imports", "-c", "print('ran')", "-C", str(path)],
    )

    class AppConfig(GoodConf):
        app_name: str

    config = AppConfig()
    config.django_manage()

    assert config.model_dump() == {"app_name": "file"}
    assert capsys.readouterr().out == "ran\n"


def test_django_manage_restores_command_parser() -> None:
    class AppConfig(GoodConf):
        app_name: str = "default"

    AppConfig().django_manage(["manage.py", "shell", "--no-imports", "-c", "pass"])
    parser = BaseCommand().create_parser("manage.py", "check")
    with pytest.raises(CommandError) as exc_info:
        parser.parse_args(["-C", "app.json"])

    assert str(exc_info.value) == "Error: unrecognized arguments: -C app.json"


def test_django_manage_restores_command_parser_on_error() -> None:
    class AppConfig(GoodConf):
        app_name: str

    with pytest.raises(ValidationError) as validation_exc_info:
        AppConfig().django_manage(["manage.py", "check"])
    parser = BaseCommand().create_parser("manage.py", "check")
    with pytest.raises(CommandError) as command_exc_info:
        parser.parse_args(["-C", "app.json"])

    assert validation_exc_info.value.errors(include_url=False) == [
        {
            "type": "missing",
            "loc": ("app_name",),
            "msg": "Field required",
            "input": {},
        }
    ]
    assert str(command_exc_info.value) == "Error: unrecognized arguments: -C app.json"


def test_load_config_from_cli_forwards_create_parser_kwargs() -> None:
    class AppConfig(GoodConf):
        app_name: str = "default"

    with goodconf_django.load_config_from_cli(AppConfig(), ["manage.py"]):
        parser = BaseCommand().create_parser("manage.py", "check", usage="custom usage")

    assert parser.format_usage() == "usage: custom usage\n"
