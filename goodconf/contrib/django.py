import sys
import argparse
from typing import List

from goodconf import GoodConf


def _monkeypatch_commandparser(*args, **kwargs):
    """Adds -c, --config to Django BaseCommand"""
    from django.core.management.base import BaseCommand
    default_parser = BaseCommand.create_parser

    def patched_parser(self, prog_name, subcommand):
        parser = default_parser(self, prog_name, subcommand)
        parser.add_argument(*args, **kwargs)
        return parser
    BaseCommand.create_parser = patched_parser


def load_config_from_cli(config: GoodConf) -> List[str]:
    """Loads config, checking CLI arguments for a config file"""
    config_argparser_args = ['-c', '--config']
    help = "Config file."
    if config.file_env_var:
        help += (" Can also be configured via the "
                 "environment variable: {}".format(config.file_env_var))
    if config.default_files:
        help += (" Defaults to the first file that exists from "
                 "[{}].".format(', '.join(config.default_files)))
    config_argparser_kwargs = dict(
        metavar='FILE',
        help=help
    )
    _monkeypatch_commandparser(*config_argparser_args,
                               **config_argparser_kwargs)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(*config_argparser_args,
                        **config_argparser_kwargs)

    config_arg, default_args = parser.parse_known_args(sys.argv)
    config.load(config_arg.config)
    return default_args


def execute_from_command_line_with_config(config: GoodConf):
    """Load's config then runs Django's execute_from_command_line"""
    args = load_config_from_cli(config)
    from django.core.management import execute_from_command_line
    execute_from_command_line(args)
