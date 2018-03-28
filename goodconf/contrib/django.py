import argparse
from typing import List

from goodconf import GoodConf
from .argparse import argparser_add_argument


def _monkeypatch_commandparser(config: GoodConf):
    """Adds -C, --config to Django BaseCommand"""
    from django.core.management.base import BaseCommand
    default_parser = BaseCommand.create_parser

    def patched_parser(self, prog_name, subcommand):
        parser = default_parser(self, prog_name, subcommand)
        argparser_add_argument(parser, config)
        return parser
    BaseCommand.create_parser = patched_parser


def load_config_from_cli(config: GoodConf, argv: List[str]) -> List[str]:
    """Loads config, checking CLI arguments for a config file"""
    _monkeypatch_commandparser(config)

    parser = argparse.ArgumentParser(add_help=False)
    argparser_add_argument(parser, config)

    config_arg, default_args = parser.parse_known_args(argv)
    config.load(config_arg.config)
    return default_args


def execute_from_command_line_with_config(config: GoodConf, argv: List[str]):
    """Load's config then runs Django's execute_from_command_line"""
    args = load_config_from_cli(config, argv)
    from django.core.management import execute_from_command_line
    execute_from_command_line(args)
