from pathlib import Path

# No file-wide Ruff suppressions are currently justified.
ALLOWED_FILE_WIDE_RUFF_NOQA: dict[str, str] = {}


def test_no_file_wide_ruff_noqa() -> None:
    root = Path(__file__).resolve().parents[1]
    roots = (root / "src", root / "evaluation", root / "tests")
    offenders: list[str] = []
    for directory in roots:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            relative = str(path.relative_to(root))
            allowed_reason = ALLOWED_FILE_WIDE_RUFF_NOQA.get(relative)
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if line.strip().startswith("# ruff: noqa") and allowed_reason is None:
                    offenders.append(f"{relative}:{line_number}")
    assert not offenders, "file-wide Ruff noqa is forbidden: " + ", ".join(offenders)


def test_citation_cff_is_valid_yaml_and_has_atomic_keywords() -> None:
    import yaml

    root = Path(__file__).resolve().parents[1]
    citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    assert citation["abstract"]
    assert citation["authors"][0]["family-names"] == "Ayora"
    assert citation["authors"][0]["given-names"] == "Anderson Leon"
    keywords = citation["keywords"]
    assert len(keywords) == 12
    assert all(isinstance(keyword, str) for keyword in keywords)
    assert {
        "claim verification",
        "fact-checking",
        "hallucination detection",
        "Portuguese",
        "LGPD",
        "auditability",
    }.issubset(keywords)
