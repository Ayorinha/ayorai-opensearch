"""RGC evaluation runner — synthetic fixtures only.

No benchmark or pilot case is used here; the only real file read is the
document corpus, to check segmentation offsets and the strict corpus export.
"""

from __future__ import annotations

import json
import runpy
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = runpy.run_path(str(ROOT / "evals" / "ptbr" / "rgc_eval.py"))
CHECKER = runpy.run_path(str(ROOT / "scripts" / "check_golden_pt.py"))
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


def test_evaluate_excludes_rule_gap_and_requires_complete_labels() -> None:
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
        _case("s3", "Algo ambíguo.", "II - por meio eletrônico."),
    ]
    labels = {"s1": "SUPPORTED", "s2": "REFUTED", "s3": "RULE_GAP"}
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
        assert result["excluded"] == [{"case_id": "s3", "label": "RULE_GAP"}]
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


def test_cli_run_writes_report(tmp_path: Path) -> None:
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
        json.dumps(
            _case(
                "s1",
                "O cancelamento será efetivado em até 2 dias.",
                "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
            ),
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    labels = tmp_path / "labels.jsonl"
    labels.write_text(json.dumps({"case_id": "s1", "verdict": "SUPPORTED"}) + "\n")
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
    out = tmp_path / "report.json"
    code = RUNNER["main"](
        [
            "run",
            str(cases),
            "--labels",
            str(labels),
            "--development-cases",
            str(development_cases),
            "--development-labels",
            str(development_labels),
            "--documents",
            str(documents),
            "--mode",
            "retrieval",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["metrics"]["system"]["accuracy"] == 1.0
    assert report["config"]["mode"] == "retrieval"
    assert report["metrics"]["baseline_primary"]["label"] == "SUPPORTED"
    assert report["metrics"]["baseline_descriptive"]["label"] == "SUPPORTED"
    assert report["baseline_provenance"]["primary"] == "B"
    assert len(report["inputs"]["cases_sha256"]) == 64
    assert len(report["inputs"]["development_cases_sha256"]) == 64
    assert len(report["inputs"]["development_labels_sha256"]) == 64


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
    ],
)
def test_invalid_atom_annotation_stops_the_run(atoms: list[dict[str, Any]], message: str) -> None:
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
