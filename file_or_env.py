"""
Transparently load variables from environment or JSON/YAML file.
"""
import json
import logging
import os
import sys

from decimal import Decimal
from distutils.util import strtobool
from typing import TypeVar

log = logging.getLogger(__name__)


# borrowed from https://github.com/theskumar/python-dotenv
def _walk_to_root(path):
    """
    Yield directories starting from the given directory up to the root
    """
    if not os.path.exists(path):
        raise IOError('Starting path not found')

    if os.path.isfile(path):
        path = os.path.dirname(path)

    last_dir = None
    current_dir = os.path.abspath(path)
    while last_dir != current_dir:
        yield current_dir
        parent_dir = os.path.abspath(os.path.join(current_dir, os.path.pardir))
        last_dir, current_dir = current_dir, parent_dir


# borrowed from https://github.com/theskumar/python-dotenv
def find_file(filename, usecwd=False, starting_stack_depth=None):
    """
    Search in increasingly higher folders for the given file
    Returns path to the file if found, or an empty string otherwise
    """
    if usecwd:
        # should work without __file__, e.g. in REPL or IPython notebook
        path = os.getcwd()
    else:
        # try to get filename of where it was called
        try:
            frame_filename = sys._getframe(
                starting_stack_depth).f_back.f_code.co_filename
            path = os.path.dirname(os.path.abspath(frame_filename))
        except AttributeError:
            path = os.getcwd()

    log.debug("Searching for %s starting at %s", filename, path)
    for dirname in _walk_to_root(path):
        check_path = os.path.join(dirname, filename)
        if os.path.exists(check_path):
            return check_path


def _load_config(path: str) -> dict:
    """
    Given a file path, parse it based on its extension (YAML or JSON)
    and return the values as a Python dictionary. JSON is the default if an
    extension can't be determined.
    """
    __, ext = os.path.splitext(path)
    if ext in ['.yaml', '.yml']:
        import yaml
        loader = yaml.safe_load
    else:
        loader = json.load
    with open(path) as f:
        config = loader(f)
    log.info("Loaded config from %s", path)
    return config


CASTS = [int, str, float, list, bool, Decimal]
CastTypes = TypeVar('CastTypes', *CASTS)


class FileOrEnv:
    """
    Dict-like object which abstracts retrieval of values from a JSON file or
    `os.environ`. Environment variables take precedence over JSON.

    The file can be provided as an absolute path or a filename. If a filename
    is provided, it will walk up the filesystem looking for a filename that
    matches, loading the first one that is found.

    Usage:

        config = FileOrEnv('/path/to/env.json')
        # or
        config = FileOrEnv('env.json')
        DEBUG = config.get('DEBUG', 'false', cast=bool)
    """
    def __init__(self, file: str = None):
        """Read config in from file if provided"""
        if file:
            if os.path.isabs(file):
                self.config_file = file
            else:
                self.config_file = find_file(file, starting_stack_depth=1)
        if self.config_file:
            self.config = _load_config(self.config_file)
        else:
            self.config = {}

    def __getitem__(self, item: str):
        """Implements getting item in dict-style"""
        try:
            return os.environ[item]
        except KeyError:
            return self.config[item]

    def __contains__(self, item: str):
        """Implements `key in config`"""
        return item in os.environ or item in self.config

    def get(self, key: str, default: str = None, cast: CastTypes = str):
        """
        Get value from environ (and cast to type). If it isn't defined in the
        environ, retrieve it from the config file.
        """
        if key in os.environ:
            return self.cast(os.environ[key], cast)
        if key in self.config:
            return self.config[key]
        if default is None:
            return default
        return self.cast(default, cast)

    def cast(self, val: str, cast_as: CastTypes):
        """converts string to type requested by `cast_as`"""
        try:
            return getattr(self, 'cast_as_{}'.format(
                cast_as.__name__.lower()))(val)
        except AttributeError:
            return cast_as(val)

    def cast_as_list(self, val: str) -> list:
        """Convert a comma-separated string to a list"""
        return val.split(',')

    def cast_as_bool(self, val: str) -> bool:
        """
        True values are y, yes, t, true, on and 1
        False values are n, no, f, false, off and 0
        Raises ValueError if val is anything else.
        """
        return bool(strtobool(val))
