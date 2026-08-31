"""Regression tests for side-effect-free informational CLI commands."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("argument", ["--help", "--version"])
def test_informational_command_does_not_create_aura_home(
    tmp_path: Path, argument: str
) -> None:
    aura_home = tmp_path / "aura-home"
    env = os.environ.copy()
    env["AURA_HOME"] = str(aura_home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    result = subprocess.run(
        [sys.executable, "-m", "aura_cli.cli.main", argument],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not aura_home.exists()
