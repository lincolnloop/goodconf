import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

PROJECTS_DIR = Path(__file__).parent
REPO_DIR = Path(__file__).parents[3]


@pytest.fixture
def manage_py(tmp_path: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the README-shaped project's manage.py with ``tmp_path`` as the cwd."""
    return build_manage_runner(PROJECTS_DIR / "project" / "manage.py", tmp_path)


@pytest.fixture
def manage_py_without_load(
    tmp_path: Path,
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run a project whose settings.py reads config without calling load()."""
    return build_manage_runner(
        PROJECTS_DIR / "project_without_load" / "manage.py", tmp_path
    )


def build_manage_runner(
    manage_path: Path, cwd: Path
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run_manage(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(manage_path), *args],
            capture_output=True,
            check=False,
            cwd=cwd,
            env={**os.environ, "PYTHONPATH": str(REPO_DIR), **env},
            stdin=subprocess.DEVNULL,
            text=True,
            timeout=60,
        )

    return run_manage
