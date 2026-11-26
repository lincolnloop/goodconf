import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

KEY = "GOODCONF_TEST"


@contextmanager
def env_var(key: str, value: str) -> Iterator[None]:
    os.environ[key] = value
    try:
        yield
    finally:
        del os.environ[key]


REPO_DIR = Path(__file__).parent.parent
MANAGE_PY = Path(__file__).parent / "contrib" / "django" / "project" / "manage.py"


def run_manage(cwd: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"DJANGO_SETTINGS_MODULE", "EXAMPLEPROJECT_CONF"}
    }
    return subprocess.run(
        [sys.executable, str(MANAGE_PY), *args],
        capture_output=True,
        check=False,
        cwd=cwd,
        env={**base_env, "PYTHONPATH": str(REPO_DIR), **env},
        text=True,
    )
