import argparse
import typing as t
from collections.abc import Generator
from contextlib import contextmanager

from django.core.management import execute_from_command_line
from django.core.management.base import BaseCommand, CommandParser

from goodconf import GoodConf
from goodconf.contrib.argparse import argparser_add_argument

__all__ = ["execute_from_command_line", "parse_config_option"]


@contextmanager
def parse_config_option(
    config: GoodConf, argv: list[str]
) -> Generator[tuple[str | None, list[str]], None, None]:
    """Split ``-C/--config`` from ``argv``; Django's commands list it in --help."""
    original_parser = BaseCommand.create_parser

    def patched_parser(
        self: BaseCommand,
        prog_name: str,
        subcommand: str,
        **kwargs: t.Any,
    ) -> CommandParser:
        parser = original_parser(self, prog_name, subcommand, **kwargs)
        argparser_add_argument(parser, config)
        return parser

    BaseCommand.create_parser = patched_parser
    try:
        parser = argparse.ArgumentParser(add_help=False)
        argparser_add_argument(parser, config)

        config_arg, django_args = parser.parse_known_args(argv)
        yield config_arg.config, django_args
    finally:
        # Put that create_parser back where it came from or so help me!
        BaseCommand.create_parser = original_parser
