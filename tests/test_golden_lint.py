from pathlib import Path
import subprocess
import sys


def test_golden_v0_lint_passes() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / "scripts/lint_golden.py")],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "GOLDEN_LINT: PASS" in result.stdout
