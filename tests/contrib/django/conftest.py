import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

MANAGE_PY = Path(__file__).parent / "project" / "manage.py"
REPO_DIR = Path(__file__).parents[3]


@pytest.fixture
def manage(tmp_path: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the fixture project's manage.py with ``tmp_path`` as the cwd."""
    base_env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"DJANGO_SETTINGS_MODULE", "PROJECT_CONF"}
    }

    def run_manage(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(MANAGE_PY), *args],
            capture_output=True,
            check=False,
            cwd=tmp_path,
            env={**base_env, "PYTHONPATH": str(REPO_DIR), **env},
            text=True,
        )

    return run_manage
