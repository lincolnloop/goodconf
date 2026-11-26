import argparse
import re

import pytest

from goodconf import GoodConf, GoodConfConfigDict
from goodconf.contrib.argparse import argparser_add_argument


@pytest.fixture(autouse=True)
def wide_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "200")


@pytest.mark.parametrize(
    ("config_dict", "expected_help"),
    [
        pytest.param(GoodConfConfigDict(), "Config file.", id="plain"),
        pytest.param(
            GoodConfConfigDict(default_files=["/etc/myapp.json", "myapp.json"]),
            "Config file. Defaults to the first file that exists from "
            "[/etc/myapp.json, myapp.json].",
            id="default-files",
        ),
        pytest.param(
            GoodConfConfigDict(file_env_var="MYAPP_CONF"),
            "Config file. Can also be configured via the environment variable: "
            "MYAPP_CONF.",
            id="file-env-var",
            marks=pytest.mark.xfail(
                raises=AssertionError,
                reason="https://github.com/lincolnloop/goodconf/issues/147",
                strict=True,
            ),
        ),
        pytest.param(
            GoodConfConfigDict(
                file_env_var="MYAPP_CONF",
                default_files=["/etc/myapp.json", "myapp.json"],
            ),
            "Config file. Can also be configured via the environment variable: "
            "MYAPP_CONF. Defaults to the first file that exists from "
            "[/etc/myapp.json, myapp.json].",
            id="file-env-var-and-default-files",
            marks=pytest.mark.xfail(
                raises=AssertionError,
                reason="https://github.com/lincolnloop/goodconf/issues/147",
                strict=True,
            ),
        ),
    ],
)
def test_argparser_add_argument_help(
    config_dict: GoodConfConfigDict, expected_help: str
) -> None:
    class AppConfig(GoodConf):
        model_config = config_dict

    parser = argparse.ArgumentParser(prog="myapp")
    argparser_add_argument(parser, AppConfig())
    match = re.search(r"--config FILE\s+(.+)", parser.format_help())

    assert match is not None
    assert match.group(1) == expected_help


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["-C", "app.json"], id="short"),
        pytest.param(["--config", "app.json"], id="long"),
    ],
)
def test_argparser_add_argument_parses_config(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="myapp")
    argparser_add_argument(parser, GoodConf())

    assert parser.parse_args(argv) == argparse.Namespace(config="app.json")
