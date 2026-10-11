from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_committed_truth_table_is_exactly_generated() -> None:
    root = Path(__file__).resolve().parents[2]
    generated = subprocess.run(
        [sys.executable, str(root / "scripts" / "gen_truth_table.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    committed = (root / "docs" / "judge2" / "TRUTH-TABLE.md").read_text(encoding="utf-8")
    assert committed == generated
