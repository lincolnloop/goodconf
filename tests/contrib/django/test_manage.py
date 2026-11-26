import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

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
@pytest.mark.xfail(
    raises=AssertionError,
    reason="https://github.com/lincolnloop/goodconf/issues/150",
    strict=True,
)
def test_manage_config_option(
    argv: list[str],
    manage: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-option"}')

    result = manage(*argv)

    assert result.stderr == ""
    assert result.stdout == "from-option\n"
    assert result.returncode == 0


def test_manage_config_file_env_var(
    manage: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-env-var"}')

    result = manage(
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
    manage: Callable[..., subprocess.CompletedProcess[str]],
    tmp_path: Path,
) -> None:
    (tmp_path / "project.json").write_text('{"APP_NAME": "from-default-file"}')

    result = manage("shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "from-default-file\n"
    assert result.returncode == 0


def test_manage_without_config_file(
    manage: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    result = manage("shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "default\n"
    assert result.returncode == 0


@pytest.mark.xfail(
    raises=AssertionError,
    reason="https://github.com/lincolnloop/goodconf/issues/147",
    strict=True,
)
def test_manage_help_lists_config_option(
    manage: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    # Wide enough that argparse keeps the option's help on one line.
    result = manage("check", "-h", COLUMNS="200")
    match = re.search(r"--config FILE\s+(.+)", result.stdout)

    assert result.returncode == 0
    assert match is not None
    assert match.group(1) == (
        "Config file. Can also be configured via the environment variable: "
        "PROJECT_CONF. Defaults to the first file that exists from "
        "[project.json]."
    )
