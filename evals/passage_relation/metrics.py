"""Passage-relation evaluation for /v1/check (protocol PROTOCOL-PASSAGE-RELATION-v0, [PROPOSTO]).

Question: do retrieved passages that a person judges materially unrelated to a claim
turn true claims into REFUTED or CONFLICTING, and does a candidate variant reduce that
without losing legitimate contradictions (exceptions, restrictions, definitions,
cross-references)?

Inputs are files written by people (cases and passage annotations) and by the system
(runs). This module never writes, completes or labels a case. It refuses to score a run
against a case set that is not fully adjudicated, or whose hash differs from the one
recorded in the run.

Subcommands:
    pool    passages to annotate, from one or more runs, WITHOUT stances or verdicts
    score   metrics of one run, with cluster-bootstrap intervals
    compare paired comparison of two runs on the same cases

Usage:
    python -m evals.passage_relation.metrics pool --cases C --documents D --runs R1 R2 --out P
    python -m evals.passage_relation.metrics score --cases C --pairs P --run R
    python -m evals.passage_relation.metrics compare --cases C --pairs P --run R1 --run R2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
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
    cases_sha256: str
    engine: Mapping[str, str]
    results: Mapping[str, ClaimRun]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _key(row: Mapping[str, Any], case_id: str, where: str) -> Key:
    start, end = _offset(row, "start", where), _offset(row, "end", where)
    if end <= start:
        raise EvaluationInputError(f"{where}: end must be greater than start")
    return case_id, _text(row, "document_id", where), start, end


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


def load_pairs(path: Path, cases: Mapping[str, Case]) -> dict[Key, PairAnnotation]:
    """Two independent annotations per pooled passage plus the adjudicated value."""

    pairs: dict[Key, PairAnnotation] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        where = f"{path.name} pair {index}"
        case_id = _text(row, "case_id", where)
        if case_id not in cases:
            raise EvaluationInputError(f"{where}: unknown case_id {case_id!r}")
        if row.get("adjudicated") is not True:
            raise EvaluationInputError(f"{where}: pair is not adjudicated")
        key = _key(row, case_id, where)
        if key in pairs:
            raise EvaluationInputError(f"{where}: duplicate passage for case {case_id}")
        pairs[key] = PairAnnotation(
            key=key,
            relation=_choice(row, "relation", RELATIONS, where),
            stance=_choice(row, "stance", STANCES, where),
            relation_a=_choice(row, "relation_a", RELATIONS, where),
            relation_b=_choice(row, "relation_b", RELATIONS, where),
            stance_a=_choice(row, "stance_a", STANCES, where),
            stance_b=_choice(row, "stance_b", STANCES, where),
        )
    return pairs


def load_run(path: Path, cases: Mapping[str, Case], cases_sha256: str) -> Run:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        raise EvaluationInputError(f"{path.name}: schema must be {SCHEMA!r}")
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raise EvaluationInputError(f"{path.name}: meta is required")
    variant = _text(meta, "variant", f"{path.name} meta")
    if meta.get("cases_sha256") != cases_sha256:
        raise EvaluationInputError(
            f"{path.name}: run was produced for another case file "
            f"({meta.get('cases_sha256')!r} != {cases_sha256!r})"
        )
    engine = meta.get("engine")
    if not isinstance(engine, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in engine.items()
    ):
        raise EvaluationInputError(f"{path.name}: meta.engine must map strings to strings")
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
                EvidenceItem(_key(item, case_id, where), _choice(item, "stance", STANCES, where))
            )
        results[case_id] = ClaimRun(case_id, verdict.lower() if verdict else None, tuple(evidence))
    missing = sorted(set(cases) - set(results))
    if missing:
        raise EvaluationInputError(f"{path.name}: missing results for {missing[:5]}")
    return Run(variant, cases_sha256, dict(engine), results)


# --------------------------------------------------------------------------- pooling


def pool(
    cases: Mapping[str, Case], runs: Iterable[Run], documents: Mapping[str, str]
) -> list[dict[str, Any]]:
    """Union of retrieved passages, blind: claim and passage text only, sorted."""

    keys: set[Key] = set()
    for run in runs:
        for result in run.results.values():
            keys.update(item.key for item in result.evidence)
    rows = []
    for case_id, document_id, start, end in sorted(keys):
        if document_id not in documents:
            raise EvaluationInputError(f"unknown document_id {document_id!r}")
        rows.append(
            {
                "case_id": case_id,
                "claim": cases[case_id].claim,
                "document_id": document_id,
                "start": start,
                "end": end,
                "passage": documents[document_id][start:end],
            }
        )
    return rows


# --------------------------------------------------------------------------- metrics


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _per_case(run: Run, pairs: Mapping[Key, PairAnnotation], case: Case) -> dict[str, int]:
    """Counts for one claim; metrics are ratios of sums, so they bootstrap by cluster."""

    result = run.results[case.case_id]
    pooled = [pair for key, pair in pairs.items() if key[0] == case.case_id]
    relevant_pool = {pair.key for pair in pooled if pair.relation != "sem_relacao"}
    counts: Counter[str] = Counter()
    retrieved_relevant = 0
    for item in result.evidence:
        pair = pairs.get(item.key)
        if pair is None:
            counts["unannotated_evidence"] += 1
            continue
        counts["retrieved"] += 1
        related = pair.relation != "sem_relacao"
        retrieved_relevant += related
        if pair.relation == "sem_relacao":
            counts["unrelated_retrieved"] += 1
            counts["unrelated_false_contradicts"] += item.stance == "contradicts"
        counts[f"system_contradicts_{pair.relation}"] += item.stance == "contradicts"
        counts[f"human_contradicts_{pair.relation}"] += pair.stance == "contradicts"
        counts[f"both_contradicts_{pair.relation}"] += (
            item.stance == "contradicts" and pair.stance == "contradicts"
        )
        counts["system_contradicts"] += item.stance == "contradicts"
        counts["both_contradicts"] += item.stance == "contradicts" and pair.stance == "contradicts"
        counts["retrieved_human_contradicts"] += pair.stance == "contradicts"
    counts["retrieved_relevant"] = retrieved_relevant
    if relevant_pool:
        counts["cases_with_relevant_pool"] = 1
        counts["relevant_pool"] = len(relevant_pool)
        counts["relevant_found"] = len(relevant_pool & {item.key for item in result.evidence})
    verdict = result.verdict
    counts[f"label_{case.label}"] = 1
    counts["abstained"] = verdict in ABSTENTION
    if case.label == "supports":
        counts["supports_false_contradiction_verdict"] = verdict in CONTRADICTION_VERDICTS
    if case.label == "contradicts":
        counts["contradicts_detected"] = verdict in CONTRADICTION_VERDICTS
    return dict(counts)


METRICS: dict[str, tuple[str, str]] = {
    # name: (numerator, denominator) over summed per-case counts
    "recall_relevant_at_k": ("relevant_found", "relevant_pool"),
    "relevance_precision_at_k": ("retrieved_relevant", "retrieved"),
    "false_contradicts_on_unrelated": ("unrelated_false_contradicts", "unrelated_retrieved"),
    "contradicts_precision": ("both_contradicts", "system_contradicts"),
    "contradicts_recall": ("both_contradicts", "retrieved_human_contradicts"),
    "false_refuted_or_conflicting_on_supports": (
        "supports_false_contradiction_verdict",
        "label_supports",
    ),
    "contradiction_detected_on_contradicts": ("contradicts_detected", "label_contradicts"),
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
    per_case: Mapping[str, Mapping[str, Any]],
    cases: Mapping[str, Case],
    statistic: Callable[[list[str]], float | None],
    *,
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    """Percentile interval resampling whole clusters (one legal instrument or provision
    per cluster); undefined replicates are excluded and reported."""

    clusters: dict[str, list[str]] = defaultdict(list)
    for case_id in sorted(per_case):
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


def score(
    run: Run,
    cases: Mapping[str, Case],
    pairs: Mapping[Key, PairAnnotation],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    per_case = {case_id: _per_case(run, pairs, case) for case_id, case in cases.items()}
    totals = _sum(per_case.values())
    if totals.get("unannotated_evidence"):
        raise EvaluationInputError(
            f"{totals['unannotated_evidence']} retrieved passages are not annotated; "
            "pool every run before annotation"
        )
    metrics: dict[str, Any] = {}
    for name in METRICS:
        point = _value(totals, name)

        def statistic(sample: list[str], name: str = name) -> float | None:
            return _value(_sum(per_case[case_id] for case_id in sample), name)

        metrics[name] = {
            "value": point,
            "numerator": totals.get(METRICS[name][0], 0),
            "denominator": totals.get(METRICS[name][1], 0),
            **(
                cluster_bootstrap(per_case, cases, statistic, iterations=iterations, seed=seed)
                if point is not None
                else {"ci95": None}
            ),
        }
    return {
        "schema": SCHEMA,
        "variant": run.variant,
        "engine": dict(run.engine),
        "cases_sha256": run.cases_sha256,
        "cases": len(cases),
        "bootstrap": {"iterations": iterations, "seed": seed, "unit": "cluster_id"},
        "agreement": agreement(pairs),
        "metrics": metrics,
    }


def compare(
    first: Run,
    second: Run,
    cases: Mapping[str, Case],
    pairs: Mapping[Key, PairAnnotation],
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Paired by claim: differences second - first, with cluster-bootstrap intervals and
    discordant counts for the claim-level outcomes. No decision rule is applied here;
    the endpoint and margin belong to the registered protocol."""

    if first.cases_sha256 != second.cases_sha256:
        raise EvaluationInputError("runs were produced for different case files")
    a = {case_id: _per_case(first, pairs, case) for case_id, case in cases.items()}
    b = {case_id: _per_case(second, pairs, case) for case_id, case in cases.items()}
    if _sum(a.values()).get("unannotated_evidence") or _sum(b.values()).get("unannotated_evidence"):
        raise EvaluationInputError("retrieved passages are not annotated; pool both runs")
    differences: dict[str, Any] = {}
    for name in METRICS:

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
                cluster_bootstrap(a, cases, statistic, iterations=iterations, seed=seed)
                if point is not None
                else {"ci95": None}
            ),
        }
    discordant: dict[str, dict[str, int]] = {}
    for field in ("supports_false_contradiction_verdict", "contradicts_detected", "abstained"):
        only_first = sum(bool(a[c].get(field)) and not b[c].get(field) for c in cases)
        only_second = sum(bool(b[c].get(field)) and not a[c].get(field) for c in cases)
        discordant[field] = {"only_first": only_first, "only_second": only_second}
    return {
        "schema": SCHEMA,
        "first": {"variant": first.variant, "engine": dict(first.engine)},
        "second": {"variant": second.variant, "engine": dict(second.engine)},
        "cases_sha256": first.cases_sha256,
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
        "pairs": len(items),
        "relation_kappa": cohen_kappa([p.relation_a for p in items], [p.relation_b for p in items]),
        "stance_kappa": cohen_kappa([p.stance_a for p in items], [p.stance_b for p in items]),
    }


# --------------------------------------------------------------------------- CLI


def load_documents(path: Path) -> dict[str, str]:
    documents: dict[str, str] = {}
    for index, row in enumerate(read_jsonl(path), start=1):
        where = f"{path.name} document {index}"
        document_id = _text(row, "document_id", where)
        text = row.get("text")
        if not isinstance(text, str) or not text:
            raise EvaluationInputError(f"{where}: text must be a non-empty string")
        if document_id in documents:
            raise EvaluationInputError(f"{where}: duplicate document_id {document_id!r}")
        documents[document_id] = text
    return documents


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    pool_cmd = sub.add_parser("pool")
    pool_cmd.add_argument("--cases", type=Path, required=True)
    pool_cmd.add_argument("--documents", type=Path, required=True)
    pool_cmd.add_argument("--runs", type=Path, nargs="+", required=True)
    pool_cmd.add_argument("--out", type=Path, required=True)
    for name in ("score", "compare"):
        command = sub.add_parser(name)
        command.add_argument("--cases", type=Path, required=True)
        command.add_argument("--pairs", type=Path, required=True)
        command.add_argument("--run", type=Path, action="append", required=True, dest="runs")
        command.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
        command.add_argument("--seed", type=int, default=DEFAULT_SEED)
        command.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    digest = sha256_file(args.cases)
    runs = [load_run(path, cases, digest) for path in args.runs]
    if args.command == "pool":
        rows = pool(cases, runs, load_documents(args.documents))
        args.out.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
        )
        print(f"{len(rows)} passages to annotate -> {args.out}")
        return 0
    pairs = load_pairs(args.pairs, cases)
    if args.command == "score":
        if len(runs) != 1:
            parser.error("score takes exactly one --run")
        report = score(runs[0], cases, pairs, iterations=args.iterations, seed=args.seed)
    else:
        if len(runs) != 2:
            parser.error("compare takes exactly two --run")
        report = compare(runs[0], runs[1], cases, pairs, iterations=args.iterations, seed=args.seed)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
