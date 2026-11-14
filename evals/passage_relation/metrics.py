"""Passage-relation evaluation for /v1/check (protocol PROTOCOL-PASSAGE-RELATION-v0, [PROPOSTO]).

Question: do retrieved passages that a person judges materially unrelated to a claim
turn true claims into REFUTED or CONFLICTING, and does a candidate variant reduce that
without losing legitimate contradictions (exceptions, restrictions, definitions,
cross-references)?

Inputs are files written by people (cases, pooled-passage annotations and the
independent passage universe) and by the system (runs). This module never writes,
completes or labels a case. Every input is bound by SHA-256: a run to its case and
document files, each annotated passage to the exact document text it covers.

Two passage sets are kept apart:
- the pool: union of the passages the evaluated variants cited, annotated blind to
  their stances and verdicts. Recall over the pool is conditional on the variants.
- the independent universe: passages people mark as candidates for each claim by
  reading the documents, before and without any run. Recall over it does not depend on
  the variants, but it is recall over the annotated universe, not over every relevant
  passage that may exist.

Subcommands:
    pool    passages to annotate, from one or more runs, WITHOUT stances or verdicts
    score   metrics of one run, with cluster-bootstrap intervals
    compare paired comparison of two runs on the same cases and documents

Usage:
    python -m evals.passage_relation.metrics pool --cases C --documents D --runs R1 R2 --out P
    python -m evals.passage_relation.metrics score --cases C --documents D --pairs P \
        [--universe U] --run R
    python -m evals.passage_relation.metrics compare --cases C --documents D --pairs P \
        [--universe U] --run R1 --run R2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "passage-relation-v0"
CLAIM_LABELS = ("supports", "contradicts", "neutral")
STANCES = ("supports", "contradicts", "neutral")
RELATIONS = (
    "direta",
    "excecao_restricao",
    "definicao_abrangencia",
    "remissao",
    "sem_relacao",
)
ABSTENTION = {None, "unverified"}
CONTRADICTION_VERDICTS = {"refuted", "conflicting"}
DEFAULT_ITERATIONS = 10_000
DEFAULT_SEED = 20261003
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")

Key = tuple[str, str, int, int]  # case_id, document_id, start, end


class EvaluationInputError(ValueError):
    """Input files violate the protocol; nothing is scored."""


@dataclass(frozen=True)
class Case:
    case_id: str
    cluster_id: str
    claim: str
    label: str


@dataclass(frozen=True)
class Documents:
    texts: Mapping[str, str]
    sha256: str


@dataclass(frozen=True)
class PairAnnotation:
    key: Key
    relation: str
    stance: str
    relation_a: str
    relation_b: str
    stance_a: str
    stance_b: str


@dataclass(frozen=True)
class EvidenceItem:
    key: Key
    stance: str


@dataclass(frozen=True)
class ClaimRun:
    case_id: str
    verdict: str | None
    evidence: tuple[EvidenceItem, ...]


@dataclass(frozen=True)
class Run:
    variant: str
    commit: str
    worktree_clean: bool
    cases_sha256: str
    documents_sha256: str
    engine: Mapping[str, str]
    results: Mapping[str, ClaimRun]


# --------------------------------------------------------------------------- loading


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def passage_sha256(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise EvaluationInputError(f"{path.name}:{number}: invalid JSON ({error})") from error
        if not isinstance(row, dict):
            raise EvaluationInputError(f"{path.name}:{number}: each line must be an object")
        rows.append(row)
    return rows


def _text(row: Mapping[str, Any], field: str, where: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise EvaluationInputError(f"{where}: {field} must be a non-empty canonical string")
    return value


def _choice(row: Mapping[str, Any], field: str, allowed: Sequence[str], where: str) -> str:
    value = row.get(field)
    if value not in allowed:
        raise EvaluationInputError(f"{where}: {field} must be one of {list(allowed)}")
    return str(value)


def _offset(row: Mapping[str, Any], field: str, where: str) -> int:
    value = row.get(field)
    if type(value) is not int or value < 0:
        raise EvaluationInputError(f"{where}: {field} must be a non-negative integer")
    return value


def _key(row: Mapping[str, Any], case_id: str, documents: Documents, where: str) -> Key:
    document_id = _text(row, "document_id", where)
    start, end = _offset(row, "start", where), _offset(row, "end", where)
    if document_id not in documents.texts:
        raise EvaluationInputError(f"{where}: unknown document_id {document_id!r}")
    if not start < end <= len(documents.texts[document_id]):
        raise EvaluationInputError(f"{where}: offsets outside document {document_id!r}")
    return case_id, document_id, start, end


def load_cases(path: Path) -> dict[str, Case]:
    """Human-written, adjudicated cases. Every case must say adjudicated: true."""

    cases: dict[str, Case] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        where = f"{path.name} case {index}"
        case_id = _text(row, "case_id", where)
        if case_id in cases:
            raise EvaluationInputError(f"{where}: duplicate case_id {case_id!r}")
        if row.get("adjudicated") is not True:
            raise EvaluationInputError(f"{where}: case {case_id} is not adjudicated")
        cases[case_id] = Case(
            case_id=case_id,
            cluster_id=_text(row, "cluster_id", where),
            claim=_text(row, "claim", where),
            label=_choice(row, "label", CLAIM_LABELS, where),
        )
    if not cases:
        raise EvaluationInputError(f"{path.name}: no cases")
    return cases


def load_documents(path: Path) -> Documents:
    texts: dict[str, str] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        where = f"{path.name} document {index}"
        document_id = _text(row, "document_id", where)
        text = row.get("text")
        if not isinstance(text, str) or not text:
            raise EvaluationInputError(f"{where}: text must be a non-empty string")
        if document_id in texts:
            raise EvaluationInputError(f"{where}: duplicate document_id {document_id!r}")
        texts[document_id] = text
    if not texts:
        raise EvaluationInputError(f"{path.name}: no documents")
    return Documents(texts, sha256_file(path))


def load_annotations(
    path: Path, cases: Mapping[str, Case], documents: Documents, *, every_case: bool = False
) -> dict[Key, PairAnnotation]:
    """Two independent annotations per passage plus the adjudicated value. Each row
    carries passage_sha256 of the exact text it covers; a mismatch means the passage
    was annotated on other document text and the file is refused."""

    pairs: dict[Key, PairAnnotation] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        where = f"{path.name} passage {index}"
        case_id = _text(row, "case_id", where)
        if case_id not in cases:
            raise EvaluationInputError(f"{where}: unknown case_id {case_id!r}")
        if row.get("adjudicated") is not True:
            raise EvaluationInputError(f"{where}: passage is not adjudicated")
        key = _key(row, case_id, documents, where)
        if key in pairs:
            raise EvaluationInputError(f"{where}: duplicate passage for case {case_id}")
        _, document_id, start, end = key
        if row.get("passage_sha256") != passage_sha256(documents.texts[document_id][start:end]):
            raise EvaluationInputError(f"{where}: passage_sha256 does not match the documents")
        pairs[key] = PairAnnotation(
            key=key,
            relation=_choice(row, "relation", RELATIONS, where),
            stance=_choice(row, "stance", STANCES, where),
            relation_a=_choice(row, "relation_a", RELATIONS, where),
            relation_b=_choice(row, "relation_b", RELATIONS, where),
            stance_a=_choice(row, "stance_a", STANCES, where),
            stance_b=_choice(row, "stance_b", STANCES, where),
        )
    if every_case:
        missing = sorted(set(cases) - {key[0] for key in pairs})
        if missing:
            raise EvaluationInputError(
                f"{path.name}: the independent universe has no passage for {missing[:5]}"
            )
    return pairs


def load_run(path: Path, cases: Mapping[str, Case], cases_sha256: str, documents: Documents) -> Run:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise EvaluationInputError(f"{path.name}: schema must be {SCHEMA!r}")
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raise EvaluationInputError(f"{path.name}: meta is required")
    where = f"{path.name} meta"
    variant = _text(meta, "variant", where)
    if meta.get("cases_sha256") != cases_sha256:
        raise EvaluationInputError(
            f"{path.name}: run was produced for another case file "
            f"({meta.get('cases_sha256')!r} != {cases_sha256!r})"
        )
    if meta.get("documents_sha256") != documents.sha256:
        raise EvaluationInputError(
            f"{path.name}: run was produced for another document file "
            f"({meta.get('documents_sha256')!r} != {documents.sha256!r})"
        )
    commit = meta.get("commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise EvaluationInputError(f"{where}: commit must be a full 40-character SHA-1")
    if not isinstance(meta.get("worktree_clean"), bool):
        raise EvaluationInputError(f"{where}: worktree_clean must be a boolean")
    engine = meta.get("engine")
    if (
        not isinstance(engine, dict)
        or not engine
        or not all(isinstance(k, str) and isinstance(v, str) for k, v in engine.items())
    ):
        raise EvaluationInputError(f"{where}: engine must map strings to strings")
    results: dict[str, ClaimRun] = {}
    for index, row in enumerate(raw.get("results") or [], start=1):
        where = f"{path.name} result {index}"
        if not isinstance(row, dict):
            raise EvaluationInputError(f"{where}: must be an object")
        case_id = _text(row, "case_id", where)
        if case_id not in cases:
            raise EvaluationInputError(f"{where}: unknown case_id {case_id!r}")
        if case_id in results:
            raise EvaluationInputError(f"{where}: duplicate case_id {case_id!r}")
        verdict = row.get("verdict")
        if verdict is not None and not isinstance(verdict, str):
            raise EvaluationInputError(f"{where}: verdict must be a string or null")
        evidence = []
        for item in row.get("evidence") or []:
            if not isinstance(item, dict):
                raise EvaluationInputError(f"{where}: evidence items must be objects")
            evidence.append(
                EvidenceItem(
                    _key(item, case_id, documents, where),
                    _choice(item, "stance", STANCES, where),
                )
            )
        results[case_id] = ClaimRun(case_id, verdict.lower() if verdict else None, tuple(evidence))
    missing = sorted(set(cases) - set(results))
    if missing:
        raise EvaluationInputError(f"{path.name}: missing results for {missing[:5]}")
    return Run(
        variant=variant,
        commit=commit,
        worktree_clean=meta["worktree_clean"],
        cases_sha256=cases_sha256,
        documents_sha256=documents.sha256,
        engine=dict(engine),
        results=results,
    )


def run_identity(run: Run) -> dict[str, Any]:
    return {
        "variant": run.variant,
        "commit": run.commit,
        "worktree_clean": run.worktree_clean,
        "cases_sha256": run.cases_sha256,
        "documents_sha256": run.documents_sha256,
        "engine": dict(run.engine),
    }


# --------------------------------------------------------------------------- pooling


def pool(
    cases: Mapping[str, Case], runs: Iterable[Run], documents: Documents
) -> list[dict[str, Any]]:
    """Union of cited passages, blind: claim and passage text only, sorted."""

    keys: set[Key] = set()
    for run in runs:
        if run.documents_sha256 != documents.sha256:
            raise EvaluationInputError(f"run {run.variant} used other documents")
        for result in run.results.values():
            keys.update(item.key for item in result.evidence)
    rows = []
    for case_id, document_id, start, end in sorted(keys):
        passage = documents.texts[document_id][start:end]
        rows.append(
            {
                "case_id": case_id,
                "claim": cases[case_id].claim,
                "document_id": document_id,
                "documents_sha256": documents.sha256,
                "start": start,
                "end": end,
                "passage": passage,
                "passage_sha256": passage_sha256(passage),
            }
        )
    return rows


# --------------------------------------------------------------------------- metrics


def _overlaps(left: Key, right: Key) -> bool:
    return left[1] == right[1] and left[2] < right[3] and right[2] < left[3]


def _per_case(
    run: Run,
    pairs: Mapping[Key, PairAnnotation],
    universe: Mapping[Key, PairAnnotation] | None,
    case: Case,
) -> dict[str, int]:
    """Counts for one claim; metrics are ratios of sums, so they bootstrap by cluster."""

    result = run.results[case.case_id]
    counts: Counter[str] = Counter()
    cited = [item.key for item in result.evidence]
    for item in result.evidence:
        pair = pairs.get(item.key)
        if pair is None:
            counts["unannotated_evidence"] += 1
            continue
        system_contradicts = item.stance == "contradicts"
        human_contradicts = pair.stance == "contradicts"
        counts["retrieved"] += 1
        counts["retrieved_relevant"] += pair.relation != "sem_relacao"
        if pair.relation == "sem_relacao":
            counts["unrelated_retrieved"] += 1
            counts["unrelated_false_contradicts"] += system_contradicts
        for suffix in ("", f"_{pair.relation}"):
            counts[f"system_contradicts{suffix}"] += system_contradicts
            counts[f"human_contradicts{suffix}"] += human_contradicts
            counts[f"both_contradicts{suffix}"] += system_contradicts and human_contradicts

    relevant_pool = {key for key, pair in pairs.items() if key[0] == case.case_id}
    relevant_pool = {key for key in relevant_pool if pairs[key].relation != "sem_relacao"}
    counts["pool_relevant"] = len(relevant_pool)
    counts["pool_relevant_cited"] = len(relevant_pool & set(cited))

    if universe is not None:
        units = [
            key
            for key, unit in universe.items()
            if key[0] == case.case_id and unit.relation != "sem_relacao"
        ]
        hit = sum(any(_overlaps(unit, key) for key in cited) for unit in units)
        counts["universe_relevant"] = len(units)
        counts["universe_relevant_cited"] = hit
        counts["universe_cases"] = bool(units)
        counts["universe_cases_covered"] = bool(units) and hit > 0

    verdict = result.verdict
    counts[f"label_{case.label}"] = 1
    counts["abstained"] = verdict in ABSTENTION
    if case.label == "supports":
        counts["supports_contradictory_verdict"] = verdict in CONTRADICTION_VERDICTS
    if case.label == "contradicts":
        counts["contradicts_detected"] = verdict in CONTRADICTION_VERDICTS
        counts["contradicts_refuted"] = verdict == "refuted"
        counts["contradicts_conflicting"] = verdict == "conflicting"
    return dict(counts)


# name: (numerator, denominator) over summed per-case counts
METRICS: dict[str, tuple[str, str]] = {
    # retrieval, independent annotated universe (not conditional on the variants)
    "recall_relevant_independent": ("universe_relevant_cited", "universe_relevant"),
    "retrieval_coverage_independent": ("universe_cases_covered", "universe_cases"),
    # retrieval, pool of cited passages (conditional on the evaluated variants)
    "recall_relevant_in_pool": ("pool_relevant_cited", "pool_relevant"),
    "relevance_precision_at_k": ("retrieved_relevant", "retrieved"),
    # passage stances
    "false_contradicts_on_unrelated": ("unrelated_false_contradicts", "unrelated_retrieved"),
    "contradicts_precision": ("both_contradicts", "system_contradicts"),
    "contradicts_recall": ("both_contradicts", "human_contradicts"),
    # claim verdicts
    "false_refuted_or_conflicting_on_supports": (
        "supports_contradictory_verdict",
        "label_supports",
    ),
    "contradiction_detected_on_contradicts": ("contradicts_detected", "label_contradicts"),
    "decisive_refutation_on_contradicts": ("contradicts_refuted", "label_contradicts"),
    "conflicting_on_contradicts": ("contradicts_conflicting", "label_contradicts"),
    "abstention_rate": ("abstained", "cases"),
}
for _relation in RELATIONS:
    METRICS[f"contradicts_precision_{_relation}"] = (
        f"both_contradicts_{_relation}",
        f"system_contradicts_{_relation}",
    )
    METRICS[f"contradicts_recall_{_relation}"] = (
        f"both_contradicts_{_relation}",
        f"human_contradicts_{_relation}",
    )
INDEPENDENT_METRICS = ("recall_relevant_independent", "retrieval_coverage_independent")


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _value(totals: Mapping[str, int], name: str) -> float | None:
    numerator, denominator = METRICS[name]
    return _ratio(totals.get(numerator, 0), totals.get(denominator, 0))


def _sum(rows: Iterable[Mapping[str, int]]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for row in rows:
        totals.update(row)
        totals["cases"] += 1
    return totals


def _percentile_interval(values: list[float]) -> tuple[float, float] | None:
    # Same order-statistic convention as evals/ptbr/rgc_eval.py (no interpolation).
    if not values:
        return None
    values = sorted(values)
    count = len(values)
    return values[int(0.025 * (count - 1))], values[int(0.975 * (count - 1))]


def cluster_bootstrap(
    case_ids: Iterable[str],
    cases: Mapping[str, Case],
    statistic: Callable[[list[str]], float | None],
    *,
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    """Percentile interval resampling whole clusters (one legal instrument or provision
    per cluster); undefined replicates are excluded and reported."""

    clusters: dict[str, list[str]] = defaultdict(list)
    for case_id in sorted(case_ids):
        clusters[cases[case_id].cluster_id].append(case_id)
    names = sorted(clusters)
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(iterations):
        sample = [case_id for _ in names for case_id in clusters[rng.choice(names)]]
        value = statistic(sample)
        if value is not None:
            values.append(value)
    return {
        "ci95": _percentile_interval(values),
        "valid_replicates": len(values),
        "undefined_replicates": iterations - len(values),
        "clusters": len(names),
    }


def _check_annotated(*tables: Mapping[str, Mapping[str, int]]) -> None:
    missing = sum(row.get("unannotated_evidence", 0) for table in tables for row in table.values())
    if missing:
        raise EvaluationInputError(
            f"{missing} cited passages are not annotated; pool every run before annotation"
        )


def _not_measured(name: str, universe: Mapping[Key, PairAnnotation] | None) -> str | None:
    if universe is None and name in INDEPENDENT_METRICS:
        return "not measured: no independent universe was provided"
    return None


def score(
    run: Run,
    cases: Mapping[str, Case],
    pairs: Mapping[Key, PairAnnotation],
    universe: Mapping[Key, PairAnnotation] | None = None,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    per_case = {cid: _per_case(run, pairs, universe, case) for cid, case in cases.items()}
    _check_annotated(per_case)
    totals = _sum(per_case.values())
    metrics: dict[str, Any] = {}
    for name in METRICS:
        reason = _not_measured(name, universe)
        if reason:
            metrics[name] = {"value": None, "status": reason}
            continue
        point = _value(totals, name)

        def statistic(sample: list[str], name: str = name) -> float | None:
            return _value(_sum(per_case[case_id] for case_id in sample), name)

        metrics[name] = {
            "value": point,
            "numerator": totals.get(METRICS[name][0], 0),
            "denominator": totals.get(METRICS[name][1], 0),
            **(
                cluster_bootstrap(cases, cases, statistic, iterations=iterations, seed=seed)
                if point is not None
                else {"ci95": None}
            ),
        }
    return {
        "schema": SCHEMA,
        "run": run_identity(run),
        "cases": len(cases),
        "bootstrap": {"iterations": iterations, "seed": seed, "unit": "cluster_id"},
        "agreement": {
            "pool": agreement(pairs),
            "independent_universe": agreement(universe) if universe is not None else None,
        },
        "metrics": metrics,
    }


def compare(
    first: Run,
    second: Run,
    cases: Mapping[str, Case],
    pairs: Mapping[Key, PairAnnotation],
    universe: Mapping[Key, PairAnnotation] | None = None,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Paired by claim: differences second - first, with cluster-bootstrap intervals and
    discordant counts for the claim-level outcomes. No decision rule is applied here;
    the endpoint and margin belong to the registered protocol."""

    if first.cases_sha256 != second.cases_sha256:
        raise EvaluationInputError("runs were produced for different case files")
    if first.documents_sha256 != second.documents_sha256:
        raise EvaluationInputError("runs were produced for different document files")
    a = {cid: _per_case(first, pairs, universe, case) for cid, case in cases.items()}
    b = {cid: _per_case(second, pairs, universe, case) for cid, case in cases.items()}
    _check_annotated(a, b)
    differences: dict[str, Any] = {}
    for name in METRICS:
        reason = _not_measured(name, universe)
        if reason:
            differences[name] = {"difference": None, "status": reason}
            continue

        def statistic(sample: list[str], name: str = name) -> float | None:
            left = _value(_sum(a[c] for c in sample), name)
            right = _value(_sum(b[c] for c in sample), name)
            return None if left is None or right is None else right - left

        point = statistic(sorted(cases))
        differences[name] = {
            "first": _value(_sum(a.values()), name),
            "second": _value(_sum(b.values()), name),
            "difference": point,
            **(
                cluster_bootstrap(cases, cases, statistic, iterations=iterations, seed=seed)
                if point is not None
                else {"ci95": None}
            ),
        }
    discordant: dict[str, dict[str, int]] = {}
    for field in (
        "supports_contradictory_verdict",
        "contradicts_detected",
        "contradicts_refuted",
        "abstained",
    ):
        only_first = sum(bool(a[c].get(field)) and not b[c].get(field) for c in cases)
        only_second = sum(bool(b[c].get(field)) and not a[c].get(field) for c in cases)
        discordant[field] = {"only_first": only_first, "only_second": only_second}
    return {
        "schema": SCHEMA,
        "first": run_identity(first),
        "second": run_identity(second),
        "bootstrap": {"iterations": iterations, "seed": seed, "unit": "cluster_id"},
        "differences": differences,
        "discordant_claims": discordant,
    }


def cohen_kappa(left: Sequence[str], right: Sequence[str]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    total = len(left)
    observed = sum(x == y for x, y in zip(left, right, strict=True)) / total
    counts_left, counts_right = Counter(left), Counter(right)
    expected = sum(counts_left[k] * counts_right[k] for k in counts_left) / (total * total)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def agreement(pairs: Mapping[Key, PairAnnotation]) -> dict[str, Any]:
    items = list(pairs.values())
    return {
        "passages": len(items),
        "relation_kappa": cohen_kappa([p.relation_a for p in items], [p.relation_b for p in items]),
        "stance_kappa": cohen_kappa([p.stance_a for p in items], [p.stance_b for p in items]),
    }


# --------------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pool_cmd = sub.add_parser("pool")
    pool_cmd.add_argument("--cases", type=Path, required=True)
    pool_cmd.add_argument("--documents", type=Path, required=True)
    pool_cmd.add_argument("--runs", type=Path, nargs="+", required=True)
    pool_cmd.add_argument("--out", type=Path, required=True)
    for name in ("score", "compare"):
        command = sub.add_parser(name)
        command.add_argument("--cases", type=Path, required=True)
        command.add_argument("--documents", type=Path, required=True)
        command.add_argument("--pairs", type=Path, required=True)
        command.add_argument("--universe", type=Path)
        command.add_argument("--run", type=Path, action="append", required=True, dest="runs")
        command.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
        command.add_argument("--seed", type=int, default=DEFAULT_SEED)
        command.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    documents = load_documents(args.documents)
    digest = sha256_file(args.cases)
    runs = [load_run(path, cases, digest, documents) for path in args.runs]
    if args.command == "pool":
        rows = pool(cases, runs, documents)
        args.out.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
        print(f"{len(rows)} passages to annotate -> {args.out}")
        return 0
    pairs = load_annotations(args.pairs, cases, documents)
    universe = (
        load_annotations(args.universe, cases, documents, every_case=True)
        if args.universe
        else None
    )
    if args.command == "score":
        if len(runs) != 1:
            parser.error("score takes exactly one --run")
        report = score(runs[0], cases, pairs, universe, iterations=args.iterations, seed=args.seed)
    else:
        if len(runs) != 2:
            parser.error("compare takes exactly two --run")
        report = compare(
            runs[0], runs[1], cases, pairs, universe, iterations=args.iterations, seed=args.seed
        )
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
