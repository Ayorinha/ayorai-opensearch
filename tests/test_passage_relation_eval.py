"""Passage-relation evaluation harness (synthetic, fictitious regulation text only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.passage_relation import metrics, run_system
from evals.passage_relation.metrics import EvaluationInputError

DOCS = [
    {
        "document_id": "reg-a",
        "text": (
            "Art. 1 O prazo de entrega do relatório sintético é de 10 dias.\n"
            "Art. 2 A taxa fictícia de inscrição é de 30 unidades.\n"
            "Art. 3 Exceto no caso do art. 1, o prazo é contado em dias úteis."
        ),
    },
    {
        "document_id": "reg-b",
        "text": "Art. 1 A comissão sintética reúne-se 4 vezes por ano.",
    },
]


def _case(case_id: str, cluster: str, claim: str, label: str, **extra: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "cluster_id": cluster,
        "claim": claim,
        "label": label,
        "document_ids": ["reg-a"] if cluster == "reg-a" else ["reg-b"],
        "adjudicated": True,
        **extra,
    }


CASES = [
    _case("c1", "reg-a", "O prazo de entrega do relatório sintético é de 10 dias.", "supports"),
    _case("c2", "reg-a", "A taxa fictícia de inscrição é de 50 unidades.", "contradicts"),
    _case("c3", "reg-b", "A comissão sintética reúne-se 4 vezes por ano.", "supports"),
]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    return path


@pytest.fixture
def files(tmp_path: Path) -> dict[str, Path]:
    return {
        "cases": _write_jsonl(tmp_path / "cases.jsonl", CASES),
        "documents": _write_jsonl(tmp_path / "documents.jsonl", DOCS),
    }


def _run(files: dict[str, Path], results: list[dict[str, Any]], variant: str = "x") -> metrics.Run:
    path = files["cases"].parent / f"run-{variant}.json"
    path.write_text(
        json.dumps(
            {
                "schema": metrics.SCHEMA,
                "meta": {
                    "variant": variant,
                    "cases_sha256": metrics.sha256_file(files["cases"]),
                    "engine": {"version": "synthetic"},
                },
                "results": results,
            }
        ),
        "utf-8",
    )
    return metrics.load_run(
        path, metrics.load_cases(files["cases"]), metrics.sha256_file(files["cases"])
    )


def _ev(doc: str, start: int, end: int, stance: str) -> dict[str, Any]:
    return {"document_id": doc, "start": start, "end": end, "stance": stance}


def _pair(case: str, doc: str, start: int, end: int, relation: str, stance: str) -> dict[str, Any]:
    return {
        "case_id": case,
        "document_id": doc,
        "start": start,
        "end": end,
        "relation": relation,
        "stance": stance,
        "relation_a": relation,
        "relation_b": relation,
        "stance_a": stance,
        "stance_b": stance,
        "adjudicated": True,
    }


# Passage offsets inside reg-a: art. 1 [0, 62), art. 2 [63, 116), art. 3 [117, 182)
A1, A2, A3, B1 = ("reg-a", 0, 62), ("reg-a", 63, 116), ("reg-a", 117, 182), ("reg-b", 0, 53)

RESULTS_FIRST = [
    # true claim, gold passage supports, an unrelated passage falsely "contradicts"
    {
        "case_id": "c1",
        "verdict": "conflicting",
        "evidence": [_ev(*A1, "supports"), _ev(*A2, "contradicts")],
    },
    # false claim, legitimate contradiction found
    {
        "case_id": "c2",
        "verdict": "refuted",
        "evidence": [_ev(*A2, "contradicts"), _ev(*A1, "neutral")],
    },
    {"case_id": "c3", "verdict": "partially_supported", "evidence": [_ev(*B1, "supports")]},
]
RESULTS_SECOND = [
    {
        "case_id": "c1",
        "verdict": "partially_supported",
        "evidence": [_ev(*A1, "supports"), _ev(*A2, "neutral")],
    },
    {
        "case_id": "c2",
        "verdict": "refuted",
        "evidence": [_ev(*A2, "contradicts"), _ev(*A1, "neutral")],
    },
    {"case_id": "c3", "verdict": None, "evidence": [_ev(*B1, "neutral")]},
]
PAIRS = [
    _pair("c1", *A1, "direta", "supports"),
    _pair("c1", *A2, "sem_relacao", "neutral"),
    _pair("c2", *A2, "direta", "contradicts"),
    _pair("c2", *A1, "sem_relacao", "neutral"),
    _pair("c3", *B1, "direta", "supports"),
]


def _pairs(files: dict[str, Path], rows: list[dict[str, Any]] = PAIRS) -> dict[Any, Any]:
    path = _write_jsonl(files["cases"].parent / "pairs.jsonl", rows)
    return metrics.load_pairs(path, metrics.load_cases(files["cases"]))


def test_cases_must_be_human_adjudicated(tmp_path: Path) -> None:
    rows = [dict(CASES[0], adjudicated=False)]
    with pytest.raises(EvaluationInputError, match="not adjudicated"):
        metrics.load_cases(_write_jsonl(tmp_path / "c.jsonl", rows))
    with pytest.raises(EvaluationInputError, match="duplicate"):
        metrics.load_cases(_write_jsonl(tmp_path / "d.jsonl", [CASES[0], CASES[0]]))
    with pytest.raises(EvaluationInputError, match="label"):
        metrics.load_cases(_write_jsonl(tmp_path / "e.jsonl", [dict(CASES[0], label="maybe")]))


def test_run_is_bound_to_the_case_file(files: dict[str, Path]) -> None:
    run = _run(files, RESULTS_FIRST)
    other = files["cases"].parent / "other.jsonl"
    _write_jsonl(other, CASES[:1] + CASES[1:])
    other.write_text(other.read_text("utf-8") + "\n", "utf-8")  # same cases, other bytes
    path = files["cases"].parent / "run-x.json"
    with pytest.raises(EvaluationInputError, match="another case file"):
        metrics.load_run(path, metrics.load_cases(other), metrics.sha256_file(other))
    assert run.variant == "x"


def test_missing_results_are_rejected(files: dict[str, Path]) -> None:
    with pytest.raises(EvaluationInputError, match="missing results"):
        _run(files, RESULTS_FIRST[:2])


def test_score_counts_false_contradictions_on_unrelated_passages(files: dict[str, Path]) -> None:
    report = metrics.score(
        _run(files, RESULTS_FIRST),
        metrics.load_cases(files["cases"]),
        _pairs(files),
        iterations=200,
    )
    m = report["metrics"]
    assert m["false_contradicts_on_unrelated"]["value"] == 0.5  # A2 on c1 of {A2/c1, A1/c2}
    assert m["false_refuted_or_conflicting_on_supports"]["value"] == 0.5  # c1 of {c1, c3}
    assert m["contradiction_detected_on_contradicts"]["value"] == 1.0
    assert m["contradicts_precision"]["value"] == 0.5
    assert m["contradicts_recall"]["value"] == 1.0
    assert m["recall_relevant_at_k"]["value"] == 1.0
    assert m["relevance_precision_at_k"]["value"] == 3 / 5
    assert m["contradicts_precision_sem_relacao"]["value"] == 0.0
    assert m["contradicts_recall_direta"]["value"] == 1.0
    assert m["abstention_rate"]["value"] == 0.0
    assert report["agreement"] == {"pairs": 5, "relation_kappa": 1.0, "stance_kappa": 1.0}
    assert report["bootstrap"]["unit"] == "cluster_id"
    assert m["false_refuted_or_conflicting_on_supports"]["clusters"] == 2


def test_score_is_deterministic_for_a_seed(files: dict[str, Path]) -> None:
    cases, pairs = metrics.load_cases(files["cases"]), _pairs(files)
    first = metrics.score(_run(files, RESULTS_FIRST), cases, pairs, iterations=300, seed=7)
    second = metrics.score(_run(files, RESULTS_FIRST), cases, pairs, iterations=300, seed=7)
    assert first == second


def test_unannotated_evidence_blocks_scoring(files: dict[str, Path]) -> None:
    with pytest.raises(EvaluationInputError, match="not annotated"):
        metrics.score(
            _run(files, RESULTS_FIRST),
            metrics.load_cases(files["cases"]),
            _pairs(files, PAIRS[:-1]),
            iterations=10,
        )


def test_pairs_need_two_annotations_and_adjudication(files: dict[str, Path]) -> None:
    with pytest.raises(EvaluationInputError, match="not adjudicated"):
        _pairs(files, [dict(PAIRS[0], adjudicated=False)])
    with pytest.raises(EvaluationInputError, match="relation_b"):
        _pairs(files, [{k: v for k, v in PAIRS[0].items() if k != "relation_b"}])


def test_compare_is_paired_by_claim(files: dict[str, Path]) -> None:
    cases, pairs = metrics.load_cases(files["cases"]), _pairs(files)
    report = metrics.compare(
        _run(files, RESULTS_FIRST, "current"),
        _run(files, RESULTS_SECOND, "candidate"),
        cases,
        pairs,
        iterations=200,
    )
    diff = report["differences"]["false_refuted_or_conflicting_on_supports"]
    assert (diff["first"], diff["second"], diff["difference"]) == (0.5, 0.0, -0.5)
    assert report["discordant_claims"]["supports_false_contradiction_verdict"] == {
        "only_first": 1,
        "only_second": 0,
    }
    assert report["discordant_claims"]["abstained"] == {"only_first": 0, "only_second": 1}
    assert report["differences"]["contradiction_detected_on_contradicts"]["difference"] == 0.0


def test_pool_is_blind_to_system_output(files: dict[str, Path]) -> None:
    cases = metrics.load_cases(files["cases"])
    rows = metrics.pool(
        cases,
        [_run(files, RESULTS_FIRST, "a"), _run(files, RESULTS_SECOND, "b")],
        metrics.load_documents(files["documents"]),
    )
    assert len(rows) == 5
    assert all(
        set(row) == {"case_id", "claim", "document_id", "start", "end", "passage"} for row in rows
    )
    assert rows[0]["passage"].startswith("Art. 1 O prazo")


def test_cohen_kappa() -> None:
    assert metrics.cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert metrics.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    assert metrics.cohen_kappa([], []) is None
    assert metrics.cohen_kappa(["a", "a"], ["a", "a"]) is None


def test_run_system_end_to_end(files: dict[str, Path], tmp_path: Path) -> None:
    out = tmp_path / "run.json"
    assert (
        run_system.main(
            [
                "--cases",
                str(files["cases"]),
                "--documents",
                str(files["documents"]),
                "--variant",
                "current",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_text("utf-8"))
    assert report["meta"]["cases_sha256"] == metrics.sha256_file(files["cases"])
    assert report["meta"]["engine"]["judge"] == "ADR-002"
    assert [row["case_id"] for row in report["results"]] == ["c1", "c2", "c3"]
    run = metrics.load_run(
        out, metrics.load_cases(files["cases"]), metrics.sha256_file(files["cases"])
    )
    rows = metrics.pool(
        metrics.load_cases(files["cases"]), [run], metrics.load_documents(files["documents"])
    )
    assert rows and all("stance" not in row for row in rows)
    with pytest.raises(EvaluationInputError, match="unknown variant"):
        run_system.run(files["cases"], files["documents"], "tuned")


def test_cli_score(files: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    _run(files, RESULTS_FIRST)
    pairs = _write_jsonl(files["cases"].parent / "pairs.jsonl", PAIRS)
    run = files["cases"].parent / "run-x.json"
    assert (
        metrics.main(
            [
                "score",
                "--cases",
                str(files["cases"]),
                "--pairs",
                str(pairs),
                "--run",
                str(run),
                "--iterations",
                "50",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["variant"] == "x"


def test_exploratory_script_reads_only_the_dev_split() -> None:
    from evals.passage_relation import exploratory_ptcp_dev

    report = exploratory_ptcp_dev.measure()
    assert report["exploratory"] is True
    assert report["split"] == "dev"
    assert report["cases"] == 70


def test_cli_compare(files: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    _run(files, RESULTS_FIRST, "current")
    _run(files, RESULTS_SECOND, "candidate")
    pairs = _write_jsonl(files["cases"].parent / "pairs.jsonl", PAIRS)
    folder = files["cases"].parent
    argv = ["compare", "--cases", str(files["cases"]), "--pairs", str(pairs)]
    argv += ["--run", str(folder / "run-current.json"), "--run", str(folder / "run-candidate.json")]
    assert metrics.main([*argv, "--iterations", "50"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert (report["first"]["variant"], report["second"]["variant"]) == ("current", "candidate")
