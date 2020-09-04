import argparse

from .. import GoodConf


def argparser_add_argument(parser: argparse.ArgumentParser, config: GoodConf):
    """Adds argument for config to existing argparser"""
    help = "Config file."
    if config.__config__.file_env_var:
        help += f" Can also be configured via the environment variable: {config.__config__.file_env_var}"
    if config.__config__.default_files:
        files_str = ", ".join(config.__config__.default_files)
        help += f" Defaults to the first file that exists from [{files_str}]."
    parser.add_argument("-C", "--config", metavar="FILE", help=help)
