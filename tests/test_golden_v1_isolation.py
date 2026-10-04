from fnmatch import fnmatch
from pathlib import Path

PATTERNS = ("v1*", "golden-v1*", "golden_v1*")
CACHE_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox"}


def test_hidden_golden_v1_isolation() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*"):
        if not path.is_file() or any(part in CACHE_DIRS for part in path.parts):
            continue
        name = path.name.lower()
        assert not any(fnmatch(name, pattern) for pattern in PATTERNS), path.relative_to(root)
