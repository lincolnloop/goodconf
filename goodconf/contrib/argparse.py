import argparse

from .. import GoodConf


def argparser_add_argument(parser: argparse.ArgumentParser, config: GoodConf):
    """Adds argument for config to existing argparser"""
    help = "Config file."
    cfg = config.model_config
    if cfg.get("file_env_var"):
        help += (
            "Can also be configured via the environment variable: "
            f"{cfg['file_env_var']}"
        )
    if cfg.get("default_files"):
        files_str = ", ".join(cfg["default_files"])
        help += f" Defaults to the first file that exists from [{files_str}]."
    parser.add_argument("-C", "--config", metavar="FILE", help=help)
