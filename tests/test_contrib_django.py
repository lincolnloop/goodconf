import re
from pathlib import Path

import pytest

from tests import utils

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
def test_manage_config_option(argv: list[str], tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-option"}')

    result = utils.run_manage(tmp_path, *argv)

    assert result.stderr == ""
    assert result.stdout == "from-option\n"
    assert result.returncode == 0


def test_manage_config_file_env_var(tmp_path: Path) -> None:
    (tmp_path / "app.json").write_text('{"APP_NAME": "from-env-var"}')

    result = utils.run_manage(
        tmp_path,
        "shell",
        "--no-imports",
        "-c",
        PRINT_APP_NAME,
        EXAMPLEPROJECT_CONF="app.json",
    )

    assert result.stderr == ""
    assert result.stdout == "from-env-var\n"
    assert result.returncode == 0


def test_manage_default_file(tmp_path: Path) -> None:
    (tmp_path / "exampleproject.json").write_text('{"APP_NAME": "from-default-file"}')

    result = utils.run_manage(tmp_path, "shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "from-default-file\n"
    assert result.returncode == 0


def test_manage_without_config_file(tmp_path: Path) -> None:
    result = utils.run_manage(tmp_path, "shell", "--no-imports", "-c", PRINT_APP_NAME)

    assert result.stderr == ""
    assert result.stdout == "default\n"
    assert result.returncode == 0


@pytest.mark.xfail(
    raises=AssertionError,
    reason="https://github.com/lincolnloop/goodconf/issues/147",
    strict=True,
)
def test_manage_help_lists_config_option(tmp_path: Path) -> None:
    # Wide enough that argparse keeps the option's help on one line.
    result = utils.run_manage(tmp_path, "check", "-h", COLUMNS="200")
    match = re.search(r"--config FILE\s+(.+)", result.stdout)

    assert result.returncode == 0
    assert match is not None
    assert match.group(1) == (
        "Config file. Can also be configured via the environment variable: "
        "EXAMPLEPROJECT_CONF. Defaults to the first file that exists from "
        "[exampleproject.json]."
    )
