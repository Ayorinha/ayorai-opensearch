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
        json.dumps({"case_id": case_id, "label": label}) + "\n"
        for case_id, label in labels
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

    assert (
        AGREEMENT["main"](
            [
                "--annotation-a",
                str(annotation_a),
                "--annotation-b",
                str(annotation_b),
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
    }


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
