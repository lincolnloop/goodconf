import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import django
import pytest

from goodconf import GoodConf, GoodConfConfigDict

PRINT_APP_NAME = "from django.conf import settings; print(settings.APP_NAME)"


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(
            ["shell", "--no-imports", "-c", PRINT_APP_NAME, "-C", "app.json"],
            id="after-subcommand",
        ),
        pytest.param(
            ["-C", "app.json", "shell", "--no-imports", "-c", PRINT_APP_NAME],
            id="before-subcommand",
        ),
    ],
)
def test_manage_config_option(
    argv: list[str],
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-option"}')

    result = manage_py(*argv)

    assert result.stderr == ""
    assert result.returncode == 0
    assert result.stdout == "from-option\n"


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["check", "-C", "app.json"], id="after-subcommand"),
        pytest.param(["-C", "app.json", "check"], id="before-subcommand"),
    ],
)
def test_manage_config_option_runs_command(
    argv: list[str],
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-option"}')

    result = manage_py(*argv)

    assert result.stderr == ""
    assert result.stdout == "System check identified no issues (0 silenced).\n"
    assert result.returncode == 0


def test_manage_config_option_missing_file(
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = manage_py("check", "-C", "missing.json")

    assert result.stderr.splitlines()[-1] == (
        "FileNotFoundError: [Errno 2] No such file or directory: 'missing.json'"
    )
    assert result.stdout == ""
    assert result.returncode == 1


def test_manage_config_file_env_var(
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-env-var"}')

    result = manage_py(
        "shell",
        "--no-imports",
        "-c",
        PRINT_APP_NAME,
        PROJECT_CONF="app.json",
    )

    assert result.stderr == ""
    assert result.stdout == "from-env-var\n"
    assert result.returncode == 0


def test_manage_default_file(
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "project.json").write_text('{"APP_NAME": "from-default-file"}')

    result = manage_py("shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "from-default-file\n"
    assert result.returncode == 0


def test_manage_without_config_file(
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = manage_py("shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "default\n"
    assert result.returncode == 0


def test_manage_help_lists_config_option(
    manage_py: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    # Wide enough that argparse keeps the option's help on one line.
    result = manage_py("check", "-h", COLUMNS="200")
    match = re.search(r"--config FILE\s+(.+)", result.stdout)

    assert result.returncode == 0
    assert match is not None
    assert match.group(1) == (
        "Config file. Can also be configured via the environment variable: "
        "PROJECT_CONF. Defaults to the first file that exists from "
        "[project.json]."
    )


def test_django_manage_args(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / "app.json"
    path.write_text('{"app_name": "from-option"}')

    class AppConfig(GoodConf):
        app_name: str = "default"

    config = AppConfig()
    config.django_manage(["manage.py", "-C", str(path), "version"])
    config.load()

    assert capsys.readouterr().out == f"{django.get_version()}\n"
    assert config.model_dump() == {"app_name": "from-option"}


@pytest.mark.parametrize(
    ("config_dict", "expected_help"),
    [
        pytest.param(
            GoodConfConfigDict(default_files=["/etc/myapp.json", "myapp.json"]),
            "Config file. Defaults to the first file that exists from "
            "[/etc/myapp.json, myapp.json].",
            id="default-files",
        ),
        pytest.param(GoodConfConfigDict(), "Config file.", id="plain"),
    ],
)
def test_django_manage_help(
    capsys: pytest.CaptureFixture[str],
    config_dict: GoodConfConfigDict,
    expected_help: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Wide enough that argparse keeps the option's help on one line.
    monkeypatch.setenv("COLUMNS", "200")

    class AppConfig(GoodConf):
        model_config = config_dict

    with pytest.raises(SystemExit) as exc_info:
        AppConfig().django_manage(["manage.py", "shell", "-h"])
    match = re.search(r"--config FILE\s+(.+)", capsys.readouterr().out)

    assert exc_info.value.code == 0
    assert match is not None
    assert match.group(1) == expected_help
