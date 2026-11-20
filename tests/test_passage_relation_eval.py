"""Passage-relation evaluation harness (synthetic, fictitious regulation text only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from evals.passage_relation import metrics, run_system
from evals.passage_relation.metrics import EvaluationInputError

DOC_A = (
    "Art. 1 O prazo de entrega do relatório sintético é de 10 dias.\n"
    "Art. 2 A taxa fictícia de inscrição é de 30 unidades.\n"
    "Art. 3 Exceto no caso do art. 1, o prazo é contado em dias úteis."
)
DOC_B = "Art. 1 A comissão sintética reúne-se 4 vezes por ano."
DOCS = [{"document_id": "reg-a", "text": DOC_A}, {"document_id": "reg-b", "text": DOC_B}]
COMMIT = "0123456789abcdef0123456789abcdef01234567"


def _case(case_id: str, cluster: str, claim: str, label: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "cluster_id": cluster,
        "claim": claim,
        "label": label,
        "document_ids": [cluster],
        "adjudicated": True,
    }


CASES = [
    _case("c1", "reg-a", "O prazo de entrega do relatório sintético é de 10 dias.", "supports"),
    _case("c2", "reg-a", "A taxa fictícia de inscrição é de 50 unidades.", "contradicts"),
    _case("c3", "reg-b", "A comissão sintética reúne-se 4 vezes por ano.", "supports"),
    _case("c4", "reg-b", "A comissão sintética reúne-se 9 vezes por ano.", "contradicts"),
]

# Passages: art. 1 [0, 62), art. 2 [63, 116), art. 3 [117, 182) in reg-a; reg-b [0, 53)
A1, A2, A3, B1 = ("reg-a", 0, 62), ("reg-a", 63, 116), ("reg-a", 117, 182), ("reg-b", 0, 53)
TEXTS = {"reg-a": DOC_A, "reg-b": DOC_B}


def _ev(doc: str, start: int, end: int, stance: str) -> dict[str, Any]:
    return {"document_id": doc, "start": start, "end": end, "stance": stance}


def _ann(case: str, doc: str, start: int, end: int, relation: str, stance: str) -> dict[str, Any]:
    return {
        "case_id": case,
        "document_id": doc,
        "start": start,
        "end": end,
        "passage_sha256": metrics.passage_sha256(TEXTS[doc][start:end]),
        "relation": relation,
        "stance": stance,
        "relation_a": relation,
        "relation_b": relation,
        "stance_a": stance,
        "stance_b": stance,
        "adjudicated": True,
    }


RESULTS_FIRST = [
    # true claim; the gold passage supports, an unrelated passage falsely contradicts
    {
        "case_id": "c1",
        "verdict": "conflicting",
        "evidence": [_ev(*A1, "supports"), _ev(*A2, "contradicts")],
    },
    # false claim; decisive refutation
    {
        "case_id": "c2",
        "verdict": "refuted",
        "evidence": [_ev(*A2, "contradicts"), _ev(*A1, "neutral")],
    },
    {"case_id": "c3", "verdict": "partially_supported", "evidence": [_ev(*B1, "supports")]},
    # false claim; conflict only
    {"case_id": "c4", "verdict": "conflicting", "evidence": [_ev(*B1, "contradicts")]},
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
    {"case_id": "c4", "verdict": "refuted", "evidence": [_ev(*B1, "contradicts")]},
]
PAIRS = [
    _ann("c1", *A1, "direta", "supports"),
    _ann("c1", *A2, "sem_relacao", "neutral"),
    _ann("c2", *A2, "direta", "contradicts"),
    _ann("c2", *A1, "sem_relacao", "neutral"),
    _ann("c3", *B1, "direta", "supports"),
    _ann("c4", *B1, "direta", "contradicts"),
]
# Independent universe: people marked art. 3 as an exception relevant to c1, which no
# run cited; recall over the pool is 1.0 but the absolute recall is not.
UNIVERSE = [
    _ann("c1", *A1, "direta", "supports"),
    _ann("c1", *A3, "excecao_restricao", "neutral"),
    _ann("c2", *A2, "direta", "contradicts"),
    _ann("c3", *B1, "direta", "supports"),
    _ann("c4", *B1, "direta", "contradicts"),
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


def _ctx(files: dict[str, Path]) -> tuple[dict[str, metrics.Case], metrics.Documents]:
    return metrics.load_cases(files["cases"]), metrics.load_documents(files["documents"])


def _run_file(
    files: dict[str, Path], results: list[dict[str, Any]], variant: str = "x", **meta: Any
) -> Path:
    path = files["cases"].parent / f"run-{variant}.json"
    payload = {
        "variant": variant,
        "commit": COMMIT,
        "worktree_clean": True,
        "cases_sha256": metrics.sha256_file(files["cases"]),
        "documents_sha256": metrics.sha256_file(files["documents"]),
        "engine": {"version": "synthetic"},
        **meta,
    }
    path.write_text(
        json.dumps({"schema": metrics.SCHEMA, "meta": payload, "results": results}), "utf-8"
    )
    return path


def _run(files: dict[str, Path], results: list[dict[str, Any]], variant: str = "x") -> metrics.Run:
    cases, documents = _ctx(files)
    return metrics.load_run(
        _run_file(files, results, variant), cases, metrics.sha256_file(files["cases"]), documents
    )


def _annotations(
    files: dict[str, Path], rows: list[dict[str, Any]], *, every_case: bool = False
) -> dict[Any, Any]:
    cases, documents = _ctx(files)
    path = _write_jsonl(files["cases"].parent / "ann.jsonl", rows)
    return metrics.load_annotations(path, cases, documents, every_case=every_case)


# --------------------------------------------------------------------------- inputs


def test_cases_must_be_human_adjudicated(tmp_path: Path) -> None:
    with pytest.raises(EvaluationInputError, match="not adjudicated"):
        metrics.load_cases(_write_jsonl(tmp_path / "c.jsonl", [dict(CASES[0], adjudicated=False)]))
    with pytest.raises(EvaluationInputError, match="duplicate"):
        metrics.load_cases(_write_jsonl(tmp_path / "d.jsonl", [CASES[0], CASES[0]]))
    with pytest.raises(EvaluationInputError, match="label"):
        metrics.load_cases(_write_jsonl(tmp_path / "e.jsonl", [dict(CASES[0], label="maybe")]))


@pytest.mark.parametrize(
    ("meta", "message"),
    [
        ({"cases_sha256": "0" * 64}, "another case file"),
        ({"documents_sha256": "0" * 64}, "another document file"),
        ({"commit": "main"}, "40-character"),
        ({"worktree_clean": "yes"}, "worktree_clean"),
        ({"engine": {}}, "engine"),
    ],
)
def test_run_identity_is_enforced(
    files: dict[str, Path], meta: dict[str, Any], message: str
) -> None:
    cases, documents = _ctx(files)
    path = _run_file(files, RESULTS_FIRST, **meta)
    with pytest.raises(EvaluationInputError, match=message):
        metrics.load_run(path, cases, metrics.sha256_file(files["cases"]), documents)


def test_run_offsets_must_lie_inside_the_documents(files: dict[str, Path]) -> None:
    results = [dict(RESULTS_FIRST[0], evidence=[_ev("reg-b", 0, 999, "supports")])]
    with pytest.raises(EvaluationInputError, match="offsets outside"):
        _run(files, results + RESULTS_FIRST[1:])
    results = [dict(RESULTS_FIRST[0], evidence=[_ev("reg-z", 0, 5, "supports")])]
    with pytest.raises(EvaluationInputError, match="unknown document_id"):
        _run(files, results + RESULTS_FIRST[1:])


def test_missing_results_are_rejected(files: dict[str, Path]) -> None:
    with pytest.raises(EvaluationInputError, match="missing results"):
        _run(files, RESULTS_FIRST[:2])


def test_annotations_are_bound_to_the_exact_document_text(files: dict[str, Path]) -> None:
    tampered = dict(PAIRS[0], passage_sha256=metrics.passage_sha256("outro texto"))
    with pytest.raises(EvaluationInputError, match="passage_sha256"):
        _annotations(files, [tampered])
    with pytest.raises(EvaluationInputError, match="not adjudicated"):
        _annotations(files, [dict(PAIRS[0], adjudicated=False)])
    with pytest.raises(EvaluationInputError, match="relation_b"):
        _annotations(files, [{k: v for k, v in PAIRS[0].items() if k != "relation_b"}])


def test_independent_universe_must_cover_every_case(files: dict[str, Path]) -> None:
    with pytest.raises(EvaluationInputError, match="no passage for"):
        _annotations(files, UNIVERSE[:2], every_case=True)


# --------------------------------------------------------------------------- metrics


def test_score_separates_pool_and_independent_recall(files: dict[str, Path]) -> None:
    cases, _ = _ctx(files)
    report = metrics.score(
        _run(files, RESULTS_FIRST),
        cases,
        _annotations(files, PAIRS),
        _annotations(files, UNIVERSE, every_case=True),
        iterations=200,
    )
    m = report["metrics"]
    assert m["recall_relevant_in_pool"]["value"] == 1.0
    assert m["recall_relevant_independent"]["value"] == 4 / 5  # art. 3 exception missed
    assert m["retrieval_coverage_independent"]["value"] == 1.0
    assert m["relevance_precision_at_k"]["value"] == 4 / 6
    assert m["false_contradicts_on_unrelated"]["value"] == 0.5
    assert m["contradicts_precision"]["value"] == 2 / 3
    assert m["contradicts_recall"]["value"] == 1.0
    assert m["contradicts_precision_sem_relacao"]["value"] == 0.0
    assert m["false_refuted_or_conflicting_on_supports"]["value"] == 0.5
    assert m["abstention_rate"]["value"] == 0.0
    assert report["run"]["commit"] == COMMIT
    assert report["run"]["documents_sha256"] == metrics.sha256_file(files["documents"])
    assert report["agreement"]["pool"]["relation_kappa"] == 1.0
    assert report["bootstrap"]["unit"] == "cluster_id"
    assert m["false_refuted_or_conflicting_on_supports"]["clusters"] == 2


def test_contradiction_metrics_keep_refuted_and_conflicting_apart(
    files: dict[str, Path],
) -> None:
    cases, _ = _ctx(files)
    report = metrics.score(
        _run(files, RESULTS_FIRST), cases, _annotations(files, PAIRS), iterations=50
    )
    m = report["metrics"]
    assert m["contradiction_detected_on_contradicts"]["value"] == 1.0  # refuted or conflicting
    assert m["decisive_refutation_on_contradicts"]["value"] == 0.5  # refuted only
    assert m["conflicting_on_contradicts"]["value"] == 0.5


def test_independent_metrics_are_not_reported_without_a_universe(
    files: dict[str, Path],
) -> None:
    cases, _ = _ctx(files)
    report = metrics.score(
        _run(files, RESULTS_FIRST), cases, _annotations(files, PAIRS), iterations=10
    )
    m = report["metrics"]
    for name in metrics.INDEPENDENT_METRICS:
        assert m[name]["value"] is None
        assert m[name]["status"].startswith("not measured")
    assert m["recall_relevant_in_pool"]["value"] == 1.0


def test_score_is_deterministic_for_a_seed(files: dict[str, Path]) -> None:
    cases, _ = _ctx(files)
    pairs = _annotations(files, PAIRS)
    first = metrics.score(_run(files, RESULTS_FIRST), cases, pairs, iterations=300, seed=7)
    second = metrics.score(_run(files, RESULTS_FIRST), cases, pairs, iterations=300, seed=7)
    assert first == second


def test_unannotated_evidence_blocks_scoring(files: dict[str, Path]) -> None:
    cases, _ = _ctx(files)
    with pytest.raises(EvaluationInputError, match="not annotated"):
        metrics.score(
            _run(files, RESULTS_FIRST), cases, _annotations(files, PAIRS[:-1]), iterations=10
        )


def test_compare_is_paired_by_claim(files: dict[str, Path]) -> None:
    cases, _ = _ctx(files)
    report = metrics.compare(
        _run(files, RESULTS_FIRST, "current"),
        _run(files, RESULTS_SECOND, "candidate"),
        cases,
        _annotations(files, PAIRS),
        _annotations(files, UNIVERSE, every_case=True),
        iterations=200,
    )
    diff = report["differences"]["false_refuted_or_conflicting_on_supports"]
    assert (diff["first"], diff["second"], diff["difference"]) == (0.5, 0.0, -0.5)
    decisive = report["differences"]["decisive_refutation_on_contradicts"]
    assert (decisive["first"], decisive["second"]) == (0.5, 1.0)
    discordant = report["discordant_claims"]
    assert discordant["supports_contradictory_verdict"] == {"only_first": 1, "only_second": 0}
    assert discordant["contradicts_refuted"] == {"only_first": 0, "only_second": 1}
    assert discordant["abstained"] == {"only_first": 0, "only_second": 1}
    assert report["first"]["variant"] == "current"
    assert report["second"]["commit"] == COMMIT


def test_compare_refuses_runs_on_different_documents(files: dict[str, Path]) -> None:
    cases, _ = _ctx(files)
    first = _run(files, RESULTS_FIRST, "current")
    second = metrics.Run(**{**first.__dict__, "documents_sha256": "f" * 64})
    with pytest.raises(EvaluationInputError, match="different document files"):
        metrics.compare(first, second, cases, _annotations(files, PAIRS), iterations=10)


def test_pool_is_blind_and_carries_passage_hashes(files: dict[str, Path]) -> None:
    cases, documents = _ctx(files)
    rows = metrics.pool(
        cases,
        [_run(files, RESULTS_FIRST, "a"), _run(files, RESULTS_SECOND, "b")],
        documents,
    )
    assert len(rows) == 6
    expected = {
        "case_id",
        "claim",
        "document_id",
        "documents_sha256",
        "start",
        "end",
        "passage",
        "passage_sha256",
    }
    assert all(set(row) == expected for row in rows)
    assert all(row["passage_sha256"] == metrics.passage_sha256(row["passage"]) for row in rows)


def test_cohen_kappa() -> None:
    assert metrics.cohen_kappa(["a", "b", "a", "b"], ["a", "b", "a", "b"]) == 1.0
    assert metrics.cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0
    assert metrics.cohen_kappa([], []) is None
    assert metrics.cohen_kappa(["a", "a"], ["a", "a"]) is None


# --------------------------------------------------------------------------- runner and CLI


def test_run_system_end_to_end(files: dict[str, Path], tmp_path: Path) -> None:
    out = tmp_path / "run.json"
    report = run_system.run(files["cases"], files["documents"], "current", allow_dirty=True)
    out.write_text(json.dumps(report), "utf-8")
    meta = report["meta"]
    commit, clean = run_system.source_state()
    assert (meta["commit"], meta["worktree_clean"]) == (commit, clean)
    assert meta["cases_sha256"] == metrics.sha256_file(files["cases"])
    assert meta["documents_sha256"] == metrics.sha256_file(files["documents"])
    assert meta["engine"]["judge"] == "ADR-002"
    assert [row["case_id"] for row in report["results"]] == ["c1", "c2", "c3", "c4"]
    cases, documents = _ctx(files)
    run = metrics.load_run(out, cases, metrics.sha256_file(files["cases"]), documents)
    rows = metrics.pool(cases, [run], documents)
    assert rows and all("stance" not in row and "verdict" not in row for row in rows)
    with pytest.raises(EvaluationInputError, match="unknown variant"):
        run_system.run(files["cases"], files["documents"], "tuned", allow_dirty=True)


def test_run_system_refuses_a_dirty_worktree(
    files: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(run_system, "source_state", lambda: (COMMIT, False))
    with pytest.raises(EvaluationInputError, match="uncommitted changes"):
        run_system.run(files["cases"], files["documents"], "current")
    report = run_system.run(files["cases"], files["documents"], "current", allow_dirty=True)
    assert report["meta"]["worktree_clean"] is False


def test_cli_score_and_compare(files: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    first = _run_file(files, RESULTS_FIRST, "current")
    second = _run_file(files, RESULTS_SECOND, "candidate")
    pairs = _write_jsonl(files["cases"].parent / "pairs.jsonl", PAIRS)
    universe = _write_jsonl(files["cases"].parent / "universe.jsonl", UNIVERSE)
    base = ["--cases", str(files["cases"]), "--documents", str(files["documents"])]
    base += ["--pairs", str(pairs), "--universe", str(universe), "--iterations", "50"]
    assert metrics.main(["score", *base, "--run", str(first)]) == 0
    scored = json.loads(capsys.readouterr().out)
    assert scored["metrics"]["recall_relevant_independent"]["value"] == 4 / 5
    assert metrics.main(["compare", *base, "--run", str(first), "--run", str(second)]) == 0
    compared = json.loads(capsys.readouterr().out)
    assert (compared["first"]["variant"], compared["second"]["variant"]) == (
        "current",
        "candidate",
    )


class _RecordingReader:
    """Binary file wrapper that records every byte range read."""

    def __init__(self, path: Path) -> None:
        self._handle = path.open("rb")
        self.ranges: list[tuple[int, int]] = []

    def __enter__(self) -> _RecordingReader:
        return self

    def __exit__(self, *_: object) -> None:
        self._handle.close()

    def seek(self, offset: int) -> int:
        return self._handle.seek(offset)

    def read(self, size: int = -1) -> bytes:
        start = self._handle.tell()
        data = self._handle.read(size)
        self.ranges.append((start, start + len(data)))
        return data


def test_exploratory_script_never_reads_test_records() -> None:
    from evals.passage_relation import exploratory_ptcp_dev

    readers: list[_RecordingReader] = []

    def opener(path: Path) -> Any:
        readers.append(_RecordingReader(path))
        return readers[-1]

    cases = exploratory_ptcp_dev.dev_cases(opener=opener)
    index = json.loads(exploratory_ptcp_dev.DEV_INDEX.read_text("utf-8"))
    allowed = [(e["offset"], e["offset"] + e["length"]) for e in index["lines"]]
    (reader,) = readers
    # Every byte read lies inside an indexed DEV line, and nothing else was read.
    assert reader.ranges == allowed
    assert all(case["split"] == "dev" for case in cases)
    assert {case["label"] for case in cases} == {"supports", "contradicts"}
    assert len(cases) == 70
    assert index["source_sha256"] == (
        "3aa702bc7bd04185389d9201e619ca7637508a5fb1aac774bdf642bf4362382c"
    )  # SHA-256 of cases.jsonl recorded in evals/pt-cp-audit/README.md


def test_dev_index_rejects_bytes_that_changed(tmp_path: Path) -> None:
    from evals.passage_relation import exploratory_ptcp_dev

    index = json.loads(exploratory_ptcp_dev.DEV_INDEX.read_text("utf-8"))
    index["lines"][0]["sha256"] = "0" * 64
    tampered = tmp_path / "index.json"
    tampered.write_text(json.dumps(index), "utf-8")
    with pytest.raises(RuntimeError, match="bytes differ"):
        exploratory_ptcp_dev.dev_cases(tampered)


def test_exploratory_measurement_is_dev_only() -> None:
    from evals.passage_relation import exploratory_ptcp_dev

    report = exploratory_ptcp_dev.measure()
    assert report["exploratory"] is True
    assert report["split"] == "dev"
    assert report["cases"] == 70
