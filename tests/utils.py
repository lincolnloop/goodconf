import os
from contextlib import contextmanager

KEY = 'GOODCONF_TEST'


@contextmanager
def env_var(key, value):
    os.environ[key] = value
    try:
        yield
    finally:
        del os.environ[key]
