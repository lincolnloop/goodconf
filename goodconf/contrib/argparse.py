import argparse
from .. import GoodConf


def argparser_add_argument(parser: argparse.ArgumentParser, config: GoodConf):
    """Adds argument for config to existing argparser"""
    help = "Config file."
    if config.__config__.file_env_var:
        help += " Can also be configured via the " "environment variable: {}".format(
            config.__config__.file_env_var
        )
    if config.__config__.default_files:
        help += " Defaults to the first file that exists from " "[{}].".format(
            ", ".join(config.__config__.default_files)
        )
    parser.add_argument("-C", "--config", metavar="FILE", help=help)
