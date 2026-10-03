from pathlib import Path


def test_no_file_wide_ruff_noqa() -> None:
    root = Path(__file__).resolve().parents[1]
    roots = (root / "src", root / "evaluation", root / "tests")
    offenders: list[str] = []
    for directory in roots:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if line.strip() == "# ruff: noqa":
                    offenders.append(f"{path.relative_to(root)}:{line_number}")
    assert not offenders, "file-wide Ruff noqa is forbidden: " + ", ".join(offenders)
