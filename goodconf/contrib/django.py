import argparse
from contextlib import contextmanager
from typing import List

from goodconf import GoodConf

from .argparse import argparser_add_argument


@contextmanager
def load_config_from_cli(config: GoodConf, argv: List[str]) -> List[str]:
    """Loads config, checking CLI arguments for a config file"""

    # Monkey patch Django's command parser
    from django.core.management.base import BaseCommand

    original_parser = BaseCommand.create_parser

    def patched_parser(self, prog_name, subcommand):
        parser = original_parser(self, prog_name, subcommand)
        argparser_add_argument(parser, config)
        return parser

    BaseCommand.create_parser = patched_parser

    try:
        parser = argparse.ArgumentParser(add_help=False)
        argparser_add_argument(parser, config)

        config_arg, default_args = parser.parse_known_args(argv)
        config.load(config_arg.config)
        yield default_args
    finally:
        # Put that create_parser back where it came from or so help me!
        BaseCommand.create_parser = original_parser


def execute_from_command_line_with_config(config: GoodConf, argv: List[str]):
    """Load's config then runs Django's execute_from_command_line"""
    with load_config_from_cli(config, argv) as args:
        from django.core.management import execute_from_command_line

        execute_from_command_line(args)
