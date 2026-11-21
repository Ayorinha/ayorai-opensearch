"""Synthetic unit tests for human annotator agreement; no real annotations."""

from __future__ import annotations

import hashlib
import json
import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
AGREEMENT: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_agreement.py"))
COMPONENTS: dict[str, Any] = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_components.py"))


def _write_cases(path: Path, case_ids: list[str]) -> Path:
    """Synthetic case inventory: one cited article per case, so each case is a component."""
    path.write_text(
        "".join(
            json.dumps(
                {
                    "case_id": case_id,
                    "cited_article_ids": [f"lei-sintetica:art-{index}"],
                    "label": "SECRET-NOT-READ",
                }
            )
            + "\n"
            for index, case_id in enumerate(case_ids, start=1)
        ),
        encoding="utf-8",
    )
    return path


def test_perfect_agreement_passes_point_estimate_gate_and_reports_matrix() -> None:
    labels = {
        "a": "SUPPORTED",
        "b": "REFUTED",
        "c": "UNVERIFIED",
        "d": "PARTIALLY_SUPPORTED",
        "e": "CONFLICTING",
    }
    result = AGREEMENT["compute_agreement"](labels, labels, iterations=100)
    assert result["cohen_kappa"] == 1.0
    assert result["gate_passed"] is True
    assert result["observed_agreement"] == 1.0
    assert result["confusion_matrix"]["SUPPORTED"]["SUPPORTED"] == 1
    assert result["class_distribution"]["CONFLICTING"]["agreements"] == 1
    assert result["ci95_case_bootstrap"] == [1.0, 1.0]


def test_balanced_cross_disagreement_has_zero_kappa() -> None:
    labels_a = {"a": "SUPPORTED", "b": "SUPPORTED", "c": "REFUTED", "d": "REFUTED"}
    labels_b = {"a": "SUPPORTED", "b": "REFUTED", "c": "SUPPORTED", "d": "REFUTED"}
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=100)
    assert result["cohen_kappa"] == 0.0
    assert result["gate_passed"] is False
    assert result["observed_agreement"] == 0.5


def test_rule_gap_is_excluded_if_either_annotator_marks_it() -> None:
    labels_a = {"a": "SUPPORTED", "b": "REFUTED", "c": "RULE_GAP"}
    labels_b = {"a": "SUPPORTED", "b": "REFUTED", "c": "SUPPORTED"}
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=100)
    assert result["n_eligible"] == 2
    assert result["n_rule_gap_excluded"] == 1
    assert result["rule_gap_excluded_disagreements"] == 1
    assert result["rule_gap_excluded_case_ids"] == ["c"]
    assert result["cohen_kappa"] == 1.0


def test_annotation_ids_must_match_exactly() -> None:
    with pytest.raises(ValueError, match="case IDs differ"):
        AGREEMENT["compute_agreement"]({"a": "SUPPORTED"}, {"b": "SUPPORTED"}, iterations=10)


def test_duplicate_annotation_id_is_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "annotations.jsonl"
    file_path.write_text(
        '{"case_id":"a","label":"SUPPORTED"}\n{"case_id":"a","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case_id"):
        AGREEMENT["load_annotations"](file_path)


def test_bootstrap_interval_is_deterministic() -> None:
    labels_a = {f"case-{i}": "SUPPORTED" if i < 10 else "REFUTED" for i in range(20)}
    labels_b = dict(labels_a)
    labels_b["case-3"] = "REFUTED"
    first = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=250, seed=17)
    second = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=250, seed=17)
    assert first["ci95_case_bootstrap"] == second["ci95_case_bootstrap"]
    assert first["bootstrap"] == second["bootstrap"]


def test_unknown_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid labels"):
        AGREEMENT["compute_agreement"]({"a": "NOT_A_LABEL"}, {"a": "SUPPORTED"}, iterations=10)


@pytest.mark.parametrize("iterations", [0, -1, True, 1.5])
def test_bootstrap_iterations_must_be_positive_integer(iterations: object) -> None:
    with pytest.raises(ValueError, match="iterations must be positive"):
        AGREEMENT["compute_agreement"](
            {"a": "SUPPORTED"}, {"a": "SUPPORTED"}, iterations=iterations
        )


def test_all_rule_gap_pairs_abort_instead_of_returning_a_kappa() -> None:
    labels_a = {"a": "RULE_GAP"}
    labels_b = {"a": "RULE_GAP"}
    with pytest.raises(ValueError, match="no eligible cases remain"):
        AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=10)


def test_kappa_is_undefined_without_marginal_variation_and_does_not_pass_gate() -> None:
    labels = {"a": "SUPPORTED", "b": "SUPPORTED", "c": "SUPPORTED"}
    result = AGREEMENT["compute_agreement"](labels, labels, iterations=100)
    assert result["cohen_kappa"] is None
    assert result["gate_passed"] is False
    assert result["ci95_case_bootstrap"] is None


def test_cli_uses_one_immutable_snapshot_for_metrics_and_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    labels = [
        ("a", "SUPPORTED"),
        ("b", "REFUTED"),
        ("c", "UNVERIFIED"),
        ("d", "PARTIALLY_SUPPORTED"),
        ("e", "CONFLICTING"),
    ]
    original = "".join(
        json.dumps({"case_id": case_id, "label": label}) + "\n" for case_id, label in labels
    ).encode("utf-8")
    replacement = (
        b'{"case_id":"a","label":"SUPPORTED"}\n'
        b'{"case_id":"b","label":"SUPPORTED"}\n'
        b'{"case_id":"c","label":"SUPPORTED"}\n'
        b'{"case_id":"d","label":"SUPPORTED"}\n'
        b'{"case_id":"e","label":"SUPPORTED"}\n'
    )
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    annotation_a.write_bytes(original)
    annotation_b.write_bytes(original)
    output = tmp_path / "agreement.json"
    cases = _write_cases(tmp_path / "cases.jsonl", [case_id for case_id, _ in labels])

    original_read_bytes = Path.read_bytes
    replaced = False

    def read_bytes_with_replacement(path: Path) -> bytes:
        nonlocal replaced
        snapshot = original_read_bytes(path)
        if path == annotation_a and not replaced:
            replaced = True
            annotation_a.write_bytes(replacement)
        return snapshot

    monkeypatch.setattr(Path, "read_bytes", read_bytes_with_replacement)

    assert (
        AGREEMENT["main"](
            [
                "--annotation-a",
                str(annotation_a),
                "--annotation-b",
                str(annotation_b),
                "--cases",
                str(cases),
                "--out",
                str(output),
            ]
        )
        == 0
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["cohen_kappa"] == 1.0
    assert report["inputs"]["annotation_a_sha256"] == hashlib.sha256(original).hexdigest()
    assert report["inputs"]["annotation_b_sha256"] == hashlib.sha256(original).hexdigest()
    replacement_hash = hashlib.sha256(replacement).hexdigest()
    current_hash = hashlib.sha256(annotation_a.read_bytes()).hexdigest()
    assert current_hash == replacement_hash


def test_cli_report_records_exact_annotation_input_hashes(tmp_path: Path) -> None:
    labels = [
        ("a", "SUPPORTED"),
        ("b", "REFUTED"),
        ("c", "UNVERIFIED"),
        ("d", "PARTIALLY_SUPPORTED"),
        ("e", "CONFLICTING"),
    ]
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    content = "".join(
        json.dumps({"case_id": case_id, "label": label}) + "\n" for case_id, label in labels
    )
    annotation_a.write_text(content, encoding="utf-8")
    annotation_b.write_text(content, encoding="utf-8")
    output = tmp_path / "agreement.json"
    cases = _write_cases(tmp_path / "cases.jsonl", [case_id for case_id, _ in labels])

    assert (
        AGREEMENT["main"](
            [
                "--annotation-a",
                str(annotation_a),
                "--annotation-b",
                str(annotation_b),
                "--cases",
                str(cases),
                "--out",
                str(output),
            ]
        )
        == 0
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["gate_passed"] is True
    assert report["bootstrap"]["method"] == "percentile_case_bootstrap"
    assert report["bootstrap"]["iterations"] == 10_000
    assert report["bootstrap"]["seed"] == 20261003
    assert report["bootstrap"]["generator"] == "RGC-PRNG-1"
    assert report["bootstrap"]["percentile"] == "hyndman-fan-type-7"
    assert (
        report["bootstrap"]["valid_replicates"] + report["bootstrap"]["degenerate_replicates"]
        == 10_000
    )
    assert report["inputs"] == {
        "annotation_a_sha256": hashlib.sha256(annotation_a.read_bytes()).hexdigest(),
        "annotation_b_sha256": hashlib.sha256(annotation_b.read_bytes()).hexdigest(),
        "cases_sha256": hashlib.sha256(cases.read_bytes()).hexdigest(),
    }
    assert report["component_bootstrap"]["decision"] == "DEC-022"
    assert report["component_bootstrap"]["iterations"] == 10_000
    assert report["component_bootstrap"]["seed"] == 20261003
    assert report["component_bootstrap"]["stream"] == "dec022-kappa-bootstrap"
    assert report["component_bootstrap"]["component_count"] == 5


@pytest.mark.parametrize(
    ("option", "value"),
    [("--iterations", "20"), ("--seed", "17")],
)
def test_protocol_cli_rejects_noncanonical_bootstrap_overrides(
    tmp_path: Path, option: str, value: str, capsys: pytest.CaptureFixture[str]
) -> None:
    annotation = tmp_path / "annotations.jsonl"
    annotation.write_text('{"case_id":"a","label":"SUPPORTED"}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        AGREEMENT["main"](
            [
                "--annotation-a",
                str(annotation),
                "--annotation-b",
                str(annotation),
                "--cases",
                str(_write_cases(tmp_path / "cases.jsonl", ["a"])),
                "--out",
                str(tmp_path / "agreement.json"),
                option,
                value,
            ]
        )
    assert "unrecognized arguments" in capsys.readouterr().err


def test_bootstrap_uses_rgc_prng_and_type7_percentile() -> None:
    labels_a = {f"c{i}": ("SUPPORTED" if i % 3 else "REFUTED") for i in range(12)}
    labels_b = {f"c{i}": ("SUPPORTED" if i % 4 else "REFUTED") for i in range(12)}
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, iterations=50)
    assert result["bootstrap"]["generator"] == "RGC-PRNG-1"
    assert result["bootstrap"]["percentile"] == "hyndman-fan-type-7"


def test_duplicate_json_object_keys_are_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "annotations.jsonl"
    file_path.write_text(
        '{"case_id":"a","case_id":"attacker","label":"SUPPORTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key 'case_id'"):
        AGREEMENT["load_annotations"](file_path)


def _component_fixture() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Twelve cases in four components; disagreements concentrated in one component."""
    labels_a: dict[str, str] = {}
    labels_b: dict[str, str] = {}
    components: dict[str, str] = {}
    cycle = ("SUPPORTED", "REFUTED", "UNVERIFIED")
    for component in range(4):
        for member in range(3):
            case_id = f"k{component}-{member}"
            label = cycle[(component + member) % 3]
            labels_a[case_id] = label
            labels_b[case_id] = label if component else cycle[(component + member + 1) % 3]
            components[case_id] = f"component:lei-sintetica:art-{component}"
    return labels_a, labels_b, components


def test_component_interval_follows_dec022_and_keeps_case_interval_as_sensitivity() -> None:
    labels_a, labels_b, components = _component_fixture()
    with_components = AGREEMENT["compute_agreement"](
        labels_a, labels_b, component_by_case=components
    )
    reference = COMPONENTS["bootstrap_cohen_kappa_by_component"](labels_a, labels_b, components)
    without = AGREEMENT["compute_agreement"](labels_a, labels_b)

    assert with_components["ci95_component_bootstrap"] == [
        round(value, 6) for value in reference.ci95
    ]
    block = with_components["component_bootstrap"]
    assert block["method"] == "percentile_component_bootstrap"
    assert block["component_count"] == 4
    assert block["valid_replicates"] + block["undefined_replicates"] == 10_000
    assert block["undefined_fraction"] == round(reference.undefined_fraction, 6)
    assert block["unstable"] is reference.unstable
    # The gate and the case-bootstrap sensitivity are unchanged by DEC-022.
    for key in ("cohen_kappa", "gate_passed", "ci95_case_bootstrap", "bootstrap"):
        assert with_components[key] == without[key]
    assert "ci95_component_bootstrap" not in without
    # Clustered disagreement widens the interval relative to case resampling.
    component_width = (
        with_components["ci95_component_bootstrap"][1]
        - with_components["ci95_component_bootstrap"][0]
    )
    case_width = without["ci95_case_bootstrap"][1] - without["ci95_case_bootstrap"][0]
    assert component_width > case_width


def test_component_interval_marks_unstable_when_many_resamples_are_undefined() -> None:
    labels = {"a1": "SUPPORTED", "a2": "SUPPORTED", "b1": "REFUTED"}
    components = {
        "a1": "component:lei-sintetica:art-1",
        "a2": "component:lei-sintetica:art-1",
        "b1": "component:lei-sintetica:art-2",
    }
    result = AGREEMENT["compute_agreement"](labels, labels, component_by_case=components)
    # Half of the two-component resamples hold one class only: kappa is undefined.
    assert result["component_bootstrap"]["undefined_fraction"] > 0.05
    assert result["component_bootstrap"]["unstable"] is True
    assert result["gate_passed"] is True


def test_component_ids_come_only_from_citations(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    rows = [
        {"case_id": "x", "cited_article_ids": ["lei-sintetica:art-1"], "label": "SUPPORTED"},
        {"case_id": "y", "cited_article_ids": ["lei-sintetica:art-1", "lei-sintetica:art-2"]},
        {"case_id": "z", "cited_article_ids": ["lei-sintetica:art-3"]},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    mapping = AGREEMENT["load_component_ids"](path)
    assert mapping["x"] == mapping["y"] != mapping["z"]
    assert set(mapping) == {"x", "y", "z"}


@pytest.mark.parametrize(
    "line",
    [
        '{"case_id":"x"}',
        '{"case_id":"x","cited_article_ids":[]}',
        '{"case_id":"x","cited_article_ids":["Not A Canonical ID"]}',
        '{"case_id":"x","case_id":"y","cited_article_ids":["lei-sintetica:art-1"]}',
    ],
)
def test_invalid_case_inventory_fails_closed(tmp_path: Path, line: str) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        AGREEMENT["load_component_ids"](path)


def test_component_mapping_must_cover_exactly_the_annotated_cases() -> None:
    labels = {"a": "SUPPORTED", "b": "REFUTED"}
    with pytest.raises(ValueError, match="must match exactly"):
        AGREEMENT["compute_agreement"](
            labels, labels, component_by_case={"a": "component:lei-sintetica:art-1"}
        )


def test_component_whose_pairs_are_all_rule_gap_is_not_resampled() -> None:
    # K counts only components with at least one eligible pair (review of #600):
    # a component whose every pair is excluded by RULE_GAP is not drawn.
    labels_a = {"x1": "SUPPORTED", "x2": "REFUTED", "y1": "RULE_GAP", "z1": "SUPPORTED"}
    labels_b = {"x1": "SUPPORTED", "x2": "REFUTED", "y1": "SUPPORTED", "z1": "REFUTED"}
    components = {
        "x1": "component:lei-sintetica:art-1",
        "x2": "component:lei-sintetica:art-1",
        "y1": "component:lei-sintetica:art-2",
        "z1": "component:lei-sintetica:art-3",
    }
    result = AGREEMENT["compute_agreement"](labels_a, labels_b, component_by_case=components)
    assert result["component_bootstrap"]["component_count"] == 2
    assert result["n_eligible"] == 3
    assert result["n_rule_gap_excluded"] == 1
    # The same data without the excluded component gives the same interval.
    reduced = AGREEMENT["compute_agreement"](
        {k: v for k, v in labels_a.items() if k != "y1"},
        {k: v for k, v in labels_b.items() if k != "y1"},
        component_by_case={k: v for k, v in components.items() if k != "y1"},
    )
    assert result["ci95_component_bootstrap"] == reduced["ci95_component_bootstrap"]
