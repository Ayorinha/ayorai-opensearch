"""Relative links and anchors in the repository's Markdown must resolve."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
_SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__", ".attractor"}
_LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
_FENCE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
_HEADING = re.compile(r"^#+\s+(.*)$", re.M)
_ANCHOR_DROP = re.compile(r"""[`*_~\[\]()!?:'",.;/\\{}|+=&%$#@^<>—–’“”]""")


def _markdown_files() -> list[Path]:
    return sorted(
        path for path in REPO_ROOT.rglob("*.md") if not _SKIP_PARTS.intersection(path.parts)
    )


def _github_anchor(heading: str) -> str:
    text = re.sub(r"<[^>]+>", "", heading).strip().lower()
    return _ANCHOR_DROP.sub("", text).replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    text = _FENCE.sub("", path.read_text(encoding="utf-8"))
    return {_github_anchor(heading) for heading in _HEADING.findall(text)}


def test_relative_markdown_links_and_anchors_resolve() -> None:
    problems: list[str] = []
    for source in _markdown_files():
        text = _FENCE.sub("", source.read_text(encoding="utf-8"))
        for target in _LINK.findall(text):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path_part, _, anchor = target.partition("#")
            destination = source if not path_part else (source.parent / path_part).resolve()
            relative = source.relative_to(REPO_ROOT)
            if path_part and not destination.exists():
                problems.append(f"{relative}: missing file {target}")
                continue
            if anchor and destination.suffix == ".md" and destination.is_file():
                if anchor.lower() not in _anchors(destination):
                    problems.append(f"{relative}: missing anchor {target}")
    assert not problems, "\n".join(problems)
