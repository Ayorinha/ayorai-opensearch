from __future__ import annotations

import subprocess
import sys


def test_cli_module_entrypoint_displays_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ayorai_attractor.cli.main", "--help"],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "AYORAI ATTRACTOR OpenSearch CLI" in result.stdout
