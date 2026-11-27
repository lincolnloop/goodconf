import os
from collections.abc import Iterator

import pytest

KEPT_ENVIRON_KEYS = {"HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH", "TMPDIR"}


@pytest.fixture(autouse=True)
def isolated_environ(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # pydantic-settings matches env vars to field names case-insensitively, so
    # a developer's DEBUG or SECRET_KEY would leak into config under test.
    for key in list(os.environ):
        if key not in KEPT_ENVIRON_KEYS and not key.startswith("COVERAGE_"):
            monkeypatch.delenv(key)
    kept_keys = set(os.environ)
    yield
    # django_manage exports -C for child processes; drop it before the next test.
    for key in set(os.environ) - kept_keys:
        del os.environ[key]
