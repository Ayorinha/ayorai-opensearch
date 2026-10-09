"""Regression guard: CI concurrency groups must be scoped per ref/PR.

A hard-coded group (e.g. ``-github-workflows-ci-yml-main``) makes every run of a
workflow, across all branches and pull requests, share one group. With
``cancel-in-progress: true`` a new run cancels unrelated runs, so pull requests
can end up with no completed CI evidence.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
GROUP_RE = re.compile(r"^concurrency:\s*\n\s+group:\s*(?P<group>.+)$", re.MULTILINE)


def _workflows_with_concurrency() -> list[tuple[Path, str]]:
    found = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        match = GROUP_RE.search(path.read_text(encoding="utf-8"))
        if match:
            found.append((path, match.group("group").strip()))
    return found


def test_some_workflow_declares_concurrency() -> None:
    assert _workflows_with_concurrency(), "expected at least one workflow with concurrency"


def test_concurrency_groups_are_scoped_per_ref() -> None:
    for path, group in _workflows_with_concurrency():
        assert "${{" in group, f"{path.name}: concurrency group is a literal: {group!r}"
        assert "github.ref" in group, f"{path.name}: concurrency group not scoped by ref: {group!r}"
