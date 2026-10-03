from pathlib import Path

import yaml


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
                stripped = line.strip()
                if stripped.startswith("# ruff: noqa"):
                    offenders.append(f"{path.relative_to(root)}:{line_number}")
    assert not offenders, "file-wide Ruff noqa is forbidden: " + ", ".join(offenders)


def test_citation_cff_is_valid_yaml_and_has_atomic_keywords() -> None:
    root = Path(__file__).resolve().parents[1]
    citation = yaml.safe_load((root / "CITATION.cff").read_text(encoding="utf-8"))
    assert citation["abstract"]
    assert citation["family-names"] if "family-names" in citation else True
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
