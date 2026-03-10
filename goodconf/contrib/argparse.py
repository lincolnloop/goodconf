import argparse

from goodconf import GoodConf


def argparser_add_argument(parser: argparse.ArgumentParser, config: GoodConf) -> None:
    """Adds argument for config to existing argparser"""
    help_text = "Config file."
    cfg = config.model_config
    if cfg.get("file_env_var"):
        help_text += (
            "Can also be configured via the environment variable: "
            f"{cfg['file_env_var']}"
        )
    if default_files := cfg.get("default_files"):
        files_str = ", ".join(default_files)
        help_text += f" Defaults to the first file that exists from [{files_str}]."
    parser.add_argument("-C", "--config", metavar="FILE", help=help_text)
