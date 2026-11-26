import os
from collections.abc import Iterator
from contextlib import contextmanager

KEY = "GOODCONF_TEST"


@contextmanager
def env_var(key: str, value: str) -> Iterator[None]:
    os.environ[key] = value
    try:
        yield
    finally:
        del os.environ[key]
