"""Deterministic evaluation runner for the PT-BR RGC benchmark.

Status: [PROPOSTO] — the configuration below is a proposal for the frozen
evaluation plan in docs/eval/RUNNER-RGC-v1.md. It is exercised only on
synthetic fixtures until the maintainer freezes it.

Pipeline per case (no learned component, no network):

1. Evidence
   * ``oracle`` mode: the case's own excerpts, checked byte-for-byte against
     the document text at the declared offsets.
   * ``retrieval`` mode: the document text is split into legal provisions
     (dispositivos: ``Art.``, ``§``, ``Parágrafo único``, incisos, alíneas),
     ranked with BM25 against the claim, and the top-k passages are used.
2. Stance: ``RuleStanceDetector`` on each (claim, passage) pair.
3. Verdict: Judge 2.0 ``adjudicate`` with one atom covering the whole claim,
   or with the annotated ``atoms`` of a compound claim (DEC-010, option A).

Cases marked ``rectified: true`` (Protocol Amendment 4, DEC-011 option A)
stay in the primary metrics and are also reported as a separate stratum.

Subcommands:
    run            evaluate cases against human labels and write a report
    export-corpus  write the strict 5-field corpus read by check_golden_pt.py

The ``run`` subcommand requires a labels file. There is no predictions-only
mode, so the system cannot be run on cases before they are labelled.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from typing import Any

from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue
from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.judge2 import adjudication
from ayorai_attractor.verification.models import Claim, Evidence
from ayorai_attractor.verification.stance import RuleStanceDetector

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = ROOT / "evals" / "ptbr" / "sources" / "DOCUMENTS.jsonl"

RUNNER_VERSION = "rgc-eval/0.3.0"
SEED = 20261003
BOOTSTRAP_ITERATIONS = 10000
DEFAULT_TOP_K = 3
BM25_K1 = 1.2
BM25_B = 0.75

JUDGE2_LABELS = ("SUPPORTED", "PARTIALLY_SUPPORTED", "REFUTED", "CONFLICTING", "UNVERIFIED")
ADR002_LABELS = ("VERIFIED", *JUDGE2_LABELS)
VOCABULARIES = {"judge2": JUDGE2_LABELS, "adr002": ADR002_LABELS}
# Gold labels that remove a case from the denominator; always reported.
EXCLUSION_LABELS = frozenset({"RULE_GAP"})
INVALID = "INVALID_PREDICTION"

STRICT_CORPUS_FIELDS = ("source_id", "source_url", "source_license", "retrieved_at", "text")

# Start of a legal provision at the beginning of a line.
PROVISION_RE = re.compile(r"(?m)^(?:Art\. ?\d+|§ ?\d+|Parágrafo único|[IVXLC]+ ?[-–]|[a-z]\) )")
ARTICLE_RE = re.compile(r"(?m)^Art\. ?\d+")
TOKEN_RE = re.compile(r"\w+")
# Function words only; no domain terms. Frozen with the runner.
STOPWORDS = frozenset(
    """
    ante após até com contra das dos desde entre para per perante por sem sob
    sobre trás que qual quais quando onde como mas nem ser são foi era está
    estão sua suas seu seus esta este isto essa esse isso aquela aquele aos
    pela pelas pelo pelos uma umas uns num numa nos nas the and
    """.split()
)


@dataclass(frozen=True)
class Document:
    source_id: str
    source_url: str
    retrieved_at: str
    text: str
    source_license: str


@dataclass(frozen=True)
class Passage:
    document_id: str
    start: int
    end: int


# ---------------------------------------------------------------- documents


def load_documents(path: Path = DOCUMENTS) -> dict[str, Document]:
    documents: dict[str, Document] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        text = str(raw["text"])
        declared = raw.get("text_sha256")
        if declared is not None and hashlib.sha256(text.encode()).hexdigest() != declared:
            raise ValueError(f"{raw['source_id']}: text_sha256 mismatch")
        if raw["source_id"] in documents:
            raise ValueError(f"duplicate document: {raw['source_id']}")
        documents[raw["source_id"]] = Document(
            source_id=str(raw["source_id"]),
            source_url=str(raw["source_url"]),
            retrieved_at=str(raw["retrieved_at"]),
            text=text,
            source_license=str(raw["source_license"]),
        )
    return documents


def export_strict_corpus(documents: Mapping[str, Document]) -> str:
    """Return the corpus JSONL with exactly the fields check_golden_pt.py accepts."""
    lines = []
    for doc in documents.values():
        record = {field: getattr(doc, field) for field in STRICT_CORPUS_FIELDS}
        lines.append(json.dumps(record, ensure_ascii=False))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------- segmenting


def segment(document: Document, granularity: str = "dispositivo") -> list[Passage]:
    """Split a document into contiguous passages that keep exact offsets.

    Leading text before the first boundary is its own passage. Trailing
    whitespace is trimmed from each passage so excerpts never end in blanks.
    """
    pattern = {"dispositivo": PROVISION_RE, "artigo": ARTICLE_RE}[granularity]
    text = document.text
    starts = sorted({0, *(m.start() for m in pattern.finditer(text))})
    passages = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        while end > start and text[end - 1].isspace():
            end -= 1
        lead = start
        while lead < end and text[lead].isspace():
            lead += 1
        if lead < end:
            passages.append(Passage(document.source_id, lead, end))
    return passages


# ---------------------------------------------------------------- retrieval


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in TOKEN_RE.findall(text.casefold()):
        if token.isdigit() or (len(token) >= 3 and token not in STOPWORDS):
            tokens.append(token)
    return tokens


class BM25Index:
    """Plain Okapi BM25 over passages; deterministic tie-break by corpus order."""

    def __init__(self, passages: Sequence[Passage], documents: Mapping[str, Document]):
        self.passages = list(passages)
        self.terms = [Counter(tokenize(_text(p, documents))) for p in self.passages]
        self.lengths = [sum(c.values()) for c in self.terms]
        n = len(self.passages)
        self.avg_length = (sum(self.lengths) / n) if n else 0.0
        df: Counter[str] = Counter()
        for counts in self.terms:
            df.update(counts.keys())
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int) -> list[tuple[Passage, float]]:
        query_terms = tokenize(query)
        scored = []
        for index, counts in enumerate(self.terms):
            score = 0.0
            norm = BM25_K1 * (1 - BM25_B + BM25_B * self.lengths[index] / self.avg_length)
            for term in query_terms:
                tf = counts.get(term, 0)
                if tf:
                    score += self.idf[term] * tf * (BM25_K1 + 1) / (tf + norm)
            if score > 0:
                scored.append((-round(score, 12), index))
        scored.sort()
        return [(self.passages[i], -s) for s, i in scored[:k]]


def _text(passage: Passage, documents: Mapping[str, Document]) -> str:
    return documents[passage.document_id].text[passage.start : passage.end]


# ------------------------------------------------------------------ predict


def oracle_passages(case: Mapping[str, Any], documents: Mapping[str, Document]) -> list[Passage]:
    passages = []
    for item in case["evidence"]:
        doc = documents[item["document_id"]]
        start, end = int(item["start_offset"]), int(item["end_offset"])
        if doc.text[start:end] != item["excerpt"]:
            raise ValueError(f"{case['case_id']}: excerpt does not match document offsets")
        passages.append(Passage(doc.source_id, start, end))
    return passages


def case_atoms(case: Mapping[str, Any]) -> list[tuple[int, int]] | None:
    """Return the annotated atom spans of a compound claim (DEC-010, option A).

    A case without ``atoms`` is a simple claim, adjudicated as one atom. When
    present, ``atoms`` must hold two or more spans of the claim text, given as
    ``start_offset``/``end_offset`` (optional ``text`` must match the span),
    sorted, non-overlapping and non-blank. Invalid annotation stops the run.
    """
    raw = case.get("atoms")
    if raw is None:
        return None
    case_id, claim = str(case["case_id"]), str(case["claim"])
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError(f"{case_id}: atoms must list two or more spans")
    spans: list[tuple[int, int]] = []
    for item in raw:
        start, end = item.get("start_offset"), item.get("end_offset")
        if not (isinstance(start, int) and isinstance(end, int)) or isinstance(start, bool):
            raise ValueError(f"{case_id}: atom offsets must be integers")
        if not 0 <= start < end <= len(claim):
            raise ValueError(f"{case_id}: atom span {start}-{end} outside the claim")
        if not claim[start:end].strip():
            raise ValueError(f"{case_id}: atom span {start}-{end} is blank")
        if "text" in item and item["text"] != claim[start:end]:
            raise ValueError(f"{case_id}: atom text does not match span {start}-{end}")
        spans.append((start, end))
    if spans != sorted(spans) or any(a[1] > b[0] for a, b in zip(spans, spans[1:], strict=False)):
        raise ValueError(f"{case_id}: atom spans must be sorted and non-overlapping")
    return spans


def case_rectified(case: Mapping[str, Any]) -> bool:
    """Return the ``rectified`` mark of a case (Protocol Amendment 4, DEC-011).

    Absent means ``False``. When present it must be a JSON boolean; any other
    value stops the run instead of being coerced.
    """
    value = case.get("rectified", False)
    if not isinstance(value, bool):
        raise ValueError(f"{case['case_id']}: rectified must be true or false")
    return value


def predict(
    claim_text: str,
    passages: Sequence[Passage],
    documents: Mapping[str, Document],
    *,
    atoms: Sequence[tuple[int, int]] | None = None,
    retrieval_succeeded: bool = True,
) -> dict[str, Any]:
    claim_id = "c1"
    spans = list(atoms) if atoms else [(0, len(claim_text))]
    evidence = []
    for index, passage in enumerate(passages, start=1):
        doc = documents[passage.document_id]
        evidence.append(
            Evidence(
                id=f"e{index}",
                claim_id=claim_id,
                source_id=doc.source_id,
                source_location=f"{doc.source_url}#offset={passage.start}-{passage.end}",
                retrieved_at=datetime.fromisoformat(doc.retrieved_at.replace("Z", "+00:00")),
                start_offset=passage.start,
                end_offset=passage.end,
                excerpt=_text(passage, documents),
                origin_id=doc.source_id,
                # canonical_url stays None: Judge 2.0 canonical hashing does not
                # serialize URL objects; the URL is kept in source_location.
            )
        )
    # Stance is detected per atom: each atom text is compared with every passage.
    detector = RuleStanceDetector()
    stances: list[dict[str, str]] = []
    for atom_index, (start, end) in enumerate(spans, start=1):
        extracted = ExtractedClaim(
            claim=Claim(id=claim_id, text=claim_text[start:end]),
            confidence=1.0,
            provenance=ComponentProvenance("rgc-eval", "rgc-eval", RUNNER_VERSION, "in", "out"),
        )
        edges = detector.detect([extracted], evidence).edges if evidence else ()
        stances.extend(
            {
                "id": f"s{len(stances) + offset}",
                "atom_id": f"a{atom_index}",
                "evidence_id": edge.edge.evidence_id,
                "stance": edge.edge.stance.value.upper(),
            }
            for offset, edge in enumerate(edges, start=1)
        )
    result = adjudication.adjudicate(
        {
            "protocol_version": "r2-a",
            "claim_id": claim_id,
            "claim_text": claim_text,
            "atoms": [
                {
                    "id": f"a{i}",
                    "text": claim_text[start:end],
                    "start_offset": start,
                    "end_offset": end,
                }
                for i, (start, end) in enumerate(spans, start=1)
            ],
            "evidence": evidence,
            "stances": stances,
            "source_texts": {p.document_id: documents[p.document_id].text for p in passages},
            "retrieval_succeeded": retrieval_succeeded,
        }
    ).to_dict()
    return {
        "decision_state": result["decision_state"],
        "reason_codes": result["reason_codes"],
        "judge_verdict": result["verdict"],
        "robustness": result["robustness"],
        "output_sha256": result["output_sha256"],
        "evidence": [
            {"document_id": p.document_id, "start_offset": p.start, "end_offset": p.end}
            for p in passages
        ],
        "atoms": [claim_text[start:end] for start, end in spans],
        "stances": [s["stance"] for s in stances],
    }


def to_label(prediction: Mapping[str, Any], vocabulary: str) -> str:
    """Map a Judge 2.0 result to the evaluated vocabulary.

    DECIDED -> its verdict (adr002: SUPPORTED with R3 -> VERIFIED, ADR-009 §11);
    ABSTAINED -> UNVERIFIED; anything else -> INVALID_PREDICTION (counted wrong).
    """
    state = prediction["decision_state"]
    if state == "ABSTAINED":
        return "UNVERIFIED"
    verdict = prediction["judge_verdict"]
    if state != "DECIDED" or verdict not in JUDGE2_LABELS:
        return INVALID
    if vocabulary == "adr002" and verdict == "SUPPORTED" and prediction["robustness"] == "R3":
        return "VERIFIED"
    return str(verdict)


# ------------------------------------------------------------------ metrics


def accuracy(gold: Sequence[str], pred: Sequence[str]) -> float:
    return sum(g == p for g, p in zip(gold, pred, strict=True)) / len(gold)


def balanced_accuracy(gold: Sequence[str], pred: Sequence[str]) -> float:
    recalls = []
    for label in sorted(set(gold)):
        idx = [i for i, g in enumerate(gold) if g == label]
        recalls.append(sum(pred[i] == label for i in idx) / len(idx))
    return sum(recalls) / len(recalls)


def macro_f1(gold: Sequence[str], pred: Sequence[str]) -> float:
    """Macro-F1 over the union of gold and predicted labels.

    INVALID_PREDICTION is kept in the union: it never appears in gold, so its
    F1 is 0 and it lowers the average (the conservative choice).
    """
    labels = sorted(set(gold) | set(pred))
    scores = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred, strict=True))
        fp = sum(g != label and p == label for g, p in zip(gold, pred, strict=True))
        fn = sum(g == label and p != label for g, p in zip(gold, pred, strict=True))
        scores.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(scores) / len(scores)


METRICS = {"accuracy": accuracy, "balanced_accuracy": balanced_accuracy, "macro_f1": macro_f1}


def bootstrap_ci(
    gold: Sequence[str], pred: Sequence[str], *, iterations: int = BOOTSTRAP_ITERATIONS
) -> dict[str, list[float]]:
    """Percentile 95% CI; one shared resample sequence for all metrics."""
    rng = Random(SEED)  # nosec B311 - deterministic statistical bootstrap
    n = len(gold)
    samples: dict[str, list[float]] = {name: [] for name in METRICS}
    for _ in range(iterations):
        idx = [rng.randrange(n) for _ in range(n)]
        g = [gold[i] for i in idx]
        p = [pred[i] for i in idx]
        for name, fn in METRICS.items():
            samples[name].append(fn(g, p))
    out = {}
    for name, values in samples.items():
        values.sort()
        out[name] = [
            values[int(0.025 * (iterations - 1))],
            values[int(0.975 * (iterations - 1))],
        ]
    return out


def majority_label(gold: Sequence[str], vocabulary: str) -> str:
    counts = Counter(gold)
    order = VOCABULARIES[vocabulary]
    return min(counts, key=lambda label: (-counts[label], order.index(label)))


def confusion(gold: Sequence[str], pred: Sequence[str], vocabulary: str) -> dict[str, Any]:
    columns = [*VOCABULARIES[vocabulary], INVALID]
    counts = Counter(zip(gold, pred, strict=True))
    return {g: {p: counts[(g, p)] for p in columns} for g in VOCABULARIES[vocabulary]}


def compute_metrics(
    gold: Sequence[str], pred: Sequence[str], vocabulary: str, *, iterations: int
) -> dict[str, Any]:
    baseline_label = majority_label(gold, vocabulary)
    baseline = [baseline_label] * len(gold)
    # Decisions use unrounded values; rounding is applied only to the report.
    system = {name: fn(gold, pred) for name, fn in METRICS.items()}
    base = {name: fn(gold, baseline) for name, fn in METRICS.items()}
    ci = bootstrap_ci(gold, pred, iterations=iterations)
    margin = system["accuracy"] - base["accuracy"]
    discordant_system = sum(p == g and b != g for g, p, b in zip(gold, pred, baseline, strict=True))
    discordant_base = sum(p != g and b == g for g, p, b in zip(gold, pred, baseline, strict=True))
    p_value = mcnemar_exact_pvalue(gold, pred, baseline)
    primary = {
        "accuracy_margin_pp": round(100 * margin, 4),
        # Tolerance only absorbs binary floating-point error (e.g. 0.7 - 0.6).
        "margin_at_least_10pp": margin >= 0.10 - 1e-12,
        "ci_lower_above_baseline": ci["accuracy"][0] > base["accuracy"],
        "mcnemar_p_below_0_05": p_value < 0.05,
    }
    primary["h1_supported"] = all(
        primary[k]
        for k in ("margin_at_least_10pp", "ci_lower_above_baseline", "mcnemar_p_below_0_05")
    )
    return {
        "n": len(gold),
        "gold_counts": {label: gold.count(label) for label in VOCABULARIES[vocabulary]},
        "absent_gold_states": [s for s in VOCABULARIES[vocabulary] if s not in gold],
        "invalid_predictions": pred.count(INVALID),
        "system": {name: round(value, 6) for name, value in system.items()},
        "system_ci95": {name: [round(v, 6) for v in pair] for name, pair in ci.items()},
        "baseline": {
            "label": baseline_label,
            **{name: round(value, 6) for name, value in base.items()},
        },
        "mcnemar": {
            "system_right_baseline_wrong": discordant_system,
            "system_wrong_baseline_right": discordant_base,
            "p_value_exact_two_sided": round(p_value, 8),
        },
        "primary_criterion": primary,
        "confusion": confusion(gold, pred, vocabulary),
    }


def stratum_metrics(
    gold: Sequence[str], pred: Sequence[str], vocabulary: str, *, iterations: int
) -> dict[str, Any]:
    """Descriptive metrics for a stratum; no H1 decision is taken on a stratum."""
    if not gold:
        return {"n": 0}
    ci = bootstrap_ci(gold, pred, iterations=iterations)
    return {
        "n": len(gold),
        "gold_counts": {label: list(gold).count(label) for label in VOCABULARIES[vocabulary]},
        "invalid_predictions": list(pred).count(INVALID),
        "system": {name: round(fn(gold, pred), 6) for name, fn in METRICS.items()},
        "system_ci95": {name: [round(v, 6) for v in pair] for name, pair in ci.items()},
        "confusion": confusion(gold, pred, vocabulary),
    }


# ---------------------------------------------------------------------- run


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def load_labels(path: Path, vocabulary: str) -> dict[str, str]:
    allowed = set(VOCABULARIES[vocabulary]) | EXCLUSION_LABELS
    labels: dict[str, str] = {}
    for row in _read_jsonl(path):
        case_id, verdict = str(row["case_id"]), str(row["verdict"])
        if verdict not in allowed:
            raise ValueError(f"{case_id}: label {verdict!r} not in vocabulary {vocabulary}")
        if case_id in labels:
            raise ValueError(f"{case_id}: duplicate label")
        labels[case_id] = verdict
    return labels


def evaluate(
    cases: Iterable[Mapping[str, Any]],
    labels: Mapping[str, str],
    documents: Mapping[str, Document],
    *,
    mode: str,
    vocabulary: str,
    top_k: int = DEFAULT_TOP_K,
    granularity: str = "dispositivo",
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> dict[str, Any]:
    index: BM25Index | None = None
    if mode == "retrieval":
        passages = [p for doc in documents.values() for p in segment(doc, granularity)]
        index = BM25Index(passages, documents)
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    unlabeled: list[str] = []
    seen: set[str] = set()
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in seen:
            raise ValueError(f"{case_id}: duplicate case")
        seen.add(case_id)
        gold = labels.get(case_id)
        if gold is None:
            unlabeled.append(case_id)
            continue
        if gold in EXCLUSION_LABELS:
            excluded.append({"case_id": case_id, "label": gold})
            continue
        atoms = case_atoms(case)
        rectified = case_rectified(case)
        if index is None:
            prediction = predict(
                case["claim"], oracle_passages(case, documents), documents, atoms=atoms
            )
        else:
            hits = index.search(case["claim"], top_k)
            prediction = predict(
                case["claim"],
                [p for p, _ in hits],
                documents,
                atoms=atoms,
                retrieval_succeeded=bool(hits),
            )
            prediction["retrieval_scores"] = [round(s, 6) for _, s in hits]
        label = to_label(prediction, vocabulary)
        rows.append(
            {
                "case_id": case_id,
                "gold": gold,
                "predicted": label,
                "rectified": rectified,
                **prediction,
            }
        )
    if unlabeled:
        raise ValueError(f"cases without a label (labels must be complete): {unlabeled}")
    extra = sorted(set(labels) - seen)
    if extra:
        raise ValueError(f"labels for unknown cases (files do not match): {extra}")
    if not rows:
        raise ValueError("no evaluable cases")
    gold_labels = [str(r["gold"]) for r in rows]
    predicted = [str(r["predicted"]) for r in rows]
    states = [str(r["decision_state"]) for r in rows]
    strata: dict[str, Any] = {}
    for name, flag in (("rectified", True), ("not_rectified", False)):
        chosen = [i for i, r in enumerate(rows) if r["rectified"] is flag]
        strata[name] = stratum_metrics(
            [gold_labels[i] for i in chosen],
            [predicted[i] for i in chosen],
            vocabulary,
            iterations=iterations,
        )
    return {
        "metrics": compute_metrics(gold_labels, predicted, vocabulary, iterations=iterations),
        # Amendment 4 (DEC-011, option A): rectified cases stay in the primary
        # metrics and are also reported as a separate, descriptive stratum.
        "strata": strata,
        # DEC-009: ABSTAINED is scored as UNVERIFIED; report how many predictions
        # came from each original Judge state so the mapping stays visible.
        "decision_states": {state: states.count(state) for state in sorted(set(states))},
        "excluded": excluded,
        "cases": rows,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("cases", type=Path)
    run.add_argument("--labels", type=Path, required=True)
    run.add_argument("--documents", type=Path, default=DOCUMENTS)
    run.add_argument("--mode", choices=("oracle", "retrieval"), required=True)
    run.add_argument("--vocabulary", choices=tuple(VOCABULARIES), default="judge2")
    run.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    run.add_argument("--granularity", choices=("dispositivo", "artigo"), default="dispositivo")
    run.add_argument("--out", type=Path, required=True)
    export = sub.add_parser("export-corpus")
    export.add_argument("--documents", type=Path, default=DOCUMENTS)
    export.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    documents = load_documents(args.documents)
    if args.command == "export-corpus":
        args.out.write_text(export_strict_corpus(documents), encoding="utf-8")
        print(f"wrote {len(documents)} documents to {args.out}")
        return 0

    result = evaluate(
        _read_jsonl(args.cases),
        load_labels(args.labels, args.vocabulary),
        documents,
        mode=args.mode,
        vocabulary=args.vocabulary,
        top_k=args.top_k,
        granularity=args.granularity,
    )
    report = {
        "runner_version": RUNNER_VERSION,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python": sys.version.split()[0],
        "inputs": {
            "cases": str(args.cases),
            "cases_sha256": _sha256(args.cases),
            "labels_sha256": _sha256(args.labels),
            "documents_sha256": _sha256(args.documents),
        },
        "config": {
            "mode": args.mode,
            "vocabulary": args.vocabulary,
            "top_k": args.top_k,
            "granularity": args.granularity,
            "bm25": {"k1": BM25_K1, "b": BM25_B},
            "stance_detector": f"{RuleStanceDetector.component}/{RuleStanceDetector.version}",
            "bootstrap": {"iterations": BOOTSTRAP_ITERATIONS, "seed": SEED},
        },
        **result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = result["metrics"]
    print(
        f"n={m['n']} accuracy={m['system']['accuracy']} "
        f"baseline={m['baseline']['accuracy']} h1={m['primary_criterion']['h1_supported']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
