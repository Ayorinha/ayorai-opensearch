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


def _passage_text(passage: Any) -> str:
    return TEXT[passage.start:passage.end]


def _case(case_id: str, claim: str, excerpt: str) -> dict[str, Any]:
    start = TEXT.index(excerpt)
    return {
        "case_id": case_id,
        "claim": claim,
        "evidence": [{"document_id": "sint-1", "excerpt": excerpt,
                      "start_offset": start, "end_offset": start + len(excerpt)}],
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
            assert document.text[cursor:passage.start].strip() == ""
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
        ("O cancelamento será efetivado em até 2 dias.",
         "§ 1º O cancelamento será efetivado em até 2 (dois) dias.", "SUPPORTED"),
        ("O cancelamento será efetivado em até 9 dias.",
         "§ 1º O cancelamento será efetivado em até 2 (dois) dias.", "REFUTED"),
        ("O cliente tem direito a reembolso por satélite.",
         "II - por meio eletrônico.", "UNVERIFIED"),
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


def test_metrics_match_hand_computation() -> None:
    gold = ["SUPPORTED", "SUPPORTED", "SUPPORTED", "REFUTED", "UNVERIFIED"]
    pred = ["SUPPORTED", "SUPPORTED", "REFUTED", "REFUTED", RUNNER["INVALID"]]
    assert RUNNER["accuracy"](gold, pred) == pytest.approx(3 / 5)
    assert RUNNER["balanced_accuracy"](gold, pred) == pytest.approx((2 / 3 + 1 + 0) / 3)
    # F1: SUPPORTED 0.8, REFUTED 2/3, UNVERIFIED 0, INVALID_PREDICTION 0.
    assert RUNNER["macro_f1"](gold, pred) == pytest.approx((0.8 + 2 / 3 + 0 + 0) / 4)
    metrics = RUNNER["compute_metrics"](gold, pred, "judge2", iterations=200)
    assert metrics["baseline"]["label"] == "SUPPORTED"
    assert metrics["baseline"]["accuracy"] == pytest.approx(0.6)
    assert metrics["invalid_predictions"] == 1
    assert metrics["absent_gold_states"] == ["PARTIALLY_SUPPORTED", "CONFLICTING"]
    assert metrics["mcnemar"]["system_right_baseline_wrong"] == 1
    assert metrics["mcnemar"]["system_wrong_baseline_right"] == 1
    assert metrics["primary_criterion"]["h1_supported"] is False
    low, high = metrics["system_ci95"]["accuracy"]
    assert 0.0 <= low <= 0.6 <= high <= 1.0
    assert metrics == RUNNER["compute_metrics"](gold, pred, "judge2", iterations=200)


def test_h1_decision_uses_unrounded_values() -> None:
    # 7 of 10 right vs a 6-of-10 baseline: margin is exactly 10 pp, which binary
    # floating point represents as 0.0999...; it must still count as >= 10 pp.
    gold = ["SUPPORTED"] * 6 + ["REFUTED"] * 4
    pred = ["SUPPORTED"] * 6 + ["REFUTED"] + ["SUPPORTED"] * 3
    metrics = RUNNER["compute_metrics"](gold, pred, "judge2", iterations=50)
    assert metrics["primary_criterion"]["margin_at_least_10pp"] is True
    # A margin of 9.999995 pp rounds to 0.1 at 6 decimals but must not pass.
    gold = ["SUPPORTED"] * 6 + ["REFUTED"] * 4
    compute = RUNNER["compute_metrics"]
    original = RUNNER["METRICS"]["accuracy"]
    try:
        RUNNER["METRICS"]["accuracy"] = lambda g, p: 0.6 if len(set(p)) == 1 else 0.69999995
        metrics = compute(gold, pred, "judge2", iterations=10)
    finally:
        RUNNER["METRICS"]["accuracy"] = original
    assert metrics["system"]["accuracy"] == 0.7
    assert metrics["primary_criterion"]["margin_at_least_10pp"] is False


def test_majority_tie_breaks_by_vocabulary_order() -> None:
    assert RUNNER["majority_label"](["REFUTED", "SUPPORTED"], "judge2") == "SUPPORTED"


def test_evaluate_excludes_rule_gap_and_requires_complete_labels() -> None:
    cases = [
        _case("s1", "O cancelamento será efetivado em até 2 dias.",
              "§ 1º O cancelamento será efetivado em até 2 (dois) dias."),
        _case("s2", "O cancelamento será efetivado em até 9 dias.",
              "§ 1º O cancelamento será efetivado em até 2 (dois) dias."),
        _case("s3", "Algo ambíguo.", "II - por meio eletrônico."),
    ]
    labels = {"s1": "SUPPORTED", "s2": "REFUTED", "s3": "RULE_GAP"}
    for mode in ("oracle", "retrieval"):
        result = RUNNER["evaluate"](cases, labels, DOCS, mode=mode, vocabulary="judge2",
                                    iterations=100)
        assert result["excluded"] == [{"case_id": "s3", "label": "RULE_GAP"}]
        assert [row["predicted"] for row in result["cases"]] == ["SUPPORTED", "REFUTED"]
    with pytest.raises(ValueError, match="unknown cases"):
        RUNNER["evaluate"](cases, {**labels, "s9": "SUPPORTED"}, DOCS, mode="oracle",
                           vocabulary="judge2", iterations=10)
    with pytest.raises(ValueError, match="duplicate case"):
        RUNNER["evaluate"]([*cases, cases[0]], labels, DOCS, mode="oracle",
                           vocabulary="judge2", iterations=10)
    with pytest.raises(ValueError, match="without a label"):
        RUNNER["evaluate"](cases, {"s1": "SUPPORTED"}, DOCS, mode="oracle",
                           vocabulary="judge2", iterations=10)


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
    documents.write_text(json.dumps({
        "source_id": "sint-1", "source_url": "https://example.test/sint-1",
        "source_license": "sintético", "retrieved_at": "2026-10-13T00:00:00Z", "text": TEXT,
    }, ensure_ascii=False) + "\n", encoding="utf-8")
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(_case(
        "s1", "O cancelamento será efetivado em até 2 dias.",
        "§ 1º O cancelamento será efetivado em até 2 (dois) dias.",
    ), ensure_ascii=False) + "\n", encoding="utf-8")
    labels = tmp_path / "labels.jsonl"
    labels.write_text(json.dumps({"case_id": "s1", "verdict": "SUPPORTED"}) + "\n")
    out = tmp_path / "report.json"
    code = RUNNER["main"]([
        "run", str(cases), "--labels", str(labels), "--documents", str(documents),
        "--mode", "retrieval", "--out", str(out),
    ])
    assert code == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["metrics"]["system"]["accuracy"] == 1.0
    assert report["config"]["mode"] == "retrieval"
    assert len(report["inputs"]["cases_sha256"]) == 64
