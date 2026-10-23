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

The ``run`` subcommand requires complete human labels, a hash-bound protocol
freeze manifest, and a human annotation-approval manifest tied to a passing
independent agreement report. It refuses to execute while any approval is absent
or any bound artifact changes. There is no predictions-only mode.
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

RUNNER_VERSION = "rgc-eval/0.7.0"
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
    """Load source documents without coercing malformed provenance fields."""
    documents: dict[str, Document] = {}
    required = {"source_id", "source_url", "retrieved_at", "source_license", "text"}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise ValueError(
                f"{path}:{line_number}: expected an object containing "
                + ", ".join(sorted(required))
            )
        for field in required:
            value = raw[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"{path}:{line_number}: {field} must be a non-empty string"
                )
        source_id = raw["source_id"]
        text = raw["text"]
        declared = raw.get("text_sha256")
        if declared is not None:
            if not isinstance(declared, str) or re.fullmatch(r"[0-9a-f]{64}", declared) is None:
                raise ValueError(
                    f"{path}:{line_number}: "
                    "text_sha256 must be 64 lowercase hex characters"
                )
            if hashlib.sha256(text.encode()).hexdigest() != declared:
                raise ValueError(
                    f"{path}:{line_number}: text_sha256 mismatch for {source_id!r}"
                )
        if source_id in documents:
            raise ValueError(f"{path}:{line_number}: duplicate document {source_id!r}")
        documents[source_id] = Document(
            source_id=source_id,
            source_url=raw["source_url"],
            retrieved_at=raw["retrieved_at"],
            text=text,
            source_license=raw["source_license"],
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
    # B311 suppression: seeded bootstrap resampling is statistical, not security-sensitive.
    rng = Random(SEED)  # nosec B311
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


def bootstrap_ci_by_cluster(
    gold: Sequence[str],
    pred: Sequence[str],
    cluster_ids: Sequence[str],
    *,
    iterations: int = BOOTSTRAP_ITERATIONS,
) -> dict[str, list[float]]:
    """Percentile 95% CI by article cluster, retaining all cases in each draw."""
    if len(gold) != len(pred) or len(gold) != len(cluster_ids):
        raise ValueError("gold, predictions, and cluster IDs must have equal lengths")
    if not gold:
        raise ValueError("cluster bootstrap requires at least one case")
    if any(not isinstance(cluster, str) or not cluster.strip() for cluster in cluster_ids):
        raise ValueError("bootstrap_cluster_id must be a non-empty string")
    groups: dict[str, list[int]] = {}
    for index, cluster in enumerate(cluster_ids):
        groups.setdefault(cluster, []).append(index)
    keys = sorted(groups)
    # B311 suppression: seeded bootstrap resampling is statistical, not security-sensitive.
    rng = Random(SEED)  # nosec B311
    samples: dict[str, list[float]] = {name: [] for name in METRICS}
    for _ in range(iterations):
        selected = [keys[rng.randrange(len(keys))] for _ in keys]
        indices = [index for cluster in selected for index in groups[cluster]]
        sampled_gold = [gold[index] for index in indices]
        sampled_pred = [pred[index] for index in indices]
        for name, fn in METRICS.items():
            samples[name].append(fn(sampled_gold, sampled_pred))
    out: dict[str, list[float]] = {}
    for name, values in samples.items():
        values.sort()
        out[name] = [
            values[int(0.025 * (iterations - 1))],
            values[int(0.975 * (iterations - 1))],
        ]
    return out


def majority_label(gold: Sequence[str], vocabulary: str) -> str:
    if not gold:
        raise ValueError("cannot determine majority label from an empty partition")
    invalid = sorted(set(gold) - set(VOCABULARIES[vocabulary]))
    if invalid:
        raise ValueError(f"labels outside vocabulary {vocabulary}: {invalid}")
    counts = Counter(gold)
    order = VOCABULARIES[vocabulary]
    return min(counts, key=lambda label: (-counts[label], order.index(label)))


def development_baseline_label(labels: Mapping[str, str], vocabulary: str) -> str:
    """Derive primary baseline B only from public development reference labels."""
    if not labels:
        raise ValueError("development labels must not be empty")
    return majority_label(list(labels.values()), vocabulary)


def confusion(gold: Sequence[str], pred: Sequence[str], vocabulary: str) -> dict[str, Any]:
    columns = [*VOCABULARIES[vocabulary], INVALID]
    counts = Counter(zip(gold, pred, strict=True))
    return {g: {p: counts[(g, p)] for p in columns} for g in VOCABULARIES[vocabulary]}


def compute_metrics(
    gold: Sequence[str],
    pred: Sequence[str],
    vocabulary: str,
    *,
    baseline_label: str,
    iterations: int,
    cluster_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Score H1 against baseline B; report baseline A as descriptive only."""
    if baseline_label not in VOCABULARIES[vocabulary]:
        raise ValueError(f"baseline B label {baseline_label!r} is outside vocabulary {vocabulary}")

    # Baseline B is frozen from public development labels before evaluation.
    baseline_b = [baseline_label] * len(gold)
    # Baseline A is an oracle summary of evaluation-label prevalence, not an
    # operational classifier and never part of the H1 decision.
    baseline_a_label = majority_label(gold, vocabulary)
    baseline_a = [baseline_a_label] * len(gold)

    # Decisions use unrounded values; rounding is applied only to the report.
    system = {name: fn(gold, pred) for name, fn in METRICS.items()}
    base_b = {name: fn(gold, baseline_b) for name, fn in METRICS.items()}
    base_a = {name: fn(gold, baseline_a) for name, fn in METRICS.items()}
    ci_case = bootstrap_ci(gold, pred, iterations=iterations)
    ci = (
        bootstrap_ci_by_cluster(gold, pred, cluster_ids, iterations=iterations)
        if cluster_ids is not None
        else ci_case
    )
    margin = system["accuracy"] - base_b["accuracy"]
    discordant_system = sum(
        p == g and b != g for g, p, b in zip(gold, pred, baseline_b, strict=True)
    )
    discordant_base = sum(p != g and b == g for g, p, b in zip(gold, pred, baseline_b, strict=True))
    p_value = mcnemar_exact_pvalue(gold, pred, baseline_b)
    primary = {
        "baseline": "B",
        "ci_method": "article_cluster_bootstrap" if cluster_ids is not None else "case_bootstrap",
        "accuracy_margin_pp": round(100 * margin, 4),
        # Tolerance only absorbs binary floating-point error (e.g. 0.7 - 0.6).
        "margin_at_least_10pp": margin >= 0.10 - 1e-12,
        "ci_lower_above_baseline": ci["accuracy"][0] > base_b["accuracy"],
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
        **(
            {
                "system_ci95_case_bootstrap": {
                    name: [round(v, 6) for v in pair] for name, pair in ci_case.items()
                }
            }
            if cluster_ids is not None
            else {}
        ),
        "bootstrap_provenance": {
            "primary_unit": "article_cluster" if cluster_ids is not None else "case",
            "sensitivity_unit": "case" if cluster_ids is not None else None,
            "cluster_count": len(set(cluster_ids)) if cluster_ids is not None else None,
            "iterations": iterations,
            "seed": SEED,
        },
        "baseline_primary": {
            "name": "B",
            "label": baseline_label,
            **{name: round(value, 6) for name, value in base_b.items()},
        },
        "baseline_descriptive": {
            "name": "A",
            "label": baseline_a_label,
            **{name: round(value, 6) for name, value in base_a.items()},
        },
        "mcnemar": {
            "baseline": "B",
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


def validate_protocol_freeze(root: Path = ROOT) -> dict[str, str]:
    """Require an explicit freeze decision bound to the exact protocol documents."""
    protocol_path = root / "docs" / "eval" / "PROTOCOL-GOLDEN-V1.md"
    preregistration_path = root / "docs" / "eval" / "PREREGISTRATION-RGC-v1.md"
    runner_spec_path = root / "docs" / "eval" / "RUNNER-RGC-v1.md"
    runner_code_path = root / "evals" / "ptbr" / "rgc_eval.py"
    manifest_path = root / "docs" / "eval" / "PROTOCOL-FREEZE.json"

    try:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        preregistration_text = preregistration_path.read_text(encoding="utf-8")
        runner_spec_text = runner_spec_path.read_text(encoding="utf-8")
        runner_code_bytes = runner_code_path.read_bytes()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "RGC evaluation blocked: protocol freeze requires both documents and "
            "docs/eval/PROTOCOL-FREEZE.json"
        ) from exc

    protocol_status = next(
        (line for line in protocol_text.splitlines() if line.startswith("Status:")), ""
    )
    preregistration_status = next(
        (line for line in preregistration_text.splitlines() if line.startswith("**Estado:**")), ""
    )
    runner_spec_status = next(
        (line for line in runner_spec_text.splitlines() if line.startswith("**Estado:**")), ""
    )
    if not re.match(r"(?i)^Status:\s*\[?CONGELADO\]?(?:\s|—|$)", protocol_status):
        raise ValueError("RGC evaluation blocked: annotation protocol is not marked CONGELADO")
    if not re.match(r"(?i)^\*\*Estado:\*\*\s*\[CONGELADO\]", preregistration_status):
        raise ValueError("RGC evaluation blocked: preregistration is not marked [CONGELADO]")
    if not re.match(r"(?i)^\*\*Estado:\*\*\s*\[CONGELADO\]", runner_spec_status):
        raise ValueError("RGC evaluation blocked: runner specification is not marked [CONGELADO]")

    required = {
        "schema_version",
        "status",
        "approved_by",
        "approved_at",
        "protocol_sha256",
        "preregistration_sha256",
        "runner_spec_sha256",
        "runner_code_sha256",
        "runner_version",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("RGC evaluation blocked: freeze manifest has an invalid schema")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["status"] != "FROZEN"
    ):
        raise ValueError("RGC evaluation blocked: freeze manifest status must be FROZEN")
    if not isinstance(manifest["approved_by"], str) or not manifest["approved_by"].strip():
        raise ValueError("RGC evaluation blocked: freeze approver is missing")
    if not isinstance(manifest["approved_at"], str):
        raise ValueError("RGC evaluation blocked: freeze approval date is missing")
    try:
        datetime.fromisoformat(manifest["approved_at"])
    except ValueError as exc:
        raise ValueError("RGC evaluation blocked: approved_at must be ISO 8601") from exc

    protocol_sha256 = _sha256(protocol_path)
    preregistration_sha256 = _sha256(preregistration_path)
    runner_spec_sha256 = _sha256(runner_spec_path)
    runner_code_sha256 = hashlib.sha256(runner_code_bytes).hexdigest()
    expected_hashes = {
        "protocol_sha256": protocol_sha256,
        "preregistration_sha256": preregistration_sha256,
        "runner_spec_sha256": runner_spec_sha256,
        "runner_code_sha256": runner_code_sha256,
    }
    for field, actual_hash in expected_hashes.items():
        if manifest[field] != actual_hash:
            raise ValueError(f"RGC evaluation blocked: {field} differs from freeze manifest")
    if manifest["runner_version"] != RUNNER_VERSION:
        raise ValueError("RGC evaluation blocked: runner version differs from freeze manifest")

    return {
        "manifest_sha256": _sha256(manifest_path),
        **expected_hashes,
        "runner_version": RUNNER_VERSION,
        "approved_by": manifest["approved_by"],
        "approved_at": manifest["approved_at"],
    }


def validate_annotation_approval(
    cases_path: Path,
    labels_path: Path,
    development_cases_path: Path,
    development_labels_path: Path,
    annotation_a_path: Path,
    annotation_b_path: Path,
    agreement_report_path: Path,
    approval_manifest_path: Path,
    adjudication_record_path: Path,
) -> dict[str, Any]:
    """Require a passing human agreement report and approval bound to exact artifacts."""
    try:
        report = json.loads(agreement_report_path.read_text(encoding="utf-8"))
        manifest = json.loads(approval_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "RGC evaluation blocked: agreement report and annotation approval manifest are required"
        ) from exc

    required = {
        "schema_version",
        "status",
        "approved_by",
        "approved_at",
        "cases_sha256",
        "labels_sha256",
        "development_cases_sha256",
        "development_labels_sha256",
        "agreement_report_sha256",
        "adjudication_record_sha256",
        "annotation_a_sha256",
        "annotation_b_sha256",
        "cohen_kappa",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError(
            "RGC evaluation blocked: annotation approval manifest has an invalid schema"
        )
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != 1
        or manifest["status"] != "APPROVED"
    ):
        raise ValueError("RGC evaluation blocked: annotation approval status must be APPROVED")
    if not isinstance(manifest["approved_by"], str) or not manifest["approved_by"].strip():
        raise ValueError("RGC evaluation blocked: annotation approval author is missing")
    if not isinstance(manifest["approved_at"], str):
        raise ValueError("RGC evaluation blocked: annotation approval date is missing")
    try:
        datetime.fromisoformat(manifest["approved_at"])
    except ValueError as exc:
        raise ValueError("RGC evaluation blocked: annotation approved_at must be ISO 8601") from exc

    if not isinstance(report, dict) or report.get("method") != "cohen_kappa_unweighted":
        raise ValueError("RGC evaluation blocked: unsupported annotator agreement report")
    kappa = report.get("cohen_kappa")
    if (
        report.get("gate_passed") is not True
        or not isinstance(kappa, (int, float))
        or isinstance(kappa, bool)
        or kappa < 0.6
    ):
        raise ValueError("RGC evaluation blocked: human annotator agreement gate did not pass")
    inputs = report.get("inputs")
    if not isinstance(inputs, dict):
        raise ValueError("RGC evaluation blocked: agreement report lacks annotation input hashes")
    for field in ("annotation_a_sha256", "annotation_b_sha256"):
        value = inputs.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"RGC evaluation blocked: agreement report has invalid {field}")
        if manifest[field] != value:
            raise ValueError(f"RGC evaluation blocked: {field} differs from agreement report")
    if manifest["cohen_kappa"] != kappa:
        raise ValueError("RGC evaluation blocked: approved kappa differs from agreement report")

    try:
        expected_hashes = {
            "cases_sha256": _sha256(cases_path),
            "labels_sha256": _sha256(labels_path),
            "development_cases_sha256": _sha256(development_cases_path),
            "development_labels_sha256": _sha256(development_labels_path),
            "annotation_a_sha256": _sha256(annotation_a_path),
            "annotation_b_sha256": _sha256(annotation_b_path),
            "agreement_report_sha256": _sha256(agreement_report_path),
            "adjudication_record_sha256": _sha256(adjudication_record_path),
        }
    except OSError as exc:
        raise ValueError(
            "RGC evaluation blocked: an approved annotation artifact is missing"
        ) from exc
    for field, actual_hash in expected_hashes.items():
        if manifest[field] != actual_hash:
            raise ValueError(f"RGC evaluation blocked: {field} differs from approval manifest")

    return {
        "manifest_sha256": _sha256(approval_manifest_path),
        **expected_hashes,
        "annotation_a_sha256": manifest["annotation_a_sha256"],
        "annotation_b_sha256": manifest["annotation_b_sha256"],
        "cohen_kappa": kappa,
        "approved_by": manifest["approved_by"],
        "approved_at": manifest["approved_at"],
    }


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def load_labels(path: Path, vocabulary: str) -> dict[str, str]:
    """Load strict JSONL gold labels without coercing malformed input."""
    allowed = set(VOCABULARIES[vocabulary]) | EXCLUSION_LABELS
    labels: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict) or set(row) != {"case_id", "verdict"}:
            raise ValueError(f"{path}:{line_number}: expected exactly case_id and verdict")
        case_id, verdict = row["case_id"], row["verdict"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{path}:{line_number}: case_id must be a non-empty string")
        if not isinstance(verdict, str) or verdict not in allowed:
            raise ValueError(
                f"{path}:{line_number}: label {verdict!r} not in vocabulary {vocabulary}"
            )
        if case_id in labels:
            raise ValueError(f"{path}:{line_number}: duplicate label for {case_id!r}")
        labels[case_id] = verdict
    return labels


def evaluate(
    cases: Iterable[Mapping[str, Any]],
    labels: Mapping[str, str],
    documents: Mapping[str, Document],
    *,
    development_cases: Iterable[Mapping[str, Any]],
    development_labels: Mapping[str, str],
    mode: str,
    vocabulary: str,
    top_k: int = DEFAULT_TOP_K,
    granularity: str = "dispositivo",
    iterations: int = BOOTSTRAP_ITERATIONS,
    partition: str = "development",
) -> dict[str, Any]:
    if partition not in {"hidden", "development"}:
        raise ValueError("partition must be hidden or development")
    cases = list(cases)
    development_cases = list(development_cases)
    development_case_ids = [str(case["case_id"]) for case in development_cases]
    if len(set(development_case_ids)) != len(development_case_ids):
        raise ValueError("duplicate case in development partition")
    development_ids = set(development_case_ids)
    missing_development_labels = sorted(development_ids - set(development_labels))
    unknown_development_labels = sorted(set(development_labels) - development_ids)
    if missing_development_labels or unknown_development_labels:
        raise ValueError(
            "development cases/labels mismatch: "
            f"missing labels={missing_development_labels}, "
            f"unknown labels={unknown_development_labels}"
        )
    baseline_label = development_baseline_label(development_labels, vocabulary)
    evaluation_case_ids = [str(case["case_id"]) for case in cases]
    overlap = sorted(set(evaluation_case_ids) & development_ids)
    if overlap:
        raise ValueError(f"development/evaluation partition overlap: {overlap}")

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
        # Validate schema-level metadata even for excluded or unlabeled cases;
        # malformed annotations must never be silently skipped.
        rectified = case_rectified(case)
        gold = labels.get(case_id)
        if gold is None:
            unlabeled.append(case_id)
            continue
        if gold in EXCLUSION_LABELS:
            excluded.append({"case_id": case_id, "label": gold})
            continue
        cluster_id = case.get("bootstrap_cluster_id")
        if partition == "hidden" and (not isinstance(cluster_id, str) or not cluster_id.strip()):
            raise ValueError(
                f"{case_id}: missing or invalid bootstrap_cluster_id for hidden partition"
            )
        if (
            partition == "hidden"
            and isinstance(cluster_id, str)
            and cluster_id.startswith("bundle:")
        ):
            members = cluster_id.removeprefix("bundle:").split("+")
            if (
                len(members) < 2
                or any(not member for member in members)
                or members != sorted(set(members))
            ):
                raise ValueError(
                    f"{case_id}: bundle bootstrap_cluster_id must contain at least two "
                    "unique, sorted IDs"
                )
        atoms = case_atoms(case)
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
                "bootstrap_cluster_id": cluster_id,
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
    cluster_ids = (
        [str(row["bootstrap_cluster_id"]) for row in rows] if partition == "hidden" else None
    )
    metrics = compute_metrics(
        gold_labels,
        predicted,
        vocabulary,
        baseline_label=baseline_label,
        iterations=iterations,
        cluster_ids=cluster_ids,
    )
    if partition == "development":
        metrics["primary_criterion"] = {
            "h1_supported": None,
            "not_tested": True,
            "reason": "development partition is descriptive; H1 is confirmatory only on hidden",
        }
    return {
        "evaluation_partition": partition,
        "metrics": metrics,
        "baseline_provenance": {
            "primary": "B",
            "development_case_count": len(development_cases),
            "development_label_count": len(development_labels),
            "development_labels_complete": True,
            "development_majority_label": baseline_label,
            "evaluation_development_id_overlap": False,
        },
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
    run.add_argument("--annotation-a", type=Path, required=True)
    run.add_argument("--annotation-b", type=Path, required=True)
    run.add_argument("--agreement-report", type=Path, required=True)
    run.add_argument("--annotation-approval", type=Path, required=True)
    run.add_argument("--adjudication-record", type=Path, required=True)
    run.add_argument(
        "--development-cases",
        type=Path,
        required=True,
        help="public 70% development partition cases",
    )
    run.add_argument(
        "--development-labels",
        type=Path,
        required=True,
        help="complete human labels for the public 70% development partition",
    )
    run.add_argument("--documents", type=Path, default=DOCUMENTS)
    run.add_argument("--mode", choices=("oracle", "retrieval"), required=True)
    run.add_argument("--vocabulary", choices=tuple(VOCABULARIES), default="judge2")
    run.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    run.add_argument(
        "--partition",
        choices=("hidden", "development"),
        required=True,
        help="hidden is confirmatory for H1; development is descriptive only",
    )
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

    try:
        protocol_freeze = validate_protocol_freeze()
        annotation_approval = validate_annotation_approval(
            args.cases,
            args.labels,
            args.development_cases,
            args.development_labels,
            args.annotation_a,
            args.annotation_b,
            args.agreement_report,
            args.annotation_approval,
            args.adjudication_record,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    development_cases = _read_jsonl(args.development_cases)
    development_labels = load_labels(args.development_labels, args.vocabulary)
    result = evaluate(
        _read_jsonl(args.cases),
        load_labels(args.labels, args.vocabulary),
        documents,
        development_cases=development_cases,
        development_labels=development_labels,
        mode=args.mode,
        vocabulary=args.vocabulary,
        top_k=args.top_k,
        granularity=args.granularity,
        partition=args.partition,
    )
    report = {
        "runner_version": RUNNER_VERSION,
        "protocol_freeze": protocol_freeze,
        "annotation_approval": annotation_approval,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python": sys.version.split()[0],
        "inputs": {
            "cases": str(args.cases),
            "cases_sha256": _sha256(args.cases),
            "labels_sha256": _sha256(args.labels),
            "development_cases_sha256": _sha256(args.development_cases),
            "development_labels_sha256": _sha256(args.development_labels),
            "documents_sha256": _sha256(args.documents),
        },
        "config": {
            "partition": args.partition,
            "mode": args.mode,
            "vocabulary": args.vocabulary,
            "top_k": args.top_k,
            "granularity": args.granularity,
            "bm25": {"k1": BM25_K1, "b": BM25_B},
            "stance_detector": f"{RuleStanceDetector.component}/{RuleStanceDetector.version}",
            "bootstrap": {
                "iterations": BOOTSTRAP_ITERATIONS,
                "seed": SEED,
                "primary_unit": "article_cluster" if args.partition == "hidden" else "case",
                "sensitivity_unit": "case" if args.partition == "hidden" else None,
            },
            "baseline_primary": {
                "name": "B",
                "development_label_count": len(development_labels),
                "label": development_baseline_label(development_labels, args.vocabulary),
            },
            "baseline_descriptive": {
                "name": "A",
                "source": "evaluation gold labels; descriptive only",
            },
        },
        **result,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m = result["metrics"]
    print(
        f"n={m['n']} accuracy={m['system']['accuracy']} "
        f"baseline_B={m['baseline_primary']['accuracy']} "
        f"baseline_A_descriptive={m['baseline_descriptive']['accuracy']} "
        f"h1={m['primary_criterion']['h1_supported']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
