"""RGC evaluation runner — synthetic fixtures only.

No benchmark or pilot case is used here; the only real file read is the
document corpus, to check segmentation offsets and the strict corpus export.
"""

from __future__ import annotations

import ast
import json
import os
import re
import runpy
import subprocess
import sys
import sysconfig
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_eval.py"))
CHECKER = runpy.run_path(str(ROOT / "scripts" / "check_golden_pt.py"))
AGREEMENT = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_agreement.py"))


def _write_agreement_report(path: Path, annotation_a: Path, annotation_b: Path) -> dict[str, Any]:
    report = AGREEMENT["compute_agreement"](
        AGREEMENT["load_annotations"](annotation_a),
        AGREEMENT["load_annotations"](annotation_b),
        iterations=AGREEMENT["DEFAULT_ITERATIONS"],
        seed=AGREEMENT["DEFAULT_SEED"],
    )
    report["inputs"] = {
        "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
        "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


Document = RUNNER["Document"]
Passage = RUNNER["Passage"]

TEXT = (
    "Preâmbulo sintético.\n"
    "Art. 1º A Operadora Fictícia deverá responder reclamações:\n"
    "I - no prazo máximo de 5 (cinco) dias úteis; e,\n"
    "II - por meio eletrônico.\n"
    "Art. 2º O cliente fictício tem direito a cancelar o plano sem multa.\n"
    "§ 1º O cancelamento será efetivado em até 2 (dois) dias.\n"
    "Parágrafo único. A cobrança indevida será devolvida em dobro.\n"
)
DOCS = {
    "sint-1": Document(
        "sint-1", "https://example.test/sint-1", "2026-10-13T00:00:00Z", TEXT, "sintético"
    )
}
DEV_CASES = [{"case_id": "dev-1"}, {"case_id": "dev-2"}, {"case_id": "dev-3"}]
DEV_LABELS = {"dev-1": "SUPPORTED", "dev-2": "SUPPORTED", "dev-3": "REFUTED"}


def _passage_text(passage: Any) -> str:
    return TEXT[passage.start : passage.end]


def _case(case_id: str, claim: str, excerpt: str) -> dict[str, Any]:
    start = TEXT.index(excerpt)
    return {
        "case_id": case_id,
        "claim": claim,
        "bootstrap_cluster_id": f"synthetic:{case_id}",
        "cited_article_ids": [f"synthetic:{case_id}"],
        "evidence": [
            {
                "document_id": "sint-1",
                "excerpt": excerpt,
                "start_offset": start,
                "end_offset": start + len(excerpt),
            }
        ],
    }


def test_segment_by_dispositivo_keeps_exact_offsets() -> None:
    passages = RUNNER["segment"](DOCS["sint-1"])
    texts = [_passage_text(p) for p in passages]
    assert texts == [
        "Preâmbulo sintético.",
        "Art. 1º A Operadora Fictícia deverá responder reclamações:",
        "I - no prazo máximo de 5 (cinco) dias úteis; e,",
        "II - por meio eletrônico.",
        "Art. 2º O cliente fictício tem direito a cancelar o plano sem multa.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        "Parágrafo único. A cobrança indevida será devolvida em dobro.",
    ]
    articles = RUNNER["segment"](DOCS["sint-1"], "artigo")
    assert [_passage_text(p).split("\n")[0] for p in articles] == [
        "Preâmbulo sintético.",
        "Art. 1º A Operadora Fictícia deverá responder reclamações:",
        "Art. 2º O cliente fictício tem direito a cancelar o plano sem multa.",
    ]


def test_segment_real_corpus_is_ordered_and_in_bounds() -> None:
    for document in RUNNER["load_documents"]().values():
        passages = RUNNER["segment"](document)
        assert len(passages) > 1
        previous_end = 0
        for passage in passages:
            assert previous_end <= passage.start < passage.end <= len(document.text)
            assert not document.text[passage.end - 1].isspace()
            previous_end = passage.end


def test_segmentation_loses_no_text_in_real_corpus() -> None:
    # Between consecutive passages (and before/after) only whitespace may remain.
    for document in RUNNER["load_documents"]().values():
        cursor = 0
        for passage in RUNNER["segment"](document):
            assert document.text[cursor : passage.start].strip() == ""
            cursor = passage.end
        assert document.text[cursor:].strip() == ""


def test_bm25_is_deterministic_and_ranks_relevant_passage_first() -> None:
    passages = RUNNER["segment"](DOCS["sint-1"])
    index = RUNNER["BM25Index"](passages, DOCS)
    hits = index.search("O cancelamento será efetivado em até 2 dias.", 2)
    assert _passage_text(hits[0][0]).startswith("§ 1º O cancelamento")
    assert hits == index.search("O cancelamento será efetivado em até 2 dias.", 2)
    assert index.search("Marte vermelho", 3) == []


def test_tokenizer_keeps_numbers_and_drops_function_words() -> None:
    assert RUNNER["tokenize"]("Em até 5 dias para o Consumidor") == ["5", "dias", "consumidor"]


@pytest.mark.parametrize(
    ("claim", "excerpt", "verdict"),
    [
        (
            "O cancelamento será efetivado em até 2 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
            "SUPPORTED",
        ),
        (
            "O cancelamento será efetivado em até 9 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
            "REFUTED",
        ),
        (
            "O cliente tem direito a reembolso por satélite.",
            "II - por meio eletrônico.",
            "UNVERIFIED",
        ),
    ],
)
def test_oracle_prediction_goes_through_judge2(claim: str, excerpt: str, verdict: str) -> None:
    case = _case("s1", claim, excerpt)
    prediction = RUNNER["predict"](claim, RUNNER["oracle_passages"](case, DOCS), DOCS)
    assert prediction["decision_state"] == "DECIDED"
    assert prediction["judge_verdict"] == verdict
    assert len(prediction["output_sha256"]) == 64


def test_oracle_rejects_excerpt_that_does_not_match_offsets() -> None:
    case = _case("s1", "x", "II - por meio eletrônico.")
    case["evidence"][0]["start_offset"] += 1
    with pytest.raises(ValueError, match="excerpt does not match"):
        RUNNER["oracle_passages"](case, DOCS)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda item: item.update(start_offset="1"), "offsets must be integers"),
        (lambda item: item.update(end_offset=True), "offsets must be integers"),
        (lambda item: item.update(document_id="missing-doc"), "unknown evidence document_id"),
        (lambda item: item.update(excerpt=" "), "excerpt must be a non-empty string"),
    ],
)
def test_oracle_rejects_malformed_evidence_metadata(
    mutate: Callable[[dict[str, Any]], None], message: str
) -> None:
    case = _case("bad-evidence", "x", "II - por meio eletrônico.")
    mutate(case["evidence"][0])
    with pytest.raises(ValueError, match=message):
        RUNNER["oracle_passages"](case, DOCS)


def test_oracle_rejects_non_object_evidence_item() -> None:
    case = _case("bad-evidence-item", "x", "II - por meio eletrônico.")
    case["evidence"] = [None]
    with pytest.raises(ValueError, match="each evidence item must be an object"):
        RUNNER["oracle_passages"](case, DOCS)


def test_oracle_rejects_empty_evidence_list() -> None:
    case = _case("empty-evidence", "x", "II - por meio eletrônico.")
    case["evidence"] = []
    with pytest.raises(ValueError, match="evidence must be a non-empty list"):
        RUNNER["oracle_passages"](case, DOCS)


def test_retrieval_failure_abstains_as_unverified() -> None:
    prediction = RUNNER["predict"]("Marte é vermelho.", [], DOCS, retrieval_succeeded=False)
    assert prediction["decision_state"] == "ABSTAINED"
    assert RUNNER["to_label"](prediction, "judge2") == "UNVERIFIED"


def test_label_mapping() -> None:
    to_label = RUNNER["to_label"]
    supported_r3 = {"decision_state": "DECIDED", "judge_verdict": "SUPPORTED", "robustness": "R3"}
    assert to_label(supported_r3, "judge2") == "SUPPORTED"
    assert to_label(supported_r3, "adr002") == "VERIFIED"
    assert to_label({**supported_r3, "robustness": "R1"}, "adr002") == "SUPPORTED"
    invalid = {"decision_state": "INVALID_INPUT", "judge_verdict": None, "robustness": "R0"}
    assert to_label(invalid, "judge2") == RUNNER["INVALID"]


def test_missing_label_vs_present_invalid_prediction_synthetic() -> None:
    """Verify DEC-017 mechanics with synthetic data only; no RGC cases are evaluated."""
    case = _case("synthetic-missing-label", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    with pytest.raises(ValueError, match="without a label"):
        RUNNER["evaluate"](
            [case],
            {},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
        )
    invalid = {"decision_state": "INVALID_INPUT", "judge_verdict": None, "robustness": "R0"}
    assert RUNNER["to_label"](invalid, "judge2") == "INVALID_PREDICTION"
    metrics = RUNNER["compute_metrics"](
        ["SUPPORTED"], ["INVALID_PREDICTION"], "judge2", baseline_label="SUPPORTED", iterations=20
    )
    assert metrics["n"] == 1
    assert metrics["invalid_predictions"] == 1
    assert metrics["system"]["accuracy"] == 0.0


def test_article_cluster_bootstrap_is_deterministic_and_distinct_from_case_bootstrap() -> None:
    gold = ["SUPPORTED"] * 4 + ["REFUTED"] * 4
    predicted = ["SUPPORTED"] * 8
    clusters = ["art:1"] * 4 + ["art:2"] * 4
    clustered = RUNNER["bootstrap_ci_by_cluster"](gold, predicted, clusters, iterations=500)
    repeated = RUNNER["bootstrap_ci_by_cluster"](gold, predicted, clusters, iterations=500)
    case_level = RUNNER["bootstrap_ci"](gold, predicted, iterations=500)
    assert clustered == repeated
    assert clustered["accuracy"] == [0.0, 1.0]
    assert clustered["accuracy"] != case_level["accuracy"]


@pytest.mark.parametrize("iterations", [0, -1, True, 1.5])
def test_bootstrap_rejects_nonpositive_or_noninteger_iterations(iterations: object) -> None:
    with pytest.raises(ValueError, match="iterations must be positive"):
        RUNNER["bootstrap_ci"](["SUPPORTED"], ["SUPPORTED"], iterations=iterations)
    with pytest.raises(ValueError, match="iterations must be positive"):
        RUNNER["bootstrap_ci_by_cluster"](
            ["SUPPORTED"], ["SUPPORTED"], ["art:1"], iterations=iterations
        )


def test_case_bootstrap_rejects_mismatched_and_empty_inputs() -> None:
    with pytest.raises(ValueError, match="equal lengths"):
        RUNNER["bootstrap_ci"](["SUPPORTED"], [], iterations=10)
    with pytest.raises(ValueError, match="at least one case"):
        RUNNER["bootstrap_ci"]([], [], iterations=10)


@pytest.mark.parametrize(
    "fields_to_remove",
    [
        ("bootstrap_cluster_id", "cited_article_ids"),
        ("bootstrap_cluster_id",),
        ("cited_article_ids",),
    ],
)
def test_development_partition_allows_omitted_optional_id_fields(
    fields_to_remove: tuple[str, ...],
) -> None:
    case = _case("optional-dev-ids", "O cliente fictício pode cancelar.", "Art. 2º")
    for field in fields_to_remove:
        case.pop(field)
    result = RUNNER["evaluate"](
        [case],
        {"optional-dev-ids": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=10,
    )
    assert result["metrics"]["n"] == 1


def test_development_partition_rejects_noncanonical_bootstrap_cluster_id() -> None:
    case = _case("invalid-dev-cluster", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "Article:2"
    with pytest.raises(ValueError, match="canonical article ID"):
        RUNNER["evaluate"](
            [case],
            {"invalid-dev-cluster": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_development_partition_rejects_noncanonical_cited_article_id() -> None:
    case = _case("invalid-dev-citation", "O cliente fictício pode cancelar.", "Art. 2º")
    case["cited_article_ids"] = ["Article:2"]
    with pytest.raises(ValueError, match="canonical article ID"):
        RUNNER["evaluate"](
            [case],
            {"invalid-dev-citation": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_development_partition_rejects_cluster_not_in_citations() -> None:
    case = _case("dev-cluster-mismatch", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "synthetic:other"
    case["cited_article_ids"] = ["synthetic:dev-cluster-mismatch"]
    with pytest.raises(ValueError, match="must be present in cited_article_ids"):
        RUNNER["evaluate"](
            [case],
            {"dev-cluster-mismatch": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_development_partition_rejects_bundle_member_absent_from_citations() -> None:
    case = _case("dev-bundle-mismatch", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "bundle:synthetic:a+synthetic:b"
    case["cited_article_ids"] = ["synthetic:a"]
    with pytest.raises(ValueError, match="absent from cited_article_ids"):
        RUNNER["evaluate"](
            [case],
            {"dev-bundle-mismatch": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_development_pilot_validates_supplied_ids_before_rule_gap_exclusion() -> None:
    case = _case("invalid-pilot-id", "O cliente fictício pode cancelar.", "Art. 2º")
    case["cited_article_ids"] = ["Article:2"]
    with pytest.raises(ValueError, match="canonical article ID"):
        RUNNER["evaluate"](
            [case],
            {"invalid-pilot-id": "RULE_GAP"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
            pilot_mode=True,
        )


def test_hidden_partition_rejects_missing_bootstrap_cluster_id() -> None:
    case = _case("no-cluster", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    case.pop("bootstrap_cluster_id")
    with pytest.raises(ValueError, match="bootstrap_cluster_id"):
        RUNNER["evaluate"](
            [case],
            {"no-cluster": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_rejects_noncanonical_multi_article_bundle() -> None:
    case = _case("bad-bundle", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "bundle:art-2+art-1"
    with pytest.raises(ValueError, match="unique, sorted IDs"):
        RUNNER["evaluate"](
            [case],
            {"bad-bundle": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_rejects_missing_cited_article_ids() -> None:
    case = _case("missing-citations", "O cliente fictício pode cancelar.", "Art. 2º")
    case.pop("cited_article_ids")
    with pytest.raises(ValueError, match="cited_article_ids is required"):
        RUNNER["evaluate"](
            [case],
            {"missing-citations": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_rejects_cluster_not_in_cited_article_ids() -> None:
    case = _case("cluster-not-cited", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "art:principal"
    case["cited_article_ids"] = ["art:other"]
    with pytest.raises(ValueError, match="must be present in cited_article_ids"):
        RUNNER["evaluate"](
            [case],
            {"cluster-not-cited": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_rejects_bundle_member_not_cited() -> None:
    case = _case("bundle-not-cited", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "bundle:art-1+art-2"
    case["cited_article_ids"] = ["art-1", "art-3"]
    with pytest.raises(ValueError, match="absent from cited_article_ids"):
        RUNNER["evaluate"](
            [case],
            {"bundle-not-cited": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_allows_bundle_subset_of_complete_citation_list() -> None:
    case = _case("bundle-citation-subset", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "bundle:art-1+art-2"
    case["cited_article_ids"] = ["art-1", "art-2", "art-3"]
    result = RUNNER["evaluate"](
        [case],
        {"bundle-citation-subset": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
        partition="hidden",
    )
    assert result["metrics"]["bootstrap_provenance"]["cluster_count"] == 1


@pytest.mark.parametrize(
    "cited_article_ids",
    [
        "art-1",
        [],
        ["art-1", "art-1"],
        ["art-1", ""],
        ["art-1", 2],
    ],
)
def test_hidden_partition_rejects_malformed_cited_article_ids(
    cited_article_ids: Any,
) -> None:
    case = _case("malformed-citations", "O cliente fictício pode cancelar.", "Art. 2º")
    case["bootstrap_cluster_id"] = "art-1"
    case["cited_article_ids"] = cited_article_ids
    with pytest.raises(ValueError, match="cited_article_ids must be"):
        RUNNER["evaluate"](
            [case],
            {"malformed-citations": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_hidden_partition_reports_component_primary_and_sensitivity_ci() -> None:
    first = _case("cluster-case-1", "A Operadora Fictícia deverá responder.", "Art. 1º")
    second = _case("cluster-case-2", "O cliente fictício pode cancelar.", "Art. 2º")
    first["bootstrap_cluster_id"] = "art:regra-1"
    second["bootstrap_cluster_id"] = "art:regra-1"
    first["cited_article_ids"] = ["art:regra-1"]
    second["cited_article_ids"] = ["art:regra-1"]
    result = RUNNER["evaluate"](
        [first, second],
        {"cluster-case-1": "SUPPORTED", "cluster-case-2": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
        partition="hidden",
    )
    metrics = result["metrics"]
    assert metrics["bootstrap_provenance"]["primary_unit"] == "component"
    assert metrics["bootstrap_provenance"]["sensitivity_units"] == ["article_cluster", "case"]
    assert metrics["bootstrap_provenance"]["cluster_count"] == 1
    assert metrics["bootstrap_provenance"]["component_count"] == 1
    assert "system_ci95_article_cluster" in metrics
    assert "system_ci95_case_bootstrap" in metrics
    primary = metrics["primary_criterion"]
    assert primary["test"] == "sign_flip_by_component"
    assert primary["ci_method"] == "component_bootstrap"
    assert "mcnemar_p_below_0_05" not in primary
    assert primary["significance_below_005_possible"] is False  # K = 1
    assert primary["h1_supported"] is False
    assert metrics["sign_flip"]["component_count"] == 1
    assert metrics["mcnemar"]["role"] == "sensitivity"


def test_metrics_match_hand_computation() -> None:
    gold = ["SUPPORTED", "SUPPORTED", "SUPPORTED", "REFUTED", "UNVERIFIED"]
    pred = ["SUPPORTED", "SUPPORTED", "REFUTED", "REFUTED", RUNNER["INVALID"]]
    assert RUNNER["accuracy"](gold, pred) == pytest.approx(3 / 5)
    assert RUNNER["balanced_accuracy"](gold, pred) == pytest.approx((2 / 3 + 1 + 0) / 3)
    # F1: SUPPORTED 0.8, REFUTED 2/3, UNVERIFIED 0, INVALID_PREDICTION 0.
    assert RUNNER["macro_f1"](gold, pred) == pytest.approx((0.8 + 2 / 3 + 0 + 0) / 4)
    metrics = RUNNER["compute_metrics"](
        gold, pred, "judge2", baseline_label="SUPPORTED", iterations=200
    )
    assert metrics["baseline_primary"]["label"] == "SUPPORTED"
    assert metrics["baseline_primary"]["accuracy"] == pytest.approx(0.6)
    assert metrics["invalid_predictions"] == 1
    assert metrics["absent_gold_states"] == ["PARTIALLY_SUPPORTED", "CONFLICTING"]
    assert metrics["mcnemar"]["system_right_baseline_wrong"] == 1
    assert metrics["mcnemar"]["system_wrong_baseline_right"] == 1
    assert metrics["primary_criterion"]["h1_supported"] is False
    low, high = metrics["system_ci95"]["accuracy"]
    assert 0.0 <= low <= 0.6 <= high <= 1.0
    assert metrics == RUNNER["compute_metrics"](
        gold, pred, "judge2", baseline_label="SUPPORTED", iterations=200
    )


def test_h1_decision_uses_unrounded_values() -> None:
    # 7 of 10 right vs a 6-of-10 baseline: margin is exactly 10 pp, which binary
    # floating point represents as 0.0999...; it must still count as >= 10 pp.
    gold = ["SUPPORTED"] * 6 + ["REFUTED"] * 4
    pred = ["SUPPORTED"] * 6 + ["REFUTED"] + ["SUPPORTED"] * 3
    metrics = RUNNER["compute_metrics"](
        gold, pred, "judge2", baseline_label="SUPPORTED", iterations=50
    )
    assert metrics["primary_criterion"]["margin_at_least_10pp"] is True
    # A margin of 9.999995 pp rounds to 0.1 at 6 decimals but must not pass.
    gold = ["SUPPORTED"] * 6 + ["REFUTED"] * 4
    compute = RUNNER["compute_metrics"]
    original = RUNNER["METRICS"]["accuracy"]
    try:
        RUNNER["METRICS"]["accuracy"] = lambda g, p: 0.6 if len(set(p)) == 1 else 0.69999995
        metrics = compute(gold, pred, "judge2", baseline_label="SUPPORTED", iterations=10)
    finally:
        RUNNER["METRICS"]["accuracy"] = original
    assert metrics["system"]["accuracy"] == 0.7
    assert metrics["primary_criterion"]["margin_at_least_10pp"] is False


def test_primary_baseline_b_uses_development_partition_not_evaluation_gold() -> None:
    gold = ["REFUTED", "REFUTED", "SUPPORTED"]
    pred = ["SUPPORTED", "SUPPORTED", "SUPPORTED"]
    metrics = RUNNER["compute_metrics"](
        gold, pred, "judge2", baseline_label="SUPPORTED", iterations=20
    )
    assert metrics["baseline_primary"]["name"] == "B"
    assert metrics["baseline_primary"]["label"] == "SUPPORTED"
    assert metrics["baseline_primary"]["accuracy"] == pytest.approx(1 / 3)
    assert metrics["baseline_descriptive"]["name"] == "A"
    assert metrics["baseline_descriptive"]["label"] == "REFUTED"
    assert metrics["baseline_descriptive"]["accuracy"] == pytest.approx(2 / 3)
    assert metrics["primary_criterion"]["baseline"] == "B"
    assert metrics["mcnemar"]["baseline"] == "B"


def test_evaluate_derives_baseline_b_from_development_partition() -> None:
    cases = [
        _case(
            "eval-1",
            "O cancelamento será efetivado em até 2 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        ),
        _case(
            "eval-2",
            "O cliente tem direito a cancelar o plano sem multa.",
            "Art. 2º O cliente fictício tem direito a cancelar o plano sem multa.",
        ),
        _case(
            "eval-3",
            "O cancelamento será efetivado em até 9 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        ),
    ]
    labels = {"eval-1": "SUPPORTED", "eval-2": "SUPPORTED", "eval-3": "REFUTED"}
    development_labels = {
        "dev-a": "REFUTED",
        "dev-b": "REFUTED",
        "dev-c": "SUPPORTED",
    }
    result = RUNNER["evaluate"](
        cases,
        labels,
        DOCS,
        development_cases=[
            {"case_id": "dev-a"},
            {"case_id": "dev-b"},
            {"case_id": "dev-c"},
        ],
        development_labels=development_labels,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
    )
    assert result["metrics"]["baseline_primary"]["label"] == "REFUTED"
    assert result["metrics"]["baseline_primary"]["accuracy"] == pytest.approx(1 / 3)
    assert result["metrics"]["baseline_descriptive"]["label"] == "SUPPORTED"
    assert result["metrics"]["baseline_descriptive"]["accuracy"] == pytest.approx(2 / 3)


def test_development_baseline_rejects_empty_and_invalid_labels() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        RUNNER["development_baseline_label"]({}, "judge2")
    with pytest.raises(ValueError, match="outside vocabulary"):
        RUNNER["development_baseline_label"]({"dev-1": "RULE_GAP"}, "judge2")


def test_evaluate_requires_complete_development_labels() -> None:
    case = _case(
        "eval-1",
        "O cancelamento será efetivado em até 2 dias.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
    )
    with pytest.raises(ValueError, match="cases/labels mismatch"):
        RUNNER["evaluate"](
            [case],
            {"eval-1": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels={"dev-1": "SUPPORTED", "dev-2": "SUPPORTED"},
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_evaluate_rejects_duplicate_development_case_ids() -> None:
    case = _case(
        "eval-1",
        "O cancelamento será efetivado em até 2 dias.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
    )
    with pytest.raises(ValueError, match="duplicate case in development partition"):
        RUNNER["evaluate"](
            [case],
            {"eval-1": "SUPPORTED"},
            DOCS,
            development_cases=[
                {"case_id": "dev-1"},
                {"case_id": "dev-1"},
            ],
            development_labels={"dev-1": "SUPPORTED"},
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_evaluate_rejects_labels_without_development_cases() -> None:
    case = _case(
        "eval-1",
        "O cancelamento será efetivado em até 2 dias.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
    )
    with pytest.raises(ValueError, match="cases/labels mismatch"):
        RUNNER["evaluate"](
            [case],
            {"eval-1": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels={**DEV_LABELS, "dev-extra": "REFUTED"},
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_evaluate_rejects_development_evaluation_overlap() -> None:
    case = _case(
        "dev-1",
        "O cancelamento será efetivado em até 2 dias.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
    )
    with pytest.raises(ValueError, match="partition overlap"):
        RUNNER["evaluate"](
            [case],
            {"dev-1": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


def test_majority_tie_breaks_by_vocabulary_order() -> None:
    assert RUNNER["majority_label"](["REFUTED", "SUPPORTED"], "judge2") == "SUPPORTED"


def test_evaluate_requires_complete_labels_without_rule_gap() -> None:
    cases = [
        _case(
            "s1",
            "O cancelamento será efetivado em até 2 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        ),
        _case(
            "s2",
            "O cancelamento será efetivado em até 9 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        ),
    ]
    labels = {"s1": "SUPPORTED", "s2": "REFUTED"}
    for mode in ("oracle", "retrieval"):
        result = RUNNER["evaluate"](
            cases,
            labels,
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode=mode,
            vocabulary="judge2",
            iterations=100,
        )
        assert result["excluded"] == []
        assert [row["predicted"] for row in result["cases"]] == ["SUPPORTED", "REFUTED"]
        assert result["decision_states"] == {"DECIDED": 2}
    with pytest.raises(ValueError, match="unknown cases"):
        RUNNER["evaluate"](
            cases,
            {**labels, "s9": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    with pytest.raises(ValueError, match="duplicate case"):
        RUNNER["evaluate"](
            [*cases, cases[0]],
            labels,
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    with pytest.raises(ValueError, match="without a label"):
        RUNNER["evaluate"](
            cases,
            {"s1": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize("partition", ["development", "hidden"])
def test_evaluate_rejects_rule_gap_in_every_definitive_partition(partition: str) -> None:
    case = _case("definitive-rule-gap", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    with pytest.raises(ValueError, match="RULE_GAP is prohibited in every definitive partition"):
        RUNNER["evaluate"](
            [case],
            {"definitive-rule-gap": "RULE_GAP"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
            partition=partition,
        )


def test_rule_gap_policy_requires_explicit_pilot_mode() -> None:
    validate = RUNNER["_validate_rule_gap_policy"]
    validate("RULE_GAP", pilot_mode=True, partition="development")
    for pilot_mode, partition in (
        (False, "development"),
        (False, "hidden"),
        (True, "hidden"),
    ):
        with pytest.raises(ValueError, match="only in explicit pilot mode"):
            validate("RULE_GAP", pilot_mode=pilot_mode, partition=partition)


def test_evaluate_reports_abstentions_mapped_to_unverified() -> None:
    cases = [
        _case(
            "s1",
            "O cancelamento será efetivado em até 2 dias.",
            "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
        )
    ]
    module_globals = RUNNER["evaluate"].__globals__
    original = module_globals["predict"]

    def abstaining_predict(*args: object, **kwargs: object) -> dict[str, object]:
        prediction = dict(original(*args, **kwargs))
        prediction.update(decision_state="ABSTAINED", verdict=None)
        return prediction

    module_globals["predict"] = abstaining_predict
    try:
        result = RUNNER["evaluate"](
            cases,
            {"s1": "UNVERIFIED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    finally:
        module_globals["predict"] = original
    assert result["decision_states"] == {"ABSTAINED": 1}
    assert result["cases"][0]["predicted"] == "UNVERIFIED"


def test_labels_outside_vocabulary_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text(json.dumps({"case_id": "s1", "verdict": "VERIFIED"}) + "\n")
    with pytest.raises(ValueError, match="not in vocabulary"):
        RUNNER["load_labels"](path, "judge2")
    assert RUNNER["load_labels"](path, "adr002") == {"s1": "VERIFIED"}


def test_strict_corpus_export_is_accepted_by_golden_checker(tmp_path: Path) -> None:
    out = tmp_path / "corpus.jsonl"
    assert RUNNER["main"](["export-corpus", "--out", str(out)]) == 0
    corpus, errors = CHECKER["_read_corpus"](out)
    assert errors == []
    assert set(corpus) == set(RUNNER["load_documents"]())


def test_cli_run_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # This test exercises report serialization with a synthetic freeze attestation;
    # the real repository protocol intentionally remains unfrozen.
    globals_ = RUNNER["main"].__globals__
    # This test targets report serialization and synthetic approvals; the
    # separate subprocess test below exercises the hermetic interpreter boundary.
    monkeypatch.setitem(globals_, "_run_evaluation", RUNNER["_run_evaluation_in_process"])
    monkeypatch.setitem(globals_, "_git_commit", lambda: "f" * 40)
    monkeypatch.setitem(globals_, "_worktree_clean", lambda: True)
    repository_root = RUNNER["ROOT"]
    synthetic_root = tmp_path / "synthetic-checkout"
    freeze_relatives = (
        "docs/eval/PROTOCOL-GOLDEN-V1.md",
        "docs/eval/PREREGISTRATION-RGC-v1.md",
        "docs/eval/RUNNER-RGC-v1.md",
        "docs/eval/PROTOCOL-FREEZE.json",
        "evals/ptbr/rgc_eval.py",
        *RUNNER["RUNNER_DEPENDENCIES"],
    )
    for relative in freeze_relatives:
        target = synthetic_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative.endswith("judge-2.0.0.json"):
            target.write_bytes((repository_root / relative).read_bytes())
        else:
            target.write_text(f"# synthetic {relative}\n", encoding="utf-8")
    monkeypatch.setitem(globals_, "ROOT", synthetic_root)
    dependency_hashes = {
        relative: RUNNER["_sha256"](synthetic_root / relative)
        for relative in RUNNER["RUNNER_DEPENDENCIES"]
    }
    freeze_attestation = {
        "manifest_sha256": "a" * 64,
        "protocol_sha256": "b" * 64,
        "preregistration_sha256": "c" * 64,
        "runner_spec_sha256": "d" * 64,
        "runner_code_sha256": RUNNER["_sha256"](synthetic_root / "evals/ptbr/rgc_eval.py"),
        "runner_dependencies_sha256": dependency_hashes,
        "runner_version": RUNNER["RUNNER_VERSION"],
        "approved_by": "Synthetic test approver",
        "approved_at": "2026-10-21",
    }
    monkeypatch.setitem(globals_, "validate_protocol_freeze", lambda **_: freeze_attestation)
    documents = tmp_path / "docs.jsonl"
    documents.write_text(
        json.dumps(
            {
                "source_id": "sint-1",
                "source_url": "https://example.test/sint-1",
                "source_license": "sintético",
                "retrieved_at": "2026-10-13T00:00:00Z",
                "text": TEXT,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        "\n".join(
            json.dumps(case, ensure_ascii=False)
            for case in (
                _case(
                    "s1",
                    "O cancelamento será efetivado em até 2 dias.",
                    "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
                ),
                _case(
                    "s2",
                    "A Operadora deve responder em até 9 dias úteis.",
                    "I - no prazo máximo de 5 (cinco) dias úteis;",
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"case_id": "s1", "verdict": "SUPPORTED"},
                {"case_id": "s2", "verdict": "REFUTED"},
            )
        )
        + "\n",
        encoding="utf-8",
    )
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    annotation_rows = (
        {"case_id": "s1", "label": "SUPPORTED"},
        {"case_id": "s2", "label": "REFUTED"},
    )
    annotation_a.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8"
    )
    annotation_b.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n", encoding="utf-8"
    )
    agreement_report = tmp_path / "agreement.json"
    _write_agreement_report(agreement_report, annotation_a, annotation_b)
    adjudication_record = tmp_path / "adjudication.md"
    adjudication_record.write_text("Synthetic test only; no real annotations.\n", encoding="utf-8")
    annotation_approval = tmp_path / "annotation-approval.json"
    annotation_approval.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "APPROVED",
                "approved_by": "Synthetic test approver",
                "approved_at": "2026-10-21",
                "cases_sha256": RUNNER["_sha256"](cases),
                "labels_sha256": RUNNER["_sha256"](labels),
                "agreement_report_sha256": RUNNER["_sha256"](agreement_report),
                "adjudication_record_sha256": RUNNER["_sha256"](adjudication_record),
                "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                "cohen_kappa": 1.0,
            }
        ),
        encoding="utf-8",
    )
    development_cases = tmp_path / "development-cases.jsonl"
    development_cases.write_text(
        "\n".join(json.dumps({"case_id": case_id}) for case_id in ("dev-1", "dev-2", "dev-3"))
        + "\n"
    )
    development_labels = tmp_path / "development-labels.jsonl"
    development_labels.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                {"case_id": "dev-1", "verdict": "SUPPORTED"},
                {"case_id": "dev-2", "verdict": "SUPPORTED"},
                {"case_id": "dev-3", "verdict": "REFUTED"},
            )
        )
        + "\n"
    )
    approval_data = json.loads(annotation_approval.read_text(encoding="utf-8"))
    approval_data["development_cases_sha256"] = RUNNER["_sha256"](development_cases)
    approval_data["development_labels_sha256"] = RUNNER["_sha256"](development_labels)
    annotation_approval.write_text(json.dumps(approval_data), encoding="utf-8")
    out = tmp_path / "report.json"
    argv = [
        "run",
        str(cases),
        "--labels",
        str(labels),
        "--annotation-a",
        str(annotation_a),
        "--annotation-b",
        str(annotation_b),
        "--agreement-report",
        str(agreement_report),
        "--annotation-approval",
        str(annotation_approval),
        "--adjudication-record",
        str(adjudication_record),
        "--development-cases",
        str(development_cases),
        "--development-labels",
        str(development_labels),
        "--documents",
        str(documents),
        "--mode",
        "retrieval",
        "--partition",
        "hidden",
        "--out",
        str(out),
    ]
    # If the runner ignores its captured rule file, adjudication would try this
    # deliberately missing import-time path and fail. The run must redirect Judge 2.0
    # to the immutable snapshot and restore the prior module setting afterwards.
    missing_rules = tmp_path / "must-not-be-read.json"
    monkeypatch.setattr(RUNNER["judge2_module"], "_RULES_PATH", missing_rules)
    code = RUNNER["main"](argv)
    assert code == 0
    assert RUNNER["judge2_module"]._RULES_PATH == missing_rules
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["runner_version"] == "rgc-eval/0.12.0"
    assert set(report["runtime_dependencies"]) == {"pydantic", "pydantic-core", "rfc8785"}
    assert all(
        isinstance(value, str) and value for value in report["runtime_dependencies"].values()
    )
    assert report["protocol_freeze"]["approved_by"] == "Synthetic test approver"
    assert report["protocol_freeze"]["protocol_sha256"] == "b" * 64
    recorded_runner_sha256 = report["protocol_freeze"]["runner_code_sha256"]
    assert recorded_runner_sha256 == freeze_attestation["runner_code_sha256"]
    assert report["annotation_approval"]["approved_by"] == "Synthetic test approver"
    assert report["annotation_approval"]["cohen_kappa"] == 1.0
    assert report["metrics"]["system"]["accuracy"] == 1.0
    assert report["config"]["mode"] == "retrieval"
    # The recorded configuration must describe the methods actually used (Emenda 11).
    assert report["config"]["bootstrap"]["primary_unit"] == "component"
    assert report["config"]["bootstrap"]["sensitivity_units"] == ["article_cluster", "case"]
    assert report["config"]["h1_test"] == "sign_flip_by_component"
    assert (
        report["config"]["bootstrap"]["primary_unit"]
        == report["metrics"]["bootstrap_provenance"]["primary_unit"]
    )
    # E5: the run manifest binds the exact report bytes, inputs, config and approvals.
    manifest_path = out.with_name(out.name + ".manifest.json")
    manifest = RUNNER["verify_run_manifest"](
        manifest_path,
        out,
        input_files={
            "cases_sha256": cases,
            "labels_sha256": labels,
            "development_cases_sha256": development_cases,
            "development_labels_sha256": development_labels,
            "documents_sha256": documents,
            "annotation_a_sha256": annotation_a,
            "annotation_b_sha256": annotation_b,
            "agreement_report_sha256": agreement_report,
            "annotation_approval_sha256": annotation_approval,
            "adjudication_record_sha256": adjudication_record,
        },
    )
    assert manifest["schema"] == "rgc-run-manifest/1"
    assert (manifest["git_commit"], manifest["worktree_clean"]) == ("f" * 40, True)
    assert manifest["partition"] == "hidden"
    assert manifest["protocol_freeze_manifest_sha256"] == "a" * 64
    assert (
        manifest["annotation_approval_manifest_sha256"]
        == (report["annotation_approval"]["manifest_sha256"])
    )
    assert manifest["report"]["sha256"] == RUNNER["_sha256"](out)
    # Any change to the report after the run is detected.
    tampered = json.loads(out.read_text(encoding="utf-8"))
    tampered["metrics"]["system"]["accuracy"] = 0.5
    out.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="report bytes differ"):
        RUNNER["verify_run_manifest"](manifest_path, out)
    # Never overwrite: a second run to the same --out is refused and nothing changes.
    before = (out.read_bytes(), manifest_path.read_bytes())
    assert RUNNER["main"](argv) == 2
    assert (out.read_bytes(), manifest_path.read_bytes()) == before
    # A run whose manifest cannot be written leaves neither report nor manifest behind.
    failed_out = tmp_path / "failed.json"
    failed_argv = [*argv[:-1], str(failed_out)]

    def failing_manifest(*_: object, **__: object) -> dict[str, object]:
        raise ValueError("synthetic manifest failure")

    monkeypatch.setitem(RUNNER["main"].__globals__, "build_run_manifest", failing_manifest)
    assert RUNNER["main"](failed_argv) == 2
    assert not failed_out.exists()
    assert not failed_out.with_name("failed.json.manifest.json").exists()
    assert not list(tmp_path.glob(".failed.json*"))
    # The same holds when the manifest is written but fails its own verification.
    monkeypatch.setitem(
        RUNNER["main"].__globals__, "build_run_manifest", RUNNER["build_run_manifest"]
    )

    def failing_verification(*_: object, **__: object) -> dict[str, object]:
        raise ValueError("synthetic verification failure")

    monkeypatch.setitem(RUNNER["main"].__globals__, "verify_run_manifest", failing_verification)
    assert RUNNER["main"](failed_argv) == 2
    assert not failed_out.exists()
    assert not failed_out.with_name("failed.json.manifest.json").exists()
    assert report["metrics"]["baseline_primary"]["label"] == "SUPPORTED"
    assert report["metrics"]["baseline_descriptive"]["label"] == "SUPPORTED"
    assert report["baseline_provenance"]["primary"] == "B"
    assert len(report["inputs"]["cases_sha256"]) == 64
    assert len(report["inputs"]["development_cases_sha256"]) == 64
    assert len(report["inputs"]["development_labels_sha256"]) == 64


def test_annotation_approval_rejects_failed_human_agreement(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    labels.write_text("{}\n", encoding="utf-8")
    annotation_a.write_text(
        json.dumps({"case_id": "case-1", "label": "SUPPORTED"}) + "\n", encoding="utf-8"
    )
    annotation_b.write_text(
        json.dumps({"case_id": "case-1", "label": "SUPPORTED"}) + "\n", encoding="utf-8"
    )
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    development_cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    agreement_data = _write_agreement_report(agreement, annotation_a, annotation_b)
    approval.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "APPROVED",
                "approved_by": "Synthetic approver",
                "approved_at": "2026-10-21",
                "cases_sha256": "0" * 64,
                "labels_sha256": "0" * 64,
                "development_cases_sha256": "0" * 64,
                "development_labels_sha256": "0" * 64,
                "agreement_report_sha256": "0" * 64,
                "adjudication_record_sha256": "0" * 64,
                "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                "cohen_kappa": agreement_data["cohen_kappa"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="human annotator agreement gate did not pass"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )


def test_annotation_approval_binds_final_labels_hash(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text(
        "\n".join(json.dumps({"case_id": case_id}) for case_id in ("case-1", "case-2")) + "\n",
        encoding="utf-8",
    )
    labels.write_text("{}\n", encoding="utf-8")
    annotation_rows = (
        {"case_id": "case-1", "label": "SUPPORTED"},
        {"case_id": "case-2", "label": "REFUTED"},
    )
    annotation_a.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n",
        encoding="utf-8",
    )
    annotation_b.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n",
        encoding="utf-8",
    )
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    development_cases.write_text(json.dumps({"case_id": "case-1"}) + "\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    _write_agreement_report(agreement, annotation_a, annotation_b)
    approval.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "APPROVED",
                "approved_by": "Synthetic approver",
                "approved_at": "2026-10-21",
                "cases_sha256": RUNNER["_sha256"](cases),
                "labels_sha256": "0" * 64,
                "development_cases_sha256": RUNNER["_sha256"](development_cases),
                "development_labels_sha256": RUNNER["_sha256"](development_labels),
                "agreement_report_sha256": RUNNER["_sha256"](agreement),
                "adjudication_record_sha256": RUNNER["_sha256"](adjudication),
                "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
                "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
                "cohen_kappa": 1.0,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="labels_sha256 differs from approval manifest"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )

    manifest = json.loads(approval.read_text(encoding="utf-8"))
    manifest["labels_sha256"] = RUNNER["_sha256"](labels)
    approval.write_text(json.dumps(manifest), encoding="utf-8")
    annotation_a.write_text(
        json.dumps({"case_id": "case-1", "label": "REFUTED"}) + "\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="annotation_a_sha256 differs from approval manifest"):
        RUNNER["validate_annotation_approval"](
            cases,
            labels,
            development_cases,
            development_labels,
            annotation_a,
            annotation_b,
            agreement,
            approval,
            adjudication,
        )


def test_annotation_approval_rejects_tampered_recomputed_statistics(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    labels = tmp_path / "labels.jsonl"
    development_cases = tmp_path / "development-cases.jsonl"
    development_labels = tmp_path / "development-labels.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    agreement = tmp_path / "agreement.json"
    approval = tmp_path / "approval.json"
    adjudication = tmp_path / "adjudication.md"
    cases.write_text(
        "\n".join(json.dumps({"case_id": x}) for x in ("a", "b")) + "\n",
        encoding="utf-8",
    )
    labels.write_text("{}\n", encoding="utf-8")
    development_cases.write_text("{}\n", encoding="utf-8")
    development_labels.write_text("{}\n", encoding="utf-8")
    adjudication.write_text("synthetic only\n", encoding="utf-8")
    annotation_rows = (
        {"case_id": "a", "label": "SUPPORTED"},
        {"case_id": "b", "label": "REFUTED"},
    )
    annotation_a.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n",
        encoding="utf-8",
    )
    annotation_b.write_text(
        "\n".join(json.dumps(row) for row in annotation_rows) + "\n",
        encoding="utf-8",
    )
    canonical = _write_agreement_report(agreement, annotation_a, annotation_b)
    manifest = {
        "schema_version": 1,
        "status": "APPROVED",
        "approved_by": "Synthetic approver",
        "approved_at": "2026-10-21",
        "cases_sha256": RUNNER["_sha256"](cases),
        "labels_sha256": RUNNER["_sha256"](labels),
        "development_cases_sha256": RUNNER["_sha256"](development_cases),
        "development_labels_sha256": RUNNER["_sha256"](development_labels),
        "agreement_report_sha256": RUNNER["_sha256"](agreement),
        "adjudication_record_sha256": RUNNER["_sha256"](adjudication),
        "annotation_a_sha256": RUNNER["_sha256"](annotation_a),
        "annotation_b_sha256": RUNNER["_sha256"](annotation_b),
        "cohen_kappa": canonical["cohen_kappa"],
    }
    mutations = (
        lambda report: report["bootstrap"].update(iterations=10),
        lambda report: report["bootstrap"].update(seed=17),
        lambda report: report["bootstrap"].update(generator="legacy-random"),
        lambda report: report["bootstrap"].update(percentile="legacy-order-statistic"),
        lambda report: report["ci95_case_bootstrap"].__setitem__(0, -0.5),
        lambda report: report.update(cohen_kappa=0.9),
    )
    for mutate in mutations:
        report = json.loads(json.dumps(canonical))
        mutate(report)
        agreement.write_text(json.dumps(report), encoding="utf-8")
        manifest["agreement_report_sha256"] = RUNNER["_sha256"](agreement)
        manifest["cohen_kappa"] = report["cohen_kappa"]
        approval.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="differs from canonical recomputation"):
            RUNNER["validate_annotation_approval"](
                cases,
                labels,
                development_cases,
                development_labels,
                annotation_a,
                annotation_b,
                agreement,
                approval,
                adjudication,
            )


def _freeze_dependencies(root: Path) -> dict[str, str]:
    """Write synthetic copies of every module the freeze binds and return their hashes."""
    hashes: dict[str, str] = {}
    for relative in RUNNER["RUNNER_DEPENDENCIES"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# synthetic {relative}\n", encoding="utf-8")
        hashes[relative] = RUNNER["_sha256"](path)
    return hashes


def test_protocol_freeze_requires_status_manifest_and_exact_hashes(tmp_path: Path) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    manifest_path = eval_dir / "PROTOCOL-FREEZE.json"
    protocol.write_text("Status: CONGELADO — aprovado após revisão humana.\n", encoding="utf-8")
    preregistration.write_text(
        "**Estado:** [CONGELADO] — critérios congelados.\n", encoding="utf-8"
    )
    runner_spec.write_text("**Estado:** [CONGELADO] — executor congelado.\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="requires both documents"):
        RUNNER["validate_protocol_freeze"](tmp_path)

    manifest = {
        "schema_version": 2,
        "status": "FROZEN",
        "approved_by": "Anderson Leon Ayora",
        "approved_at": "2026-10-21",
        "protocol_sha256": RUNNER["_sha256"](protocol),
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_dependencies_sha256": _freeze_dependencies(tmp_path),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = RUNNER["validate_protocol_freeze"](tmp_path)
    assert result["approved_by"] == "Anderson Leon Ayora"
    assert result["protocol_sha256"] == manifest["protocol_sha256"]
    assert len(result["manifest_sha256"]) == 64

    protocol.write_text("Status: alterado após congelamento.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="protocol is not marked CONGELADO"):
        RUNNER["validate_protocol_freeze"](tmp_path)


def test_protocol_freeze_rejects_stale_document_hash(tmp_path: Path) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}\n', encoding="utf-8")
    manifest_path = eval_dir / "PROTOCOL-FREEZE.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "status": "FROZEN",
                "approved_by": "Anderson Leon Ayora",
                "approved_at": "2026-10-21",
                "protocol_sha256": "0" * 64,
                "preregistration_sha256": RUNNER["_sha256"](preregistration),
                "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
                "runner_code_sha256": "0" * 64,
                "runner_dependencies_sha256": _freeze_dependencies(tmp_path),
                "runner_version": RUNNER["RUNNER_VERSION"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="protocol_sha256 differs"):
        RUNNER["validate_protocol_freeze"](tmp_path)


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("runner_spec_sha256", "0" * 64, "runner_spec_sha256 differs"),
        ("runner_code_sha256", "0" * 64, "runner_code_sha256 differs"),
        ("runner_version", "rgc-eval/9.9.9", "runner version differs"),
    ],
)
def test_protocol_freeze_rejects_runner_artifact_drift(
    tmp_path: Path, field: str, bad_value: str, message: str
) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}"\n', encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "status": "FROZEN",
        "approved_by": "Anderson Leon Ayora",
        "approved_at": "2026-10-21",
        "protocol_sha256": RUNNER["_sha256"](protocol),
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_dependencies_sha256": _freeze_dependencies(tmp_path),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    manifest[field] = bad_value
    (eval_dir / "PROTOCOL-FREEZE.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["validate_protocol_freeze"](tmp_path)


def test_dec018_development_partition_reports_metrics_without_testing_h1() -> None:
    case = _case("dev-scope", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    result = RUNNER["evaluate"](
        [case],
        {"dev-scope": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
        partition="development",
    )
    assert result["evaluation_partition"] == "development"
    assert result["metrics"]["primary_criterion"]["h1_supported"] is None
    assert result["metrics"]["primary_criterion"]["not_tested"] is True


# --- DEC-010 option A: annotated atoms for compound claims -------------------

CANCEL = "§ 1º O cancelamento será efetivado em até 2 (dois) dias."


def _compound(case_id: str, claim: str, parts: list[str]) -> dict[str, Any]:
    case = _case(case_id, claim, CANCEL)
    case["atoms"] = [
        {"start_offset": claim.index(part), "end_offset": claim.index(part) + len(part)}
        for part in parts
    ]
    return case


def _predict(case: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = RUNNER["predict"](
        case["claim"],
        RUNNER["oracle_passages"](case, DOCS),
        DOCS,
        atoms=RUNNER["case_atoms"](case),
    )
    return result


def test_compound_claim_with_one_unconfirmed_part_is_partially_supported() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    case = _compound(
        "k4", claim, ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    )
    result = _predict(case)
    assert result["judge_verdict"] == "PARTIALLY_SUPPORTED"
    assert result["stances"] == ["SUPPORTS", "NEUTRAL"]
    # The same text as a single atom cannot reach K4 (the limitation fixed here).
    single = _predict(_case("k4-single", claim, CANCEL))
    assert single["judge_verdict"] != "PARTIALLY_SUPPORTED"


def test_compound_claim_with_a_contradicted_part_is_refuted() -> None:
    claim = "O cancelamento será efetivado em até 9 dias e o plano terá multa de 10%."
    case = _compound(
        "k1", claim, ["O cancelamento será efetivado em até 9 dias", "o plano terá multa de 10%"]
    )
    assert _predict(case)["judge_verdict"] == "REFUTED"


def test_compound_prediction_is_deterministic_and_lists_atoms() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    parts = ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    first = _predict(_compound("d1", claim, parts))
    second = _predict(_compound("d1", claim, parts))
    assert first["output_sha256"] == second["output_sha256"]
    assert first["atoms"] == parts


def test_case_without_atoms_keeps_single_atom_behaviour() -> None:
    case = _case("s1", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    assert RUNNER["case_atoms"](case) is None
    result = _predict(case)
    assert result["atoms"] == [case["claim"]]
    assert result["judge_verdict"] == "SUPPORTED"


@pytest.mark.parametrize(
    ("atoms", "message"),
    [
        ([{"start_offset": 0, "end_offset": 5}], "two or more"),
        (
            [{"start_offset": 0, "end_offset": 5}, {"start_offset": 3, "end_offset": 9}],
            "non-overlapping",
        ),
        (
            [{"start_offset": 0, "end_offset": 5}, {"start_offset": 6, "end_offset": 999}],
            "outside the claim",
        ),
        ([{"start_offset": 0, "end_offset": 5}, {"start_offset": 5, "end_offset": 6}], "blank"),
        (
            [
                {"start_offset": 0, "end_offset": 5, "text": "Outro"},
                {"start_offset": 6, "end_offset": 10},
            ],
            "does not match",
        ),
        (
            [{"start_offset": "0", "end_offset": 5}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        (
            [{"start_offset": True, "end_offset": 5}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        (
            [{"start_offset": 0, "end_offset": True}, {"start_offset": 6, "end_offset": 10}],
            "integers",
        ),
        ([None, {"start_offset": 6, "end_offset": 10}], "each atom must be an object"),
    ],
)
def test_invalid_atom_annotation_stops_the_run(atoms: list[Any], message: str) -> None:
    case = _case("bad", "Texto A e texto B.", CANCEL)
    case["atoms"] = atoms
    with pytest.raises(ValueError, match=message):
        RUNNER["case_atoms"](case)


def test_evaluate_uses_annotated_atoms() -> None:
    claim = "O cancelamento será efetivado em até 2 dias e o plano terá multa de 10%."
    case = _compound(
        "e1", claim, ["O cancelamento será efetivado em até 2 dias", "o plano terá multa de 10%"]
    )
    result = RUNNER["evaluate"](
        [case],
        {"e1": "PARTIALLY_SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=10,
    )
    assert result["cases"][0]["predicted"] == "PARTIALLY_SUPPORTED"


# ------------------------------------------- rectified stratum (Amendment 4)


def _rectified_cases() -> list[dict[str, Any]]:
    supported = _case("r1", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    refuted = _case("r2", "O cancelamento será efetivado em até 9 dias.", CANCEL)
    plain = _case("r3", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    supported["rectified"] = True
    refuted["rectified"] = True
    plain["rectified"] = False
    return [supported, refuted, plain]


def test_rectified_mark_defaults_to_false_and_must_be_boolean() -> None:
    case = _case("r0", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    assert RUNNER["case_rectified"](case) is False
    case["rectified"] = True
    assert RUNNER["case_rectified"](case) is True
    for bad in ("true", 1, None, "sim"):
        case["rectified"] = bad
        with pytest.raises(ValueError, match="rectified must be true or false"):
            RUNNER["case_rectified"](case)


def test_rectified_cases_are_reported_as_a_separate_stratum() -> None:
    labels = {"r1": "SUPPORTED", "r2": "SUPPORTED", "r3": "SUPPORTED"}
    result = RUNNER["evaluate"](
        _rectified_cases(),
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=50,
    )
    # Primary metrics keep every evaluable case, rectified or not.
    assert result["metrics"]["n"] == 3
    assert [row["rectified"] for row in result["cases"]] == [True, True, False]
    rectified, plain = result["strata"]["rectified"], result["strata"]["not_rectified"]
    assert rectified["n"] == 2
    assert rectified["system"]["accuracy"] == 0.5
    assert rectified["confusion"]["SUPPORTED"]["REFUTED"] == 1
    assert plain["n"] == 1
    assert plain["system"]["accuracy"] == 1.0
    assert "primary_criterion" not in rectified


def test_rectified_mark_does_not_change_the_judge_output() -> None:
    marked = _rectified_cases()
    unmarked = [{k: v for k, v in case.items() if k != "rectified"} for case in marked]
    labels = {"r1": "SUPPORTED", "r2": "REFUTED", "r3": "SUPPORTED"}
    run = RUNNER["evaluate"]
    with_mark = run(
        marked,
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
    )
    without = run(
        unmarked,
        labels,
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
    )
    assert [r["output_sha256"] for r in with_mark["cases"]] == [
        r["output_sha256"] for r in without["cases"]
    ]
    assert with_mark["metrics"] == without["metrics"]
    assert without["strata"]["rectified"] == {"n": 0}
    assert without["strata"]["not_rectified"]["n"] == 3


def test_invalid_rectified_mark_stops_the_run() -> None:
    cases = _rectified_cases()
    cases[0]["rectified"] = "true"
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            cases,
            {"r1": "SUPPORTED", "r2": "REFUTED", "r3": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("labels", "case_id"),
    [
        ({"r4": "RULE_GAP"}, "excluded"),
        ({}, "unlabeled"),
    ],
)
def test_invalid_rectified_mark_is_rejected_even_when_case_is_not_scored(
    labels: dict[str, str], case_id: str
) -> None:
    case = _case("r4", "O cancelamento será efetivado em até 2 dias.", CANCEL)
    case["rectified"] = "true"
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            [case],
            labels,
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ('{"case_id":123,"verdict":"SUPPORTED"}', "case_id must be a non-empty string"),
        (
            '{"case_id":"x","verdict":"SUPPORTED","note":"extra"}',
            "expected exactly case_id and verdict",
        ),
        ('{"case_id":"x"}', "expected exactly case_id and verdict"),
        ('{"case_id":" ","verdict":"SUPPORTED"}', "case_id must be a non-empty string"),
        ('{"case_id":"x","verdict":1}', "label 1"),
    ],
)
def test_load_labels_rejects_noncanonical_records(tmp_path: Path, line: str, message: str) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_labels"](path, "judge2")


def test_load_labels_rejects_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "labels.jsonl"
    path.write_text('{"case_id":"x","verdict":"SUPPORTED"}\n\n', encoding="utf-8")
    with pytest.raises(ValueError, match="blank lines are not allowed"):
        RUNNER["load_labels"](path, "judge2")


def _source_record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "source_id": "synthetic-source",
        "source_url": "https://example.test/source",
        "retrieved_at": "2026-10-22T00:00:00Z",
        "source_license": "synthetic",
        "text": "Synthetic source text.",
    }
    record.update(overrides)
    return record


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (_source_record(source_id=123), "source_id must be a non-empty string"),
        (_source_record(source_url=" "), "source_url must be a non-empty string"),
        (_source_record(retrieved_at=None), "retrieved_at must be a non-empty string"),
        (
            _source_record(source_license=["synthetic"]),
            "source_license must be a non-empty string",
        ),
        (_source_record(text=42), "text must be a non-empty string"),
        *[
            (
                {key: value for key, value in _source_record().items() if key != missing},
                "expected an object",
            )
            for missing in ("source_id", "source_url", "retrieved_at", "source_license", "text")
        ],
        *[
            (_source_record(**{field: ""}), f"{field} must be a non-empty string")
            for field in ("source_id", "source_url", "retrieved_at", "source_license", "text")
        ],
        (
            _source_record(text_sha256="not-a-hash"),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (
            _source_record(text_sha256="A" * 64),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (
            _source_record(text_sha256=None),
            "text_sha256 must be 64 lowercase hex characters",
        ),
        (_source_record(text_sha256="0" * 64), "text_sha256 mismatch"),
    ],
)
def test_load_documents_rejects_malformed_source_records(
    tmp_path: Path, record: dict[str, Any], message: str
) -> None:
    path = tmp_path / "documents.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_documents"](path)


def test_load_documents_accepts_additional_provenance_metadata(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    record = _source_record(
        title="Synthetic source",
        extraction="synthetic extraction method",
        page_source_ids=["synthetic-page-1"],
    )
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")
    documents = RUNNER["load_documents"](path)
    assert documents["synthetic-source"].text == "Synthetic source text."


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"source_id":', "invalid JSON"),
        ('{"source_id":"x"}\n', "expected an object"),
        (json.dumps(_source_record()) + "\n\n", "blank lines are not allowed"),
    ],
)
def test_load_documents_rejects_invalid_jsonl_layout(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "documents.jsonl"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["load_documents"](path)


def test_load_documents_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    path = tmp_path / "documents.jsonl"
    record = _source_record()
    path.write_text(
        json.dumps(record) + "\n" + json.dumps(record) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate document"):
        RUNNER["load_documents"](path)


# --- approval integrity / definitive partition guards -------------------------


def test_annotation_approval_requires_exact_case_id_coverage(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    annotation_a = tmp_path / "annotation-a.jsonl"
    annotation_b = tmp_path / "annotation-b.jsonl"
    cases.write_text('{"case_id":"case-1"}\n{"case_id":"case-2"}\n', encoding="utf-8")
    annotation_a.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-2","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    annotation_b.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-2","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    RUNNER["_validate_annotation_case_ids"](cases, annotation_a, annotation_b)

    annotation_a.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"extra-a","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    annotation_b.write_text(
        '{"case_id":"case-2","label":"REFUTED"}\n{"case_id":"extra-b","label":"SUPPORTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError) as exc_info:
        RUNNER["_validate_annotation_case_ids"](cases, annotation_a, annotation_b)
    message = str(exc_info.value)
    assert "cases-A=['case-2']" in message
    assert "cases-B=['case-1']" in message
    assert "A-cases=['extra-a']" in message
    assert "B-cases=['extra-b']" in message


def test_annotation_case_id_reader_rejects_duplicate_and_blank_records(tmp_path: Path) -> None:
    path = tmp_path / "annotation.jsonl"
    path.write_text(
        '{"case_id":"case-1","label":"SUPPORTED"}\n{"case_id":"case-1","label":"REFUTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate case_id"):
        RUNNER["_strict_jsonl_case_ids"](path, annotation=True)

    path.write_text('{"case_id":"case-1","label":"SUPPORTED"}\n\n', encoding="utf-8")
    with pytest.raises(ValueError, match="blank lines are not allowed"):
        RUNNER["_strict_jsonl_case_ids"](path, annotation=True)


def test_evaluate_preflights_all_cases_before_predicting(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [
        _case(
            "preflight-1",
            "O prazo é de cinco dias úteis.",
            "no prazo máximo de 5 (cinco) dias úteis",
        ),
        _case(
            "preflight-2",
            "O cancelamento ocorre em dois dias.",
            "O cancelamento será efetivado em até 2 (dois) dias",
        ),
        _case(
            "preflight-3",
            "A devolução é em dobro.",
            "A cobrança indevida será devolvida em dobro",
        ),
    ]
    cases[1]["rectified"] = "invalid"
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when preflight fails")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="rectified must be true or false"):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def test_evaluate_preflights_invalid_gold_label_before_predicting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _case(
        "invalid-gold-label",
        "O prazo é de cinco dias úteis.",
        "no prazo máximo de 5 (cinco) dias úteis",
    )
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when the gold label is invalid")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="invalid gold label"):
        RUNNER["evaluate"](
            [case],
            {"invalid-gold-label": "UNRECOGNIZED_LABEL"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def _preflight_cases() -> list[dict[str, Any]]:
    return [
        _case(
            "oracle-preflight-1",
            "O prazo é de cinco dias úteis.",
            "no prazo máximo de 5 (cinco) dias úteis",
        ),
        _case(
            "oracle-preflight-2",
            "O cancelamento ocorre em dois dias.",
            "O cancelamento será efetivado em até 2 (dois) dias",
        ),
    ]


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        (
            lambda case: case["evidence"][0].update(excerpt="trecho divergente"),
            "excerpt does not match document offsets",
        ),
        (
            lambda case: case["evidence"][0].update(document_id="documento-inexistente"),
            "unknown evidence document_id",
        ),
        (lambda case: case.pop("evidence"), "evidence must be a non-empty list"),
        (lambda case: case.update(claim="   "), "claim must be a non-empty string"),
    ],
)
def test_evaluate_preflights_oracle_evidence_before_predicting(
    monkeypatch: pytest.MonkeyPatch,
    corrupt: Callable[[dict[str, Any]], object],
    message: str,
) -> None:
    cases = _preflight_cases()
    corrupt(cases[-1])
    calls: list[str] = []

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls.append(str(args[0]))
        raise AssertionError("predict must not run when oracle evidence is invalid")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match=message):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=10,
        )
    assert calls == []


def test_evaluate_rejects_unknown_mode_before_predicting(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = _preflight_cases()

    def predictor(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("predict must not run for an unknown mode")

    monkeypatch.setitem(RUNNER["evaluate"].__globals__, "predict", predictor)
    with pytest.raises(ValueError, match="mode must be oracle or retrieval"):
        RUNNER["evaluate"](
            cases,
            {case["case_id"]: "SUPPORTED" for case in cases},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="orcale",
            vocabulary="judge2",
            iterations=10,
        )


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        ('{"case_id":', "invalid JSON"),
        ("[]", "expected an object"),
        ('{"case_id":123}', "case_id must be a non-empty string"),
        ('{"case_id":" "}', "case_id must be a non-empty string"),
        ('{"case_id":"case-1"}\n\n', "blank lines are not allowed"),
        (
            '{"case_id":"case-1"}\n{"case_id":"case-1"}\n',
            "duplicate case_id",
        ),
    ],
)
def test_read_jsonl_rejects_malformed_case_records(
    tmp_path: Path, contents: str, message: str
) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        RUNNER["_read_jsonl"](path)


def test_read_jsonl_accepts_valid_case_records(tmp_path: Path) -> None:
    path = tmp_path / "cases.jsonl"
    path.write_text('{"case_id":"case-1","claim":"A"}\n', encoding="utf-8")
    assert RUNNER["_read_jsonl"](path) == [{"case_id": "case-1", "claim": "A"}]


def _required_manifest_keys(function_name: str) -> set[str]:
    """Read the validator's literal required-key set without loading any data files."""
    runner_path = ROOT / "evals" / "ptbr" / "rgc_eval.py"
    tree = ast.parse(runner_path.read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    for node in ast.walk(function):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "required" for target in node.targets
        ):
            value = ast.literal_eval(node.value)
            if isinstance(value, set) and all(isinstance(key, str) for key in value):
                return value
    raise AssertionError(f"required-key set not found in {function_name}")


def test_manifest_templates_match_runner_required_keys() -> None:
    """Keep blank JSON templates synchronized with the runner's exact schemas."""
    templates = (
        (
            ROOT / "docs" / "eval" / "templates" / "PROTOCOL-FREEZE.template.json",
            "validate_protocol_freeze",
        ),
        (
            ROOT / "docs" / "eval" / "templates" / "ANNOTATION-APPROVAL.template.json",
            "validate_annotation_approval",
        ),
    )
    for path, validator_name in templates:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert set(payload) == _required_manifest_keys(validator_name)
        # A blank template must never look like an already granted human gate.
        assert payload["status"] == "DRAFT"
        if validator_name == "validate_annotation_approval":
            assert payload["cohen_kappa"] is None


def test_blank_annotation_template_is_rejected_by_operational_validator(
    tmp_path: Path,
) -> None:
    """An unfilled template must fail the runner's approval gate."""
    template = ROOT / "docs" / "eval" / "templates" / "ANNOTATION-APPROVAL.template.json"
    manifest_path = tmp_path / "annotation-approval.json"
    manifest_path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    agreement_path = tmp_path / "agreement.json"
    agreement_path.write_text(json.dumps({"method": "cohen_kappa_unweighted"}), encoding="utf-8")

    with pytest.raises(ValueError, match="status must be APPROVED"):
        RUNNER["validate_annotation_approval"](
            cases_path=tmp_path / "cases.jsonl",
            labels_path=tmp_path / "labels.jsonl",
            development_cases_path=tmp_path / "development-cases.jsonl",
            development_labels_path=tmp_path / "development-labels.jsonl",
            annotation_a_path=tmp_path / "annotation-a.jsonl",
            annotation_b_path=tmp_path / "annotation-b.jsonl",
            agreement_report_path=agreement_path,
            approval_manifest_path=manifest_path,
            adjudication_record_path=tmp_path / "adjudication.json",
        )


def test_blank_protocol_freeze_template_is_rejected_by_validator(tmp_path: Path) -> None:
    """A DRAFT freeze template must not pass the operational freeze gate."""
    protocol_dir = tmp_path / "docs" / "eval"
    protocol_dir.mkdir(parents=True)
    (protocol_dir / "PROTOCOL-GOLDEN-V1.md").write_text("Status: CONGELADO\n", encoding="utf-8")
    (protocol_dir / "PREREGISTRATION-RGC-v1.md").write_text(
        "**Estado:** [CONGELADO]\n", encoding="utf-8"
    )
    (protocol_dir / "RUNNER-RGC-v1.md").write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_dir = tmp_path / "evals" / "ptbr"
    runner_dir.mkdir(parents=True)
    (runner_dir / "rgc_eval.py").write_text("# synthetic validator fixture\n", encoding="utf-8")
    manifest_path = protocol_dir / "PROTOCOL-FREEZE.json"
    template_path = ROOT / "docs" / "eval" / "templates" / "PROTOCOL-FREEZE.template.json"
    manifest_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ValueError, match="schema_version 2 with status FROZEN"):
        RUNNER["validate_protocol_freeze"](root=tmp_path)


@pytest.mark.parametrize(
    ("cited", "cluster", "message"),
    [
        (["syn:a+syn:b"], "syn:a+syn:b", "not a canonical article ID"),
        (["Syn:A"], "Syn:A", "not a canonical article ID"),
        (["syn:a", "syn:b"], "bundle:syn:b+syn:a", "unique, sorted IDs"),
        (["syn:a"], "component:syn:a", "not a canonical article ID"),
    ],
)
def test_hidden_partition_enforces_the_article_id_grammar(
    cited: list[str], cluster: str, message: str
) -> None:
    case = _case("grammar", "O cliente fictício pode cancelar.", "Art. 2º")
    case["cited_article_ids"] = cited
    case["bootstrap_cluster_id"] = cluster
    with pytest.raises(ValueError, match=message):
        RUNNER["evaluate"](
            [case],
            {"grammar": "SUPPORTED"},
            DOCS,
            development_cases=DEV_CASES,
            development_labels=DEV_LABELS,
            mode="oracle",
            vocabulary="judge2",
            iterations=20,
            partition="hidden",
        )


def test_runner_uses_the_shared_article_id_validator() -> None:
    from evals.ptbr import rgc_ids

    assert RUNNER["require_article_id"].__code__ is rgc_ids.require_article_id.__code__
    assert RUNNER["cluster_members"].__code__ is rgc_ids.cluster_members.__code__


# --------------------------------------------------------------------------- DEC-027 D4-D5


def test_hidden_h1_uses_the_component_sign_flip() -> None:
    # Seven single-case components, the system right and baseline B wrong in each:
    # T = 7, exact p = 2 / 2^7 < 0.05, margin 100 pp, component CI lower bound 1.0.
    gold = ["REFUTED"] * 7
    clusters = [f"syn:a{i}" for i in range(7)]
    components = [f"component:syn:a{i}" for i in range(7)]
    metrics = RUNNER["compute_metrics"](
        gold,
        list(gold),
        "judge2",
        baseline_label="SUPPORTED",
        iterations=50,
        cluster_ids=clusters,
        component_ids=components,
    )
    primary = metrics["primary_criterion"]
    assert metrics["sign_flip"]["statistic_observed"] == 7
    assert metrics["sign_flip"]["p_value_two_sided"] == pytest.approx(2 / 2**7)
    assert primary["sign_flip_p_below_0_05"] is True
    assert primary["significance_below_005_possible"] is True
    assert primary["h1_supported"] is True
    assert metrics["system_ci95"]["accuracy"] == [1.0, 1.0]
    # Five components cannot reach p < 0.05 even when every one favours the system.
    small = RUNNER["compute_metrics"](
        gold[:5],
        list(gold[:5]),
        "judge2",
        baseline_label="SUPPORTED",
        iterations=50,
        cluster_ids=clusters[:5],
        component_ids=components[:5],
    )
    assert small["primary_criterion"]["significance_below_005_possible"] is False
    assert small["primary_criterion"]["h1_supported"] is False
    assert metrics["sign_flip"]["informative_component_count"] == 7
    assert metrics["sign_flip"]["minimum_attainable_p"] == 2 / 2**7
    # A seventh component on which system and baseline B tie (d_k = 0) adds to K but not
    # to the attainable significance: six informative components still reach 2 / 2^6.
    tied = RUNNER["compute_metrics"](
        ["REFUTED"] * 5 + ["SUPPORTED"],
        ["REFUTED"] * 5 + ["SUPPORTED"],
        "judge2",
        baseline_label="SUPPORTED",
        iterations=50,
        cluster_ids=clusters[:6],
        component_ids=components[:6],
    )
    assert tied["sign_flip"]["component_count"] == 6
    assert tied["sign_flip"]["informative_component_count"] == 5
    assert tied["primary_criterion"]["significance_below_005_possible"] is False
    assert tied["primary_criterion"]["h1_supported"] is False


def test_primary_interval_is_the_component_bootstrap() -> None:
    from evals.ptbr.rgc_components import bootstrap_metrics_by_component

    gold = ["SUPPORTED", "REFUTED", "SUPPORTED", "REFUTED", "SUPPORTED", "REFUTED"]
    pred = ["SUPPORTED", "SUPPORTED", "SUPPORTED", "REFUTED", "REFUTED", "REFUTED"]
    clusters = ["syn:a", "syn:a", "syn:b", "syn:b", "syn:c", "syn:c"]
    components = [f"component:{c}" for c in clusters]
    metrics = RUNNER["compute_metrics"](
        gold,
        pred,
        "judge2",
        baseline_label="SUPPORTED",
        iterations=200,
        cluster_ids=clusters,
        component_ids=components,
    )
    keys = [f"{i:06d}" for i in range(6)]
    expected = bootstrap_metrics_by_component(
        dict(zip(keys, gold, strict=True)),
        dict(zip(keys, pred, strict=True)),
        dict(zip(keys, components, strict=True)),
        RUNNER["METRICS"],
        iterations=200,
    )
    for name, (low, high) in expected.ci95.items():
        assert metrics["system_ci95"][name] == [round(low, 6), round(high, 6)]
    assert metrics["system_ci95_article_cluster"] != {}  # sensitivity reported separately


def test_cluster_and_component_ids_are_required_together() -> None:
    with pytest.raises(ValueError, match="together"):
        RUNNER["compute_metrics"](
            ["SUPPORTED"],
            ["SUPPORTED"],
            "judge2",
            baseline_label="SUPPORTED",
            iterations=10,
            cluster_ids=["syn:a"],
        )


def test_hidden_components_join_cases_that_share_a_citation() -> None:
    first = _case("join-1", "A Operadora Fictícia deverá responder.", "Art. 1º")
    second = _case("join-2", "O cliente fictício pode cancelar.", "Art. 2º")
    first["cited_article_ids"] = ["syn:a", "syn:shared"]
    first["bootstrap_cluster_id"] = "syn:a"
    second["cited_article_ids"] = ["syn:b", "syn:shared"]
    second["bootstrap_cluster_id"] = "syn:b"
    result = RUNNER["evaluate"](
        [first, second],
        {"join-1": "SUPPORTED", "join-2": "SUPPORTED"},
        DOCS,
        development_cases=DEV_CASES,
        development_labels=DEV_LABELS,
        mode="oracle",
        vocabulary="judge2",
        iterations=20,
        partition="hidden",
    )
    provenance = result["metrics"]["bootstrap_provenance"]
    assert (provenance["cluster_count"], provenance["component_count"]) == (2, 1)


# --------------------------------------------------------------------------- E5


def _frozen_root(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text("# synthetic runner\n", encoding="utf-8")
    manifest: dict[str, object] = {
        "schema_version": 2,
        "status": "FROZEN",
        "approved_by": "Synthetic approver",
        "approved_at": "2026-11-14",
        "protocol_sha256": RUNNER["_sha256"](protocol),
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_dependencies_sha256": _freeze_dependencies(tmp_path),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    (eval_dir / "PROTOCOL-FREEZE.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, manifest


def test_freeze_binds_every_statistical_module(tmp_path: Path) -> None:
    root, _ = _frozen_root(tmp_path)
    result = RUNNER["validate_protocol_freeze"](root)
    assert set(result["runner_dependencies_sha256"]) == set(RUNNER["RUNNER_DEPENDENCIES"])
    # Editing a dependency after the freeze blocks the run, like editing rgc_eval.py.
    (root / "evals" / "ptbr" / "rgc_components.py").write_text("# changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rgc_components.py differs from freeze manifest"):
        RUNNER["validate_protocol_freeze"](root)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda m: m.update(schema_version=1), "schema_version 2"),
        (lambda m: m.pop("runner_dependencies_sha256"), "invalid schema"),
        (lambda m: m.update(runner_dependencies_sha256={}), "must list exactly"),
        (
            lambda m: m["runner_dependencies_sha256"].pop("evals/ptbr/rgc_ids.py"),
            "must list exactly",
        ),
    ],
)
def test_freeze_rejects_old_or_incomplete_dependency_records(
    tmp_path: Path, mutation: Any, message: str
) -> None:
    root, manifest = _frozen_root(tmp_path)
    mutation(manifest)
    (root / "docs" / "eval" / "PROTOCOL-FREEZE.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ValueError, match=message):
        RUNNER["validate_protocol_freeze"](root)


def test_freeze_dependency_list_matches_the_runner_imports() -> None:
    source = (ROOT / "evals" / "ptbr" / "rgc_eval.py").read_text(encoding="utf-8")
    imported = {
        f"evals/ptbr/{name}.py"
        for name in ("rgc_agreement", "rgc_components", "rgc_ids", "rgc_random")
        if f"evals.ptbr.{name}" in source or f"from evals.ptbr import {name}" in source
    }
    expected_dependencies = {
        "evals/ptbr/rgc_agreement.py",
        "evals/ptbr/rgc_components.py",
        "evals/ptbr/rgc_ids.py",
        "evals/ptbr/rgc_random.py",
        "pyproject.toml",
        "rules/judge-2.0.0.json",
        "src/ayorai_attractor/__init__.py",
        "src/ayorai_attractor/evaluation/__init__.py",
        "src/ayorai_attractor/evaluation/stats.py",
        "src/ayorai_attractor/models.py",
        "src/ayorai_attractor/verification/__init__.py",
        "src/ayorai_attractor/verification/claim_pipeline.py",
        "src/ayorai_attractor/verification/clusters.py",
        "src/ayorai_attractor/verification/excerpt.py",
        "src/ayorai_attractor/verification/extraction.py",
        "src/ayorai_attractor/verification/judge.py",
        "src/ayorai_attractor/verification/judge2/__init__.py",
        "src/ayorai_attractor/verification/judge2/adjudication.py",
        "src/ayorai_attractor/verification/judge2/gates.py",
        "src/ayorai_attractor/verification/judge2/rules/judge-2.0.0.json",
        "src/ayorai_attractor/verification/models.py",
        "src/ayorai_attractor/verification/numeric.py",
        "src/ayorai_attractor/verification/pt_normalize.py",
        "src/ayorai_attractor/verification/response.py",
        "src/ayorai_attractor/verification/security.py",
        "src/ayorai_attractor/verification/stance.py",
    }
    assert imported <= expected_dependencies
    assert set(RUNNER["RUNNER_DEPENDENCIES"]) == expected_dependencies
    assert all((ROOT / relative).is_file() for relative in expected_dependencies)
    assert RUNNER["_sha256"](ROOT / "rules/judge-2.0.0.json") == RUNNER["_sha256"](
        ROOT / "src/ayorai_attractor/verification/judge2/rules/judge-2.0.0.json"
    )


@pytest.mark.parametrize(("commit", "clean"), [(None, True), ("f" * 40, False), ("f" * 40, None)])
def test_hidden_run_requires_a_clean_resolvable_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    commit: str | None,
    clean: bool | None,
) -> None:
    globals_ = RUNNER["main"].__globals__
    monkeypatch.setitem(globals_, "validate_protocol_freeze", lambda: {"manifest_sha256": "a" * 64})
    monkeypatch.setitem(globals_, "validate_annotation_approval", lambda *_: {})
    monkeypatch.setitem(globals_, "_git_commit", lambda: commit)
    monkeypatch.setitem(globals_, "_worktree_clean", lambda: clean)
    paths = [str(tmp_path / name) for name in ("c", "l", "a", "b", "r", "m", "j", "dc", "dl")]
    out = tmp_path / "report.json"
    code = RUNNER["main"](
        [
            "run",
            paths[0],
            "--labels",
            paths[1],
            "--annotation-a",
            paths[2],
            "--annotation-b",
            paths[3],
            "--agreement-report",
            paths[4],
            "--annotation-approval",
            paths[5],
            "--adjudication-record",
            paths[6],
            "--development-cases",
            paths[7],
            "--development-labels",
            paths[8],
            "--mode",
            "oracle",
            "--partition",
            "hidden",
            "--out",
            str(out),
        ]
    )
    assert code == 2
    assert "clean git checkout" in capsys.readouterr().err
    assert not out.exists()


def _synthetic_run(
    tmp_path: Path, *, partition: str = "hidden"
) -> tuple[Path, Path, dict[str, Any], dict[str, Any]]:
    """A synthetic report and its run manifest; no RGC case, label or result."""
    code_root = tmp_path / "checkout"
    (code_root / "evals" / "ptbr").mkdir(parents=True)
    for relative in ("evals/ptbr/rgc_eval.py", *RUNNER["RUNNER_DEPENDENCIES"]):
        target = code_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# synthetic {relative}\n", encoding="utf-8")
    cases = tmp_path / "cases.jsonl"
    cases.write_text('{"case_id": "syn-1"}\n', encoding="utf-8")
    report: dict[str, Any] = {
        "runner_version": RUNNER["RUNNER_VERSION"],
        "protocol_freeze": {
            "manifest_sha256": "a" * 64,
            "runner_code_sha256": RUNNER["_sha256"](code_root / "evals" / "ptbr" / "rgc_eval.py"),
            "runner_dependencies_sha256": {
                relative: RUNNER["_sha256"](code_root / relative)
                for relative in RUNNER["RUNNER_DEPENDENCIES"]
            },
        },
        "annotation_approval": {"manifest_sha256": "b" * 64},
        "started_at": "2026-11-14T20:00:00+00:00",
        "generated_at": "2026-11-14T20:00:05+00:00",
        "git_commit": "f" * 40,
        "worktree_clean": True,
        "python": "3.13.0",
        "python_implementation": "CPython",
        "package_version": "0.0.0-synthetic",
        "inputs": {"cases": str(cases), "cases_sha256": RUNNER["_sha256"](cases)},
        "config": {"partition": partition, "mode": "oracle"},
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = RUNNER["build_run_manifest"](
        report, report_path, finished_at="2026-11-14T20:00:06+00:00"
    )
    manifest_path = tmp_path / "report.json.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path, report_path, manifest, report


def test_run_manifest_binds_every_field_and_verifies(tmp_path: Path) -> None:
    manifest_path, report_path, manifest, _ = _synthetic_run(tmp_path)
    assert set(manifest) == RUNNER["RUN_MANIFEST_FIELDS"]
    verified = RUNNER["verify_run_manifest"](
        manifest_path,
        report_path,
        root=tmp_path / "checkout",
        input_files={"cases_sha256": tmp_path / "cases.jsonl"},
    )
    assert verified == manifest


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("protocol_freeze_manifest_sha256", "c" * 64, "protocol_freeze_manifest_sha256 differs"),
        (
            "annotation_approval_manifest_sha256",
            "c" * 64,
            "annotation_approval_manifest_sha256 differs",
        ),
        ("partition", "development", "partition differs"),
        ("git_commit", "0" * 40, "git_commit differs"),
        ("worktree_clean", False, "worktree_clean differs"),
        ("worktree_clean", None, "worktree_clean differs"),
        ("started_at", "2026-11-14T19:59:00+00:00", "started_at differs"),
        ("config_sha256", "0" * 64, "config_sha256 differs"),
        ("runner_version", "rgc-eval/0.0.0", "runner_version differs"),
        ("python", "3.11.0", "python differs"),
        ("python_implementation", "PyPy", "python_implementation differs"),
        ("package_version", "9.9.9", "package_version differs"),
        ("finished_at", "2026-11-14T20:00:04+00:00", "started_at <= generated_at <= finished_at"),
        ("finished_at", "2026-11-14T17:00:06-03:00", "must be in UTC"),
        ("finished_at", "yesterday", "ISO 8601"),
        ("finished_at", 1, "ISO 8601"),
    ],
)
def test_run_manifest_rejects_each_tampered_field(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    manifest_path, report_path, manifest, _ = _synthetic_run(tmp_path)
    manifest[field] = value
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(message)):
        RUNNER["verify_run_manifest"](manifest_path, report_path)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda m: m["runner_dependencies_sha256"].update({"evals/ptbr/rgc_ids.py": "0" * 64}),
            "runner_dependencies_sha256 differs",
        ),
        (
            lambda m: m["runner_dependencies_sha256"].pop("evals/ptbr/rgc_random.py"),
            "runner_dependencies_sha256 must map exactly",
        ),
        (
            lambda m: m["runner_dependencies_sha256"].update({"evals/ptbr/rgc_ids.py": "XYZ"}),
            "runner_dependencies_sha256 must map exactly",
        ),
        (lambda m: m["inputs"].update(cases_sha256="0" * 64), "inputs differs"),
        (lambda m: m["inputs"].update(cases_sha256="0" * 63), "inputs.cases_sha256 is not"),
        (lambda m: m["inputs"].update(cases="elsewhere.jsonl"), "inputs differs"),
        (lambda m: m["report"].update(file="other.json"), "report.file does not name"),
        (lambda m: m["report"].update(sha256="F" * 64), "report.sha256 is not"),
        (lambda m: m["report"].update(extra=1), "exactly file and sha256"),
        (lambda m: m.update(git_commit="F" * 40), "git_commit must be"),
        (lambda m: m.update(git_commit="f" * 39), "git_commit must be"),
        (lambda m: m.update(worktree_clean=1), "worktree_clean must be"),
        (lambda m: m.update(worktree_clean="true"), "worktree_clean must be"),
        (lambda m: m.update(config_sha256="0" * 64 + "0"), "config_sha256 is not"),
        (lambda m: m.update(partition="test"), "partition must be"),
        (lambda m: m.update(python=3.13), "python must be"),
        (lambda m: m.pop("finished_at"), "missing=['finished_at']"),
        (lambda m: m.update(signature="none"), "extra=['signature']"),
        (lambda m: m.update(schema="rgc-run-manifest/2"), "schema must be"),
    ],
)
def test_run_manifest_rejects_malformed_fields(tmp_path: Path, mutate: Any, message: str) -> None:
    manifest_path, report_path, manifest, _ = _synthetic_run(tmp_path)
    mutate(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(message)):
        RUNNER["verify_run_manifest"](manifest_path, report_path)


def test_run_manifest_rejects_unreadable_or_absent_files(tmp_path: Path) -> None:
    manifest_path, report_path, _, _ = _synthetic_run(tmp_path)
    verify = RUNNER["verify_run_manifest"]
    with pytest.raises(ValueError, match="run manifest is missing"):
        verify(tmp_path / "absent.manifest.json", report_path)
    with pytest.raises(ValueError, match="report is missing"):
        verify(manifest_path, tmp_path / "absent.json")
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(original[:-5], encoding="utf-8")
    with pytest.raises(ValueError, match="run manifest is not valid JSON"):
        verify(manifest_path, report_path)
    manifest_path.write_text('{"schema": "rgc-run-manifest/1", "schema": "x"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key 'schema'"):
        verify(manifest_path, report_path)
    manifest_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON object"):
        verify(manifest_path, report_path)


def test_run_manifest_detects_a_tampered_report(tmp_path: Path) -> None:
    manifest_path, report_path, _, report = _synthetic_run(tmp_path)
    report["config"]["mode"] = "retrieval"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="report bytes differ"):
        RUNNER["verify_run_manifest"](manifest_path, report_path)


def test_hidden_run_manifest_requires_clean_commit_even_when_consistent(tmp_path: Path) -> None:
    manifest_path, report_path, _, report = _synthetic_run(tmp_path)
    report["worktree_clean"] = False
    report_path.write_text(json.dumps(report), encoding="utf-8")
    manifest = RUNNER["build_run_manifest"](
        report, report_path, finished_at="2026-11-14T20:00:06+00:00"
    )
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="clean worktree"):
        RUNNER["verify_run_manifest"](manifest_path, report_path)
    # A development run may come from a dirty worktree; it is descriptive only.
    dev_manifest, dev_report, _, dev = _synthetic_run(tmp_path / "dev", partition="development")
    dev["worktree_clean"] = False
    dev_report.write_text(json.dumps(dev), encoding="utf-8")
    dev_manifest.write_text(
        json.dumps(
            RUNNER["build_run_manifest"](dev, dev_report, finished_at="2026-11-14T20:00:06+00:00")
        ),
        encoding="utf-8",
    )
    assert RUNNER["verify_run_manifest"](dev_manifest, dev_report)["worktree_clean"] is False


def test_run_manifest_detects_statistical_code_changed_after_the_run(tmp_path: Path) -> None:
    manifest_path, report_path, _, _ = _synthetic_run(tmp_path)
    checkout = tmp_path / "checkout"
    component = checkout / "evals" / "ptbr" / "rgc_components.py"
    component.write_text("# changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="rgc_components.py differs from the frozen code"):
        RUNNER["verify_run_manifest"](manifest_path, report_path, root=checkout)
    component.unlink()
    with pytest.raises(ValueError, match="rgc_components.py is missing"):
        RUNNER["verify_run_manifest"](manifest_path, report_path, root=checkout)


def test_run_manifest_rehashes_input_files_on_request(tmp_path: Path) -> None:
    manifest_path, report_path, _, _ = _synthetic_run(tmp_path)
    cases = tmp_path / "cases.jsonl"
    cases.write_text('{"case_id": "syn-2"}\n', encoding="utf-8")
    verify = RUNNER["verify_run_manifest"]
    with pytest.raises(ValueError, match="inputs.cases_sha256 differs"):
        verify(manifest_path, report_path, input_files={"cases_sha256": cases})
    with pytest.raises(ValueError, match="no digest field 'labels_sha256'"):
        verify(manifest_path, report_path, input_files={"labels_sha256": cases})
    with pytest.raises(ValueError, match="cannot be read"):
        verify(manifest_path, report_path, input_files={"cases_sha256": tmp_path / "gone"})


def test_report_missing_a_bound_field_is_rejected(tmp_path: Path) -> None:
    manifest_path, report_path, _, report = _synthetic_run(tmp_path)
    del report["package_version"]
    report_path.write_text(json.dumps(report), encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["report"]["sha256"] = RUNNER["_sha256"](report_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="report lacks a field"):
        RUNNER["verify_run_manifest"](manifest_path, report_path)


def test_publish_refuses_a_stale_manifest_without_its_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, report = _synthetic_run(tmp_path)
    out = tmp_path / "new.json"
    stale = tmp_path / "new.json.manifest.json"
    stale.write_text("{}", encoding="utf-8")
    assert RUNNER["_publish_run"](report, out, stale) == 2
    assert "already exists" in capsys.readouterr().err
    assert not out.exists() and stale.read_text(encoding="utf-8") == "{}"
    stale.unlink()
    assert RUNNER["_publish_run"](report, out, stale) == 0
    assert RUNNER["verify_run_manifest"](stale, out)["report"]["file"] == "new.json"


def test_input_snapshot_is_immutable_to_source_replacement_and_reuses_same_capture(
    tmp_path: Path,
) -> None:
    source = tmp_path / "caller-controlled.jsonl"
    original = b'{"case_id":"snapshot-original"}\n'
    source.write_bytes(original)
    snapshots, digests = RUNNER["_snapshot_files"](
        {"inputs/cases.jsonl": source, "inputs/labels.jsonl": source},
        tmp_path / "private-snapshot",
    )
    source.write_bytes(b'{"case_id":"attacker-replacement"}\n')

    assert snapshots["inputs/cases.jsonl"] == snapshots["inputs/labels.jsonl"]
    assert snapshots["inputs/cases.jsonl"].read_bytes() == original
    assert RUNNER["_sha256"](snapshots["inputs/cases.jsonl"]) == digests["inputs/cases.jsonl"]
    assert RUNNER["_read_jsonl"](snapshots["inputs/cases.jsonl"]) == [
        {"case_id": "snapshot-original"}
    ]
    assert not (snapshots["inputs/cases.jsonl"].stat().st_mode & 0o222)


def test_snapshot_digest_is_not_recomputed_from_replaced_source(tmp_path: Path) -> None:
    source = tmp_path / "approved.jsonl"
    original = b'{"case_id":"approved"}\n'
    source.write_bytes(original)
    snapshots, digests = RUNNER["_snapshot_files"](
        {"inputs/cases.jsonl": source}, tmp_path / "snapshot"
    )

    # Simulate a concurrent replacement after the initial capture and before
    # validation/evaluation/publication. The private snapshot remains authoritative.
    source.write_bytes(b'{"case_id":"replacement"}\n')
    assert RUNNER["_read_jsonl"](snapshots["inputs/cases.jsonl"])[0]["case_id"] == "approved"
    assert RUNNER["_sha256"](snapshots["inputs/cases.jsonl"]) == digests["inputs/cases.jsonl"]
    assert RUNNER["_sha256"](source) != digests["inputs/cases.jsonl"]


def test_publish_rechecks_the_exact_input_snapshots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, _, _, report = _synthetic_run(tmp_path)
    cases = tmp_path / "cases.jsonl"
    out = tmp_path / "bound.json"
    manifest = tmp_path / "bound.json.manifest.json"
    cases.write_text('{"case_id":"changed-after-evaluation"}\n', encoding="utf-8")

    status = RUNNER["_publish_run"](report, out, manifest, input_files={"cases_sha256": cases})
    assert status == 2
    assert "inputs.cases_sha256 differs" in capsys.readouterr().err
    assert not out.exists()
    assert not manifest.exists()


def test_atomic_text_publication_never_overwrites_existing_output(tmp_path: Path) -> None:
    target = tmp_path / "report.json"
    target.write_text("original\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        RUNNER["_atomic_write_text"](target, "replacement\n")
    assert target.read_text(encoding="utf-8") == "original\n"
    assert not list(tmp_path.glob(".report.json.*"))


def test_strict_json_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    manifest = tmp_path / "freeze.json"
    manifest.write_text(
        '{"schema_version":2,"status":"FROZEN","status":"DRAFT"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key 'status'"):
        RUNNER["_load_strict_json"](manifest, "protocol freeze manifest")


def test_protocol_freeze_rejects_non_digest_hash_format(tmp_path: Path) -> None:
    eval_dir = tmp_path / "docs" / "eval"
    eval_dir.mkdir(parents=True)
    protocol = eval_dir / "PROTOCOL-GOLDEN-V1.md"
    preregistration = eval_dir / "PREREGISTRATION-RGC-v1.md"
    runner_spec = eval_dir / "RUNNER-RGC-v1.md"
    runner_code = tmp_path / "evals" / "ptbr" / "rgc_eval.py"
    runner_code.parent.mkdir(parents=True)
    protocol.write_text("Status: CONGELADO\n", encoding="utf-8")
    preregistration.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_spec.write_text("**Estado:** [CONGELADO]\n", encoding="utf-8")
    runner_code.write_text(f'RUNNER_VERSION = "{RUNNER["RUNNER_VERSION"]}"\n', encoding="utf-8")
    manifest = {
        "schema_version": 2,
        "status": "FROZEN",
        "approved_by": "Synthetic approver",
        "approved_at": "2026-10-21",
        "protocol_sha256": "not-a-digest",
        "preregistration_sha256": RUNNER["_sha256"](preregistration),
        "runner_spec_sha256": RUNNER["_sha256"](runner_spec),
        "runner_code_sha256": RUNNER["_sha256"](runner_code),
        "runner_dependencies_sha256": _freeze_dependencies(tmp_path),
        "runner_version": RUNNER["RUNNER_VERSION"],
    }
    (eval_dir / "PROTOCOL-FREEZE.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="protocol_sha256 must be a lowercase SHA-256 digest"):
        RUNNER["validate_protocol_freeze"](tmp_path)


def test_snapshot_capture_fails_closed_if_source_changes_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "changing.jsonl"
    source.write_text('{"case_id":"stable"}\n', encoding="utf-8")
    real_fstat = RUNNER["os"].fstat
    calls = 0

    def changed_fstat(descriptor: int) -> object:
        nonlocal calls
        result = real_fstat(descriptor)
        calls += 1
        if calls == 2:
            fields = list(result)
            fields[8] += 1
            return RUNNER["os"].stat_result(fields)
        return result

    monkeypatch.setattr(RUNNER["os"], "fstat", changed_fstat)
    destination = tmp_path / "snapshot"
    with pytest.raises(ValueError, match="changed while being snapshotted"):
        RUNNER["_snapshot_files"]({"inputs/cases.jsonl": source}, destination)
    assert not destination.exists()


def test_case_jsonl_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text('{"case_id":"a","case_id":"attacker"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key 'case_id'"):
        RUNNER["_read_jsonl"](cases)


def test_label_jsonl_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    labels = tmp_path / "labels.jsonl"
    labels.write_text(
        '{"case_id":"a","verdict":"SUPPORTED","verdict":"REFUTED"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key 'verdict'"):
        RUNNER["load_labels"](labels, "judge2")


def test_document_jsonl_rejects_duplicate_object_keys(tmp_path: Path) -> None:
    documents = tmp_path / "documents.jsonl"
    documents.write_text(
        '{"source_id":"a","source_id":"attacker","source_url":"https://example.test",'
        '"retrieved_at":"2026-10-21T00:00:00Z","source_license":"synthetic","text":"x"}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate JSON key 'source_id'"):
        RUNNER["load_documents"](documents)


def test_execution_provenance_accepts_exact_snapshot_module_bytes() -> None:
    runner_path = ROOT / "evals" / "ptbr" / "rgc_eval.py"
    module_path = ROOT / "evals" / "ptbr" / "rgc_ids.py"
    expected = {
        "evals/ptbr/rgc_eval.py": RUNNER["_sha256"](runner_path),
        "evals/ptbr/rgc_ids.py": RUNNER["_sha256"](module_path),
    }
    loaded = {"evals.ptbr.rgc_ids": type("LoadedModule", (), {"__file__": str(module_path)})()}
    RUNNER["_assert_loaded_modules_from_snapshot"](ROOT, expected, loaded)


def test_execution_provenance_rejects_import_origin_outside_snapshot(tmp_path: Path) -> None:
    runner_path = ROOT / "evals" / "ptbr" / "rgc_eval.py"
    foreign_module = tmp_path / "rgc_ids.py"
    foreign_module.write_text("# foreign module\n", encoding="utf-8")
    expected = {"evals/ptbr/rgc_eval.py": RUNNER["_sha256"](runner_path)}
    loaded = {"evals.ptbr.rgc_ids": type("LoadedModule", (), {"__file__": str(foreign_module)})()}
    with pytest.raises(ValueError, match="imported outside the snapshot"):
        RUNNER["_assert_loaded_modules_from_snapshot"](ROOT, expected, loaded)


def test_execution_provenance_rejects_loaded_source_digest_mismatch() -> None:
    runner_path = ROOT / "evals" / "ptbr" / "rgc_eval.py"
    module_path = ROOT / "evals" / "ptbr" / "rgc_ids.py"
    expected = {
        "evals/ptbr/rgc_eval.py": RUNNER["_sha256"](runner_path),
        "evals/ptbr/rgc_ids.py": "0" * 64,
    }
    loaded = {"evals.ptbr.rgc_ids": type("LoadedModule", (), {"__file__": str(module_path)})()}
    with pytest.raises(ValueError, match="not bound to the captured source bytes"):
        RUNNER["_assert_loaded_modules_from_snapshot"](ROOT, expected, loaded)


def test_snapshot_child_environment_drops_git_overrides_and_unrelated_secrets() -> None:
    parent = {
        "PATH": "/tmp/attacker-bin",
        "LANG": "C.UTF-8",
        "GIT_DIR": "/tmp/attacker.git",
        "GIT_WORK_TREE": "/tmp/attacker-worktree",
        "GIT_INDEX_FILE": "/tmp/attacker-index",
        "GIT_CONFIG_COUNT": "1",
        "AWS_ACCESS_KEY_ID": "must-not-leak",
        "GITHUB_TOKEN": "must-not-leak",
        "ATTRACTOR_API_KEYS_HMAC_SHA256": "must-not-leak",
        "PYTHONPATH": "/tmp/foreign-python",
        "HTTP_PROXY": "http://attacker.invalid",
    }
    metadata = {
        "AYORAI_RGC_SNAPSHOT_CHILD": "1",
        "AYORAI_RGC_EXPECTED_GIT_COMMIT": "a" * 40,
        "AYORAI_RGC_EXPECTED_WORKTREE_CLEAN": "true",
    }

    child = RUNNER["_snapshot_child_environment"](parent, metadata)

    assert child == {"LANG": "C.UTF-8", **metadata}
    assert not any(key.startswith("GIT_") for key in child)
    assert not any(key in child for key in ("AWS_ACCESS_KEY_ID", "GITHUB_TOKEN"))
    assert not any(key.startswith("PYTHON") for key in child)


def test_snapshot_child_environment_rejects_non_provenance_metadata() -> None:
    with pytest.raises(ValueError, match="unexpected child environment variable"):
        RUNNER["_snapshot_child_environment"](
            {}, {"GIT_DIR": "/tmp/attacker.git"}
        )


def test_isolated_interpreter_imports_snapshot_despite_hostile_python_environment(
    tmp_path: Path,
) -> None:
    # Include non-Python runtime artifacts too: Judge 2.0 loads its JSON
    # rule contract during import, before the runner can redirect its path.
    code_files = ("evals/ptbr/rgc_eval.py", *RUNNER["RUNNER_DEPENDENCIES"])
    sources = {path: ROOT / path for path in code_files}
    snapshot_root = tmp_path / "snapshot"
    snapshots, digests = RUNNER["_snapshot_files"](sources, snapshot_root)
    expected = {path: digests[path] for path in code_files}
    site_paths = sysconfig.get_paths()
    canary_site_packages = tmp_path / "canary-site-packages"
    canary_site_packages.mkdir()
    (canary_site_packages / "fractions.py").write_text("CANARY = True\n", encoding="utf-8")
    site_packages = [\n        *sorted({site_paths["purelib"], site_paths["platlib"]}),\n        str(canary_site_packages),\n    ]
    script = (
        "import json, runpy, sys; "
        "from pathlib import Path; "
        "snapshot = Path(sys.argv[2]).resolve(); "
        "site_packages = json.loads(sys.argv[3]); "
        "stdlib_paths = list(sys.path); "
        "sys.modules.pop('fractions', None); "
        "sys.path[:] = list(dict.fromkeys(["
        "str(snapshot / 'src'), str(snapshot), *stdlib_paths, *site_packages])); "
        "import fractions; "
        "assert Path(fractions.__file__).resolve().parent != "
        "Path(site_packages[-1]).resolve(); "
        "assert sys.flags.isolated == 1; "
        "assert sys.flags.ignore_environment == 1; "
        "assert sys.flags.no_user_site == 1; "
        "assert sys.flags.no_site == 1; "
        "assert str(Path(sys.argv[4]).resolve()) not in sys.path; "
        "namespace = runpy.run_path(sys.argv[1]); "
        "namespace['_assert_loaded_modules_from_snapshot']("
        "snapshot, json.loads(__import__('os').environ['EXPECTED_CODE']))"
    )
    hostile_environment = os.environ.copy()
    # pytest-cov propagates its tracing configuration to child interpreters.
    # This subprocess validates import provenance, not test coverage; allowing
    # it to trace snapshot copies creates duplicate coverage paths for modules.
    for variable in tuple(hostile_environment):
        if variable.startswith("COV_CORE_"):
            hostile_environment.pop(variable)
    hostile_environment["EXPECTED_CODE"] = json.dumps(expected, sort_keys=True)
    hostile_environment["PYTHONPATH"] = str(ROOT / "src")
    hostile_environment["PYTHONHOME"] = str(tmp_path / "attacker-pythonhome")
    hostile_environment["PYTHONUSERBASE"] = str(tmp_path / "attacker-userbase")
    command = [
        sys.executable,
        "-I",
        "-S",
        "-B",
        "-c",
        script,
        str(snapshots["evals/ptbr/rgc_eval.py"]),
        str(snapshot_root),
        json.dumps(site_packages),
        str(ROOT / "src"),
    ]

    accepted = subprocess.run(
        command,
        cwd=snapshot_root,
        env=hostile_environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert accepted.returncode == 0, accepted.stderr
