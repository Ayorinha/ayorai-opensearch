from fnmatch import fnmatch
from pathlib import Path

PATTERNS = ("golden-v1*", "golden_v1*")
IGNORE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".tox", ".nox", ".venv", "venv", "node_modules", "build", "dist",
    ".attractor", ".hypothesis",
}


def test_hidden_golden_v1_isolation() -> None:
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*"):
        if not path.is_file() or any(part.lower() in IGNORE_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix().lower()
        name = path.name.lower()
        assert not fnmatch(relative, "evals/golden/v1*")
        assert not any(fnmatch(name, pattern) for pattern in PATTERNS)
