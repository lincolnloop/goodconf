import os

import pytest

KEPT_ENVIRON_KEYS = {"HOME", "LANG", "LC_ALL", "LC_CTYPE", "PATH", "TMPDIR"}


@pytest.fixture(autouse=True)
def isolated_environ(monkeypatch: pytest.MonkeyPatch) -> None:
    # pydantic-settings matches env vars to field names case-insensitively, so
    # a developer's DEBUG or SECRET_KEY would leak into config under test.
    for key in list(os.environ):
        if key not in KEPT_ENVIRON_KEYS and not key.startswith("COVERAGE_"):
            monkeypatch.delenv(key)
