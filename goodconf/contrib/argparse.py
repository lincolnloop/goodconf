import argparse
from .. import GoodConf


def argparser_add_argument(parser: argparse.ArgumentParser, config: GoodConf):
    """Adds argument for config to existing argparser"""
    args = ['-c', '--config']
    help = "Config file."
    if config.file_env_var:
        help += (" Can also be configured via the "
                 "environment variable: {}".format(config.file_env_var))
    if config.default_files:
        help += (" Defaults to the first file that exists from "
                 "[{}].".format(', '.join(config.default_files)))
    parser.add_argument('-c', '--config', metavar='FILE', help=help)
