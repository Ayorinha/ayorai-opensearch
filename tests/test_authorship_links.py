import re

from pathlib import Path


LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def test_authorship_relative_links_resolve() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "docs" / "AUTHORSHIP.md"
    text = source.read_text(encoding="utf-8")

    relative_links = [
        target
        for target in LINK_PATTERN.findall(text)
        if not target.startswith(("#", "http://", "https://", "mailto:"))
    ]

    assert relative_links
    missing = [
        target
        for target in relative_links
        if not (source.parent / target.split("#", 1)[0]).exists()
    ]
    assert not missing, "broken relative links: " + ", ".join(missing)
