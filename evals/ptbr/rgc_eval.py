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
import os
import platform
import re
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

import ayorai_attractor.verification.judge2 as judge2_module
from ayorai_attractor.evaluation.stats import mcnemar_exact_pvalue
from ayorai_attractor.verification.extraction import ComponentProvenance, ExtractedClaim
from ayorai_attractor.verification.judge2 import adjudication
from ayorai_attractor.verification.models import Claim, Evidence
from ayorai_attractor.verification.stance import RuleStanceDetector

if __package__ in (None, ""):  # run as a script: make the repository importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evals.ptbr import rgc_agreement  # noqa: E402
from evals.ptbr.rgc_components import (  # noqa: E402
    bootstrap_metrics_by_component,
    build_article_components,
    component_differences,
    obuchowski_clustered_test,
    sign_flip_by_component,
)
from evals.ptbr.rgc_ids import cluster_members, require_article_id  # noqa: E402
from evals.ptbr.rgc_random import (  # noqa: E402
    LABEL_CASE_ACCURACY,
    LABEL_CLUSTER_ACCURACY,
    RGC_SEED,
    RgcPrng,
    percentile_ci95,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = ROOT / "evals" / "ptbr" / "sources" / "DOCUMENTS.jsonl"

RUNNER_VERSION = "rgc-eval/0.12.0"
FREEZE_SCHEMA_VERSION = 2
RUN_MANIFEST_SCHEMA = "rgc-run-manifest/1"
# Direct and transitive deterministic runtime dependencies loaded by the RGC runner,
# including Judge 2.0 code/rules and the project dependency specification. The freeze
# binds the full execution closure, not only the statistical helper modules.
RUNNER_DEPENDENCIES = (
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
)
SEED = RGC_SEED
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


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


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
            raw = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(raw, dict) or not required.issubset(raw):
            raise ValueError(
                f"{path}:{line_number}: expected an object containing "
                + ", ".join(sorted(required))
            )
        for field in required:
            value = raw[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{path}:{line_number}: {field} must be a non-empty string")
        source_id = raw["source_id"]
        text = raw["text"]
        declared = raw.get("text_sha256")
        if "text_sha256" in raw:
            if not isinstance(declared, str) or re.fullmatch(r"[0-9a-f]{64}", declared) is None:
                message = f"{path}:{line_number}: text_sha256 must be 64 lowercase hex characters"
                raise ValueError(message)
            if hashlib.sha256(text.encode()).hexdigest() != declared:
                raise ValueError(f"{path}:{line_number}: text_sha256 mismatch for {source_id!r}")
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
    """Validate oracle evidence strictly; do not coerce offsets or malformed fields."""
    case_id = str(case["case_id"])
    raw_evidence = case.get("evidence")
    if not isinstance(raw_evidence, list) or not raw_evidence:
        raise ValueError(f"{case_id}: evidence must be a non-empty list")
    passages = []
    for item in raw_evidence:
        if not isinstance(item, Mapping):
            raise ValueError(f"{case_id}: each evidence item must be an object")
        document_id = item.get("document_id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError(f"{case_id}: evidence document_id must be a non-empty string")
        if document_id not in documents:
            raise ValueError(f"{case_id}: unknown evidence document_id {document_id!r}")
        start, end = item.get("start_offset"), item.get("end_offset")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
            raise ValueError(f"{case_id}: evidence offsets must be integers")
        doc = documents[document_id]
        if not 0 <= start < end <= len(doc.text):
            raise ValueError(f"{case_id}: evidence offsets {start}-{end} outside document")
        excerpt = item.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip():
            raise ValueError(f"{case_id}: evidence excerpt must be a non-empty string")
        if doc.text[start:end] != excerpt:
            raise ValueError(f"{case_id}: excerpt does not match document offsets")
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
        if not isinstance(item, Mapping):
            raise ValueError(f"{case_id}: each atom must be an object")
        start, end = item.get("start_offset"), item.get("end_offset")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
        ):
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


def validate_cluster_citations(
    case: Mapping[str, Any],
    cluster_id: object,
    case_id: str,
    *,
    require_citations: bool = True,
    require_cluster: bool = True,
) -> None:
    """Validate every supplied canonical article ID and cluster/citation consistency.

    Hidden evaluation requires both fields. Development evaluation may omit either,
    but any supplied field is still checked against DEC-027, D1. A bundle is the
    subset jointly necessary when no single principal article exists; it must be
    contained in, not equal to, the complete citation list. This check cannot
    determine legal relevance or whether a principal article was selected correctly.
    """
    cited_ids: set[str] | None = None
    if "cited_article_ids" not in case:
        if require_citations:
            raise ValueError(f"{case_id}: cited_article_ids is required for hidden partition cases")
    else:
        cited = case["cited_article_ids"]
        if (
            not isinstance(cited, list)
            or not cited
            or any(not isinstance(article_id, str) or not article_id for article_id in cited)
            or len(cited) != len(set(cited))
        ):
            raise ValueError(
                f"{case_id}: cited_article_ids must be a non-empty list of unique, "
                "canonical, non-empty strings"
            )
        for article_id in cited:  # DEC-027, D1: one grammar for every article ID
            require_article_id(article_id, f"{case_id}: cited_article_ids")
        cited_ids = set(cited)

    members = (
        cluster_members(cluster_id, f"{case_id}: bootstrap_cluster_id") if require_cluster else None
    )
    if members is not None and cited_ids is not None:
        missing = sorted(set(members) - cited_ids)
        if missing:
            if isinstance(cluster_id, str) and cluster_id.startswith("bundle:"):
                raise ValueError(
                    f"{case_id}: bundle bootstrap_cluster_id contains IDs absent "
                    f"from cited_article_ids: {missing}"
                )
            raise ValueError(
                f"{case_id}: bootstrap_cluster_id must be present in cited_article_ids"
            )


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


def _ci95(samples: Mapping[str, list[float]]) -> dict[str, list[float]]:
    """Type-7 percentile interval of each metric (DEC-027, D2)."""
    out: dict[str, list[float]] = {}
    for name, values in samples.items():
        interval = percentile_ci95(values)
        if interval is None:
            raise ValueError("bootstrap produced no replicates")
        out[name] = interval
    return out


def bootstrap_ci(
    gold: Sequence[str], pred: Sequence[str], *, iterations: int = BOOTSTRAP_ITERATIONS
) -> dict[str, list[float]]:
    """Percentile 95% CI by case; one shared RGC-PRNG-1 stream for all metrics."""
    if len(gold) != len(pred):
        raise ValueError("gold and predictions must have equal lengths")
    if not gold:
        raise ValueError("case bootstrap requires at least one case")
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be positive")
    rng = RgcPrng(SEED, LABEL_CASE_ACCURACY)
    n = len(gold)
    samples: dict[str, list[float]] = {name: [] for name in METRICS}
    for _ in range(iterations):
        idx = [rng.below(n) for _ in range(n)]
        g = [gold[i] for i in idx]
        p = [pred[i] for i in idx]
        for name, fn in METRICS.items():
            samples[name].append(fn(g, p))
    return _ci95(samples)


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
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be positive")
    if any(not isinstance(cluster, str) or not cluster.strip() for cluster in cluster_ids):
        raise ValueError("bootstrap_cluster_id must be a non-empty string")
    groups: dict[str, list[int]] = {}
    for index, cluster in enumerate(cluster_ids):
        groups.setdefault(cluster, []).append(index)
    keys = sorted(groups)  # lexical order of the cluster IDs (DEC-027, D3)
    rng = RgcPrng(SEED, LABEL_CLUSTER_ACCURACY)
    samples: dict[str, list[float]] = {name: [] for name in METRICS}
    for _ in range(iterations):
        selected = [keys[rng.below(len(keys))] for _ in keys]
        indices = [index for cluster in selected for index in groups[cluster]]
        sampled_gold = [gold[index] for index in indices]
        sampled_pred = [pred[index] for index in indices]
        for name, fn in METRICS.items():
            samples[name].append(fn(sampled_gold, sampled_pred))
    return _ci95(samples)


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
    component_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Score H1 against baseline B; report baseline A as descriptive only.

    Hidden partition (DEC-027 D4-D5; Emenda 11): the primary interval resamples DEC-023
    connected components and the primary test is the DEC-021 sign-flip by component.
    The DEC-019 cluster interval, the case interval, exact McNemar and Obuchowski's
    clustered test are sensitivity analyses only and never decide H1.
    """
    if (cluster_ids is None) != (component_ids is None):
        raise ValueError("cluster and component IDs are required together")
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
    ci_cluster: dict[str, list[float]] | None = None
    ci = ci_case
    if cluster_ids is not None and component_ids is not None:
        ci_cluster = bootstrap_ci_by_cluster(gold, pred, cluster_ids, iterations=iterations)
        keys = [f"{index:06d}" for index in range(len(gold))]
        component_ci = bootstrap_metrics_by_component(
            dict(zip(keys, gold, strict=True)),
            dict(zip(keys, pred, strict=True)),
            dict(zip(keys, component_ids, strict=True)),
            METRICS,
            iterations=iterations,
        )
        ci = {name: list(pair) for name, pair in component_ci.ci95.items()}
    margin = system["accuracy"] - base_b["accuracy"]
    discordant_system = sum(
        p == g and b != g for g, p, b in zip(gold, pred, baseline_b, strict=True)
    )
    discordant_base = sum(p != g and b == g for g, p, b in zip(gold, pred, baseline_b, strict=True))
    p_value = mcnemar_exact_pvalue(gold, pred, baseline_b)
    sign_flip = (
        sign_flip_by_component(component_differences(gold, pred, baseline_b, component_ids))
        if component_ids is not None
        else None
    )
    obuchowski = (
        obuchowski_clustered_test(gold, pred, baseline_b, component_ids)
        if component_ids is not None
        else None
    )
    primary: dict[str, Any] = {
        "baseline": "B",
        "ci_method": "component_bootstrap" if component_ids is not None else "case_bootstrap",
        "test": "sign_flip_by_component" if sign_flip is not None else "mcnemar_exact",
        "accuracy_margin_pp": round(100 * margin, 4),
        # Tolerance only absorbs binary floating-point error (e.g. 0.7 - 0.6).
        "margin_at_least_10pp": margin >= 0.10 - 1e-12,
        "ci_lower_above_baseline": ci["accuracy"][0] > base_b["accuracy"],
    }
    if sign_flip is not None:
        primary["sign_flip_p_below_0_05"] = sign_flip.p_value_two_sided < 0.05
        primary["significance_below_005_possible"] = sign_flip.significance_below_005_possible
        test_key = "sign_flip_p_below_0_05"
    else:
        primary["mcnemar_p_below_0_05"] = p_value < 0.05
        test_key = "mcnemar_p_below_0_05"
    primary["h1_supported"] = all(
        primary[k] for k in ("margin_at_least_10pp", "ci_lower_above_baseline", test_key)
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
                "system_ci95_article_cluster": {
                    name: [round(v, 6) for v in pair] for name, pair in ci_cluster.items()
                },
                "system_ci95_case_bootstrap": {
                    name: [round(v, 6) for v in pair] for name, pair in ci_case.items()
                },
            }
            if ci_cluster is not None
            else {}
        ),
        "bootstrap_provenance": {
            "primary_unit": "component" if component_ids is not None else "case",
            "sensitivity_units": ["article_cluster", "case"] if component_ids is not None else [],
            "cluster_count": len(set(cluster_ids)) if cluster_ids is not None else None,
            "component_count": len(set(component_ids)) if component_ids is not None else None,
            "iterations": iterations,
            "seed": SEED,
            "generator": "RGC-PRNG-1",
            "percentile": "hyndman-fan-type-7",
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
        **(
            {
                "sign_flip": {
                    "baseline": "B",
                    "statistic_observed": sign_flip.statistic_observed,
                    "p_value_two_sided": round(sign_flip.p_value_two_sided, 8),
                    "method": sign_flip.method,
                    "component_count": sign_flip.component_count,
                    "informative_component_count": sign_flip.informative_component_count,
                    "minimum_attainable_p": sign_flip.minimum_attainable_p,
                    "extreme_permutations": sign_flip.extreme_permutations,
                    "permutations_considered": sign_flip.permutations_considered,
                    "theoretical_exact_resolution": sign_flip.theoretical_exact_resolution,
                    "monte_carlo_minimum_p": sign_flip.monte_carlo_minimum_p,
                    "significance_below_005_possible": sign_flip.significance_below_005_possible,
                    "seed": sign_flip.seed,
                    "generator": sign_flip.generator,
                },
                "obuchowski_sensitivity": obuchowski._asdict() if obuchowski else None,
            }
            if sign_flip is not None
            else {}
        ),
        "mcnemar": {
            "role": "sensitivity" if sign_flip is not None else "primary",
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
    """Read case JSONL strictly; malformed or blank records must not disappear."""
    records: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            record = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: expected an object")
        case_id = record.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{path}:{line_number}: case_id must be a non-empty string")
        if case_id in seen_case_ids:
            raise ValueError(f"{path}:{line_number}: duplicate case_id {case_id!r}")
        seen_case_ids.add(case_id)
        records.append(record)
    return records


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_protocol_freeze(root: Path = ROOT) -> dict[str, Any]:
    """Require an explicit freeze decision bound to the exact protocol documents."""
    protocol_path = root / "docs" / "eval" / "PROTOCOL-GOLDEN-V1.md"
    preregistration_path = root / "docs" / "eval" / "PREREGISTRATION-RGC-v1.md"
    runner_spec_path = root / "docs" / "eval" / "RUNNER-RGC-v1.md"
    runner_code_path = root / "evals" / "ptbr" / "rgc_eval.py"
    manifest_path = root / "docs" / "eval" / "PROTOCOL-FREEZE.json"
    if not manifest_path.is_file():
        raise ValueError(
            "RGC evaluation blocked: protocol freeze requires both documents and "
            "docs/eval/PROTOCOL-FREEZE.json"
        )

    try:
        protocol_text = protocol_path.read_text(encoding="utf-8")
        preregistration_text = preregistration_path.read_text(encoding="utf-8")
        runner_spec_text = runner_spec_path.read_text(encoding="utf-8")
        runner_code_bytes = runner_code_path.read_bytes()
        manifest = _load_strict_json(manifest_path, "protocol freeze manifest")
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
        "runner_dependencies_sha256",
        "runner_version",
    }
    if not isinstance(manifest, dict) or set(manifest) != required:
        raise ValueError("RGC evaluation blocked: freeze manifest has an invalid schema")
    if (
        type(manifest["schema_version"]) is not int
        or manifest["schema_version"] != FREEZE_SCHEMA_VERSION
        or manifest["status"] != "FROZEN"
    ):
        raise ValueError(
            f"RGC evaluation blocked: freeze manifest must be schema_version "
            f"{FREEZE_SCHEMA_VERSION} with status FROZEN"
        )
    for field in (
        "protocol_sha256",
        "preregistration_sha256",
        "runner_spec_sha256",
        "runner_code_sha256",
    ):
        if (
            not isinstance(manifest[field], str)
            or re.fullmatch(r"[0-9a-f]{64}", manifest[field]) is None
        ):
            raise ValueError(f"RGC evaluation blocked: {field} must be a lowercase SHA-256 digest")
    dependencies = manifest["runner_dependencies_sha256"]
    if not isinstance(dependencies, dict) or set(dependencies) != set(RUNNER_DEPENDENCIES):
        raise ValueError(
            "RGC evaluation blocked: runner_dependencies_sha256 must list exactly "
            f"{list(RUNNER_DEPENDENCIES)}"
        )
    if not isinstance(manifest["approved_by"], str) or not manifest["approved_by"].strip():
        raise ValueError("RGC evaluation blocked: freeze approver is missing")
    if not isinstance(manifest["runner_version"], str) or not manifest["runner_version"]:
        raise ValueError("RGC evaluation blocked: freeze runner version is missing")
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
    dependency_hashes: dict[str, str] = {}
    for relative in RUNNER_DEPENDENCIES:
        try:
            dependency_hashes[relative] = _sha256(root / relative)
        except OSError as exc:
            raise ValueError(f"RGC evaluation blocked: {relative} is missing") from exc
        if dependencies[relative] != dependency_hashes[relative]:
            raise ValueError(f"RGC evaluation blocked: {relative} differs from freeze manifest")
    if manifest["runner_version"] != RUNNER_VERSION:
        raise ValueError("RGC evaluation blocked: runner version differs from freeze manifest")

    return {
        "manifest_sha256": _sha256(manifest_path),
        **expected_hashes,
        "runner_dependencies_sha256": dependency_hashes,
        "runner_version": RUNNER_VERSION,
        "approved_by": manifest["approved_by"],
        "approved_at": manifest["approved_at"],
    }


def _strict_jsonl_case_ids(path: Path, *, annotation: bool = False) -> set[str]:
    """Read unique case IDs from cases or human annotations without skipping malformed lines."""
    ids: set[str] = set()
    allowed_annotation_labels = set(VOCABULARIES["judge2"]) | EXCLUSION_LABELS
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        expected_keys = {"case_id", "label"} if annotation else None
        if annotation and set(row) != expected_keys:
            raise ValueError(f"{path}:{line_number}: expected exactly case_id and label")
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError(f"{path}:{line_number}: case_id must be a non-empty string")
        if case_id in ids:
            raise ValueError(f"{path}:{line_number}: duplicate case_id {case_id!r}")
        if annotation:
            label = row.get("label")
            if not isinstance(label, str) or label not in allowed_annotation_labels:
                raise ValueError(f"{path}:{line_number}: invalid annotation label {label!r}")
        ids.add(case_id)
    if not ids:
        raise ValueError(f"{path}: file is empty")
    return ids


def _validate_annotation_case_ids(
    cases_path: Path, annotation_a_path: Path, annotation_b_path: Path
) -> None:
    """Require both independent annotation files to cover exactly the approved cases."""
    approved_case_ids = _strict_jsonl_case_ids(cases_path)
    annotation_a_ids = _strict_jsonl_case_ids(annotation_a_path, annotation=True)
    annotation_b_ids = _strict_jsonl_case_ids(annotation_b_path, annotation=True)
    cases_minus_a = sorted(approved_case_ids - annotation_a_ids)
    cases_minus_b = sorted(approved_case_ids - annotation_b_ids)
    a_minus_cases = sorted(annotation_a_ids - approved_case_ids)
    b_minus_cases = sorted(annotation_b_ids - approved_case_ids)
    if cases_minus_a or cases_minus_b or a_minus_cases or b_minus_cases:
        raise ValueError(
            "RGC evaluation blocked: annotation case IDs must exactly match approved cases "
            f"(cases-A={cases_minus_a}, cases-B={cases_minus_b}, "
            f"A-cases={a_minus_cases}, B-cases={b_minus_cases})"
        )


def _validate_rule_gap_policy(label: str, *, pilot_mode: bool, partition: str) -> None:
    """Allow RULE_GAP only in an explicitly selected, non-hidden pilot run."""
    if label in EXCLUSION_LABELS and (not pilot_mode or partition != "development"):
        raise ValueError(
            "RULE_GAP is prohibited in every definitive partition; "
            "it is accepted only in explicit pilot mode"
        )


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
        report = _load_strict_json(agreement_report_path, "agreement report")
        manifest = _load_strict_json(approval_manifest_path, "annotation approval manifest")
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

    try:
        _validate_annotation_case_ids(cases_path, annotation_a_path, annotation_b_path)
    except OSError as exc:
        raise ValueError(
            "RGC evaluation blocked: an approved annotation artifact is missing"
        ) from exc

    if set(inputs) != {"annotation_a_sha256", "annotation_b_sha256"}:
        raise ValueError("RGC evaluation blocked: agreement report input schema is invalid")
    try:
        canonical_agreement = rgc_agreement.compute_agreement(
            rgc_agreement.load_annotations(annotation_a_path),
            rgc_agreement.load_annotations(annotation_b_path),
            iterations=rgc_agreement.DEFAULT_ITERATIONS,
            seed=rgc_agreement.DEFAULT_SEED,
        )
    except (OSError, ValueError) as exc:
        raise ValueError(
            "RGC evaluation blocked: canonical annotator agreement could not be recomputed"
        ) from exc
    report_without_inputs = {key: value for key, value in report.items() if key != "inputs"}
    if report_without_inputs != canonical_agreement:
        raise ValueError(
            "RGC evaluation blocked: agreement report differs from canonical recomputation"
        )

    return {
        "manifest_sha256": _sha256(approval_manifest_path),
        **expected_hashes,
        "annotation_a_sha256": manifest["annotation_a_sha256"],
        "annotation_b_sha256": manifest["annotation_b_sha256"],
        "cohen_kappa": kappa,
        "approved_by": manifest["approved_by"],
        "approved_at": manifest["approved_at"],
    }


def _snapshot_files(
    sources: Mapping[str, Path], destination: Path
) -> tuple[dict[str, Path], dict[str, str]]:
    """Capture each source path once and return private, read-only snapshot paths and hashes.

    All later validation, parsing, evaluation and manifest verification must use these
    snapshots, never reopen the caller-controlled source paths. Repeated source paths
    share one captured byte sequence.
    """
    snapshots: dict[str, Path] = {}
    digests: dict[str, str] = {}
    captured: dict[Path, tuple[Path, str]] = {}
    for name, source in sources.items():
        try:
            source_key = source.absolute()
            existing = captured.get(source_key)
            if existing is None:
                descriptor = os.open(
                    source_key,
                    os.O_RDONLY | getattr(os, "O_NONBLOCK", 0),
                )
                with os.fdopen(descriptor, "rb") as source_handle:
                    before = os.fstat(source_handle.fileno())
                    if not stat.S_ISREG(before.st_mode):
                        raise ValueError(f"RGC evaluation blocked: {name} is not a regular file")
                    payload = source_handle.read()
                    after = os.fstat(source_handle.fileno())
                stable_before = (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                )
                stable_after = (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                )
                if stable_before != stable_after or len(payload) != before.st_size:
                    raise ValueError(
                        f"RGC evaluation blocked: {name} changed while being snapshotted"
                    )
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(payload)
                target.chmod(0o400)
                digest = hashlib.sha256(payload).hexdigest()
                captured[source_key] = (target, digest)
                existing = (target, digest)
        except OSError as exc:
            raise ValueError(f"RGC evaluation blocked: cannot snapshot {name}: {source}") from exc
        snapshots[name], digests[name] = existing
    return snapshots, digests


def _git_commit() -> str | None:
    git_root = ROOT
    if os.environ.get("AYORAI_RGC_SNAPSHOT_CHILD") == "1":
        git_root = Path(os.environ.get("AYORAI_RGC_GIT_ROOT", str(ROOT))).resolve()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=git_root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip()


def _worktree_clean() -> bool | None:
    """True when tracked and untracked files match the commit; None if git is unavailable."""
    git_root = ROOT
    if os.environ.get("AYORAI_RGC_SNAPSHOT_CHILD") == "1":
        git_root = Path(os.environ.get("AYORAI_RGC_GIT_ROOT", str(ROOT))).resolve()
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() == ""


def _canonical_sha256(payload: object) -> str:
    """SHA-256 of canonical JSON: sorted keys, compact separators, UTF-8."""
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
RUN_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "runner_version",
        "git_commit",
        "worktree_clean",
        "python",
        "python_implementation",
        "package_version",
        "partition",
        "started_at",
        "finished_at",
        "inputs",
        "config_sha256",
        "protocol_freeze_manifest_sha256",
        "runner_dependencies_sha256",
        "annotation_approval_manifest_sha256",
        "report",
    }
)


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _utc_timestamp(value: object, field: str) -> datetime:
    """Parse an ISO 8601 timestamp that must carry a zero UTC offset."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO 8601 timestamp") from exc
    offset = parsed.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise ValueError(f"{field} must be in UTC")
    return parsed


def _load_strict_json(path: Path, what: str) -> Any:
    """Read JSON, rejecting unreadable files, invalid JSON and duplicate keys."""

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{what} has a duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{what} cannot be read: {path}") from exc
    try:
        return json.loads(text, object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{what} is not valid JSON: {path}") from exc


def _manifest_fields_from_report(report: Mapping[str, Any]) -> dict[str, Any]:
    """Every run-manifest field that the report itself records.

    The report bytes are bound by their SHA-256, so each of these fields is bound too;
    only ``finished_at`` (written after the report) and the report digest are not.
    """
    try:
        freeze = report["protocol_freeze"]
        approval = report["annotation_approval"]
        return {
            "schema": RUN_MANIFEST_SCHEMA,
            "runner_version": report["runner_version"],
            "git_commit": report["git_commit"],
            "worktree_clean": report["worktree_clean"],
            "python": report["python"],
            "python_implementation": report["python_implementation"],
            "package_version": report["package_version"],
            "partition": report["config"]["partition"],
            "started_at": report["started_at"],
            "inputs": report["inputs"],
            "config_sha256": _canonical_sha256(report["config"]),
            "protocol_freeze_manifest_sha256": freeze["manifest_sha256"],
            "runner_dependencies_sha256": freeze["runner_dependencies_sha256"],
            "annotation_approval_manifest_sha256": approval["manifest_sha256"],
        }
    except (KeyError, TypeError) as exc:
        raise ValueError(f"report lacks a field the run manifest binds: {exc}") from exc


def build_run_manifest(
    report: Mapping[str, Any], report_path: Path, *, finished_at: str
) -> dict[str, Any]:
    """Technical record of one execution (E5). It binds the exact report bytes, the
    inputs, the configuration, the code version and the approvals the run relied on.

    It does not approve, freeze or publish anything: methodological approval lives in
    the freeze and annotation manifests, and publication is a separate human decision.
    """
    return {
        **_manifest_fields_from_report(report),
        "finished_at": finished_at,
        "report": {"file": report_path.name, "sha256": _sha256(report_path)},
    }


def _package_version() -> str:
    from ayorai_attractor import __version__

    return str(__version__)


def verify_run_manifest(
    manifest_path: Path,
    report_path: Path,
    *,
    root: Path | None = None,
    input_files: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Check every field of a run manifest; raise ValueError on any difference.

    Checked: the schema and the exact field set, field types and digest formats, the
    report file name and SHA-256, every field recorded in the report (runner, commit,
    clean worktree, Python, package, partition, start time, inputs, canonical config,
    freeze, dependency and approval digests), the hidden-partition requirement of a
    resolvable commit and a clean worktree, and started_at <= generated_at <=
    finished_at. Optionally, ``input_files`` maps input digest fields (for example
    ``cases_sha256``) to files whose bytes are hashed again, and ``root`` is a checkout
    whose runner code and statistical dependencies are hashed again and compared with
    the frozen digests recorded in the report.

    Limits: SHA-256 gives integrity, not authenticity. Anyone able to rewrite both
    files can produce a consistent pair; there is no signature. ``finished_at`` is only
    checked for format and order. The commit is checked for format, not for existence
    in a repository.
    """
    if not manifest_path.is_file():
        raise ValueError(f"run manifest is missing: {manifest_path}")
    if not report_path.is_file():
        raise ValueError(f"report is missing: {report_path}")
    manifest = _load_strict_json(manifest_path, "run manifest")
    report = _load_strict_json(report_path, "report")
    if not isinstance(manifest, dict):
        raise ValueError("run manifest must be a JSON object")
    if manifest.get("schema") != RUN_MANIFEST_SCHEMA:
        raise ValueError(f"run manifest schema must be {RUN_MANIFEST_SCHEMA}")
    if set(manifest) != RUN_MANIFEST_FIELDS:
        missing = sorted(RUN_MANIFEST_FIELDS - set(manifest))
        extra = sorted(set(manifest) - RUN_MANIFEST_FIELDS)
        raise ValueError(f"run manifest fields differ: missing={missing} extra={extra}")
    if not isinstance(report, dict):
        raise ValueError("report must be a JSON object")

    bound = manifest["report"]
    if not isinstance(bound, dict) or set(bound) != {"file", "sha256"}:
        raise ValueError("run manifest report entry must have exactly file and sha256")
    if not _is_sha256(bound["sha256"]):
        raise ValueError("report.sha256 is not a SHA-256 hex digest")
    if bound["file"] != report_path.name:
        raise ValueError("report.file does not name the report being verified")
    if bound["sha256"] != _sha256(report_path):
        raise ValueError("report bytes differ from the run manifest")

    for field in (
        "config_sha256",
        "protocol_freeze_manifest_sha256",
        "annotation_approval_manifest_sha256",
    ):
        if not _is_sha256(manifest[field]):
            raise ValueError(f"{field} is not a SHA-256 hex digest")
    dependencies = manifest["runner_dependencies_sha256"]
    if (
        not isinstance(dependencies, dict)
        or set(dependencies) != set(RUNNER_DEPENDENCIES)
        or not all(_is_sha256(value) for value in dependencies.values())
    ):
        raise ValueError(
            f"runner_dependencies_sha256 must map exactly {list(RUNNER_DEPENDENCIES)} "
            "to SHA-256 hex digests"
        )
    inputs = manifest["inputs"]
    if not isinstance(inputs, dict) or not any(key.endswith("_sha256") for key in inputs):
        raise ValueError("inputs must be an object with input digests")
    for key, value in inputs.items():
        if key.endswith("_sha256") and not _is_sha256(value):
            raise ValueError(f"inputs.{key} is not a SHA-256 hex digest")
    for field in ("runner_version", "python", "python_implementation", "package_version"):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise ValueError(f"{field} must be a non-empty string")
    commit = manifest["git_commit"]
    if commit is not None and (not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit)):
        raise ValueError("git_commit must be a 40-character lowercase hex SHA-1 or null")
    if manifest["worktree_clean"] is not None and type(manifest["worktree_clean"]) is not bool:
        raise ValueError("worktree_clean must be true, false or null")
    if manifest["partition"] not in ("hidden", "development"):
        raise ValueError("partition must be hidden or development")

    expected = _manifest_fields_from_report(report)
    for field, value in expected.items():
        # bool is a subclass of int in Python; compare JSON types exactly.
        if manifest[field] != value or type(manifest[field]) is not type(value):
            raise ValueError(f"{field} differs between report and run manifest")

    if manifest["partition"] == "hidden" and (
        commit is None or manifest["worktree_clean"] is not True
    ):
        raise ValueError(
            "hidden-partition run must record a resolvable commit and a clean worktree"
        )

    started = _utc_timestamp(manifest["started_at"], "started_at")
    generated = _utc_timestamp(report.get("generated_at"), "generated_at")
    finished = _utc_timestamp(manifest["finished_at"], "finished_at")
    if not started <= generated <= finished:
        raise ValueError("timestamps must satisfy started_at <= generated_at <= finished_at")

    for key, path in (input_files or {}).items():
        if not key.endswith("_sha256") or key not in inputs:
            raise ValueError(f"inputs has no digest field {key!r}")
        try:
            actual = _sha256(path)
        except OSError as exc:
            raise ValueError(f"input file for {key} cannot be read: {path}") from exc
        if inputs[key] != actual:
            raise ValueError(f"inputs.{key} differs from {path}")

    if root is not None:
        freeze = report["protocol_freeze"]
        frozen = {
            "evals/ptbr/rgc_eval.py": freeze.get("runner_code_sha256"),
            **freeze["runner_dependencies_sha256"],
        }
        for relative, digest in frozen.items():
            try:
                actual = _sha256(root / relative)
            except OSError as exc:
                raise ValueError(f"{relative} is missing under {root}") from exc
            if actual != digest:
                raise ValueError(
                    f"{relative} differs from the frozen code that produced the report"
                )
    return manifest


def _atomic_write_text(path: Path, text: str) -> None:
    """Publish a fully written temporary file with atomic no-overwrite semantics."""
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    linked = False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # Hard-link publication is atomic and refuses an existing destination. Unlike
        # os.replace(), it cannot overwrite a report created by a concurrent run.
        os.link(temporary, path)
        linked = True
        Path(temporary).unlink()
    except BaseException:
        if linked:
            Path(path).unlink(missing_ok=True)
        Path(temporary).unlink(missing_ok=True)
        raise


def _publish_run(
    report: Mapping[str, Any],
    out: Path,
    manifest_path: Path,
    *,
    input_files: Mapping[str, Path] | None = None,
    root: Path | None = None,
) -> int:
    """Write a report and its run manifest as one unit; return 0 or exit code 2.

    Never overwrites: an existing report or manifest is refused, so an earlier file can
    never be paired with this run. Both files are written to temporaries and checked
    before either becomes visible. If anything fails after the report is in place, the
    report and the manifest written by this call are removed, so a failed run leaves no
    report that looks complete. A crash between the two atomic link publications can
    still leave a report without a manifest; verify_run_manifest then refuses it.
    """
    if out.exists() or manifest_path.exists():
        print(
            f"RGC run refused: {out} or {manifest_path} already exists; choose a new --out",
            file=sys.stderr,
        )
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    report_text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    published: list[Path] = []
    try:
        _atomic_write_text(out, report_text)
        published.append(out)
        manifest = build_run_manifest(
            report, out, finished_at=datetime.now(UTC).isoformat(timespec="seconds")
        )
        _atomic_write_text(
            manifest_path,
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        )
        published.append(manifest_path)
        verify_run_manifest(manifest_path, out, input_files=input_files, root=root)
    except (OSError, ValueError) as exc:
        for path in published:
            path.unlink(missing_ok=True)
        print(f"RGC run incomplete: no report or manifest was kept ({exc})", file=sys.stderr)
        return 2
    return 0


def load_labels(path: Path, vocabulary: str) -> dict[str, str]:
    """Load strict JSONL gold labels without coercing malformed input."""
    allowed = set(VOCABULARIES[vocabulary]) | EXCLUSION_LABELS
    labels: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise ValueError(f"{path}:{line_number}: blank lines are not allowed")
        try:
            row = json.loads(line, object_pairs_hook=_reject_duplicate_json_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
        except ValueError as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
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
    pilot_mode: bool = False,
) -> dict[str, Any]:
    if partition not in {"hidden", "development"}:
        raise ValueError("partition must be hidden or development")
    if mode not in {"oracle", "retrieval"}:
        raise ValueError("mode must be oracle or retrieval")
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

    # Preflight the complete evaluation set before invoking the predictor.
    # This prevents partial prediction side effects when a later case is invalid.
    seen: set[str] = set()
    unlabeled: list[str] = []
    oracle_evidence: dict[str, list[Passage]] = {}
    for case in cases:
        case_id = str(case["case_id"])
        if case_id in seen:
            raise ValueError(f"{case_id}: duplicate case")
        seen.add(case_id)
        case_rectified(case)
        gold = labels.get(case_id)
        if gold is None:
            unlabeled.append(case_id)
            continue
        if not isinstance(gold, str) or (
            gold not in VOCABULARIES[vocabulary] and gold not in EXCLUSION_LABELS
        ):
            raise ValueError(f"{case_id}: invalid gold label {gold!r} for vocabulary {vocabulary}")
        _validate_rule_gap_policy(gold, pilot_mode=pilot_mode, partition=partition)
        cluster_id = case.get("bootstrap_cluster_id")
        if partition == "hidden" and (not isinstance(cluster_id, str) or not cluster_id.strip()):
            raise ValueError(
                f"{case_id}: missing or invalid bootstrap_cluster_id for hidden partition"
            )
        has_cluster_id = "bootstrap_cluster_id" in case
        has_cited_article_ids = "cited_article_ids" in case
        if partition == "hidden" or has_cluster_id or has_cited_article_ids:
            validate_cluster_citations(
                case,
                cluster_id,
                case_id,
                require_citations=partition == "hidden",
                require_cluster=partition == "hidden" or has_cluster_id,
            )
        if gold in EXCLUSION_LABELS:
            continue
        claim = case.get("claim")
        if not isinstance(claim, str) or not claim.strip():
            raise ValueError(f"{case_id}: claim must be a non-empty string")
        case_atoms(case)
        if mode == "oracle":
            # Resolve oracle evidence up front: a missing document or a
            # mismatched excerpt must stop the run before any prediction.
            try:
                oracle_evidence[case_id] = oracle_passages(case, documents)
            except (KeyError, TypeError) as exc:
                raise ValueError(f"{case_id}: malformed oracle evidence ({exc!r})") from exc
    if unlabeled:
        raise ValueError(f"cases without a label (labels must be complete): {unlabeled}")
    extra = sorted(set(labels) - seen)
    if extra:
        raise ValueError(f"labels for unknown cases (files do not match): {extra}")

    index: BM25Index | None = None
    if mode == "retrieval":
        passages = [p for doc in documents.values() for p in segment(doc, granularity)]
        index = BM25Index(passages, documents)
    rows: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for case in cases:
        case_id = str(case["case_id"])
        rectified = case_rectified(case)
        gold = labels[case_id]
        if gold in EXCLUSION_LABELS:
            excluded.append({"case_id": case_id, "label": gold})
            continue
        cluster_id = case.get("bootstrap_cluster_id")
        atoms = case_atoms(case)
        if index is None:
            prediction = predict(case["claim"], oracle_evidence[case_id], documents, atoms=atoms)
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
    component_ids: list[str] | None = None
    if partition == "hidden":
        # DEC-023 components over the evaluated cases, from their full citations.
        case_by_id = {str(case["case_id"]): case for case in cases}
        summary = build_article_components(
            [
                {
                    "case_id": str(row["case_id"]),
                    "cited_article_ids": case_by_id[str(row["case_id"])]["cited_article_ids"],
                    "bootstrap_cluster_id": row["bootstrap_cluster_id"],
                }
                for row in rows
            ]
        )
        component_of = {
            case_id: component.component_id
            for component in summary.components
            for case_id in component.case_ids
        }
        component_ids = [component_of[str(row["case_id"])] for row in rows]
    metrics = compute_metrics(
        gold_labels,
        predicted,
        vocabulary,
        baseline_label=baseline_label,
        iterations=iterations,
        cluster_ids=cluster_ids,
        component_ids=component_ids,
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



def _assert_loaded_modules_from_snapshot(
    snapshot_root: Path,
    expected_code_hashes: Mapping[str, str],
    loaded_modules: Mapping[str, Any] | None = None,
) -> None:
    """Fail closed unless every loaded AYORAI/evaluation module came from captured bytes."""
    runner_relative = "evals/ptbr/rgc_eval.py"
    runner_path = Path(__file__).resolve()
    expected_runner = (snapshot_root / runner_relative).resolve()
    if runner_path != expected_runner:
        raise ValueError("RGC evaluation blocked: runner was not executed from its code snapshot")
    expected_runner_hash = expected_code_hashes.get(runner_relative)
    if expected_runner_hash is None or _sha256(runner_path) != expected_runner_hash:
        raise ValueError("RGC evaluation blocked: runner bytes differ from captured snapshot")

    modules = sys.modules if loaded_modules is None else loaded_modules
    for name, module in tuple(modules.items()):
        if not (
            name == "ayorai_attractor"
            or name.startswith("ayorai_attractor.")
            or name.startswith("evals.ptbr.")
        ):
            continue
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue  # namespace package
        origin_path = Path(origin).resolve()
        try:
            relative = origin_path.relative_to(snapshot_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError(
                f"RGC evaluation blocked: module {name} was imported outside the snapshot"
            ) from exc
        if relative.startswith(("src/ayorai_attractor/", "evals/ptbr/")):
            expected = expected_code_hashes.get(relative)
            if expected is None or _sha256(origin_path) != expected:
                raise ValueError(
                    f"RGC evaluation blocked: loaded module {name} is not bound "
                    "to the captured source bytes"
                )


def _run_evaluation(args: argparse.Namespace) -> int:
    """Capture first, then evaluate in a fresh interpreter importing only that snapshot."""
    if os.environ.get("AYORAI_RGC_SNAPSHOT_CHILD") == "1":
        try:
            expected = json.loads(os.environ["AYORAI_RGC_EXPECTED_CODE_SHA256"])
            if not isinstance(expected, dict) or any(
                not isinstance(key, str) or not isinstance(value, str)
                for key, value in expected.items()
            ):
                raise ValueError("invalid expected code digest map")
            _assert_loaded_modules_from_snapshot(ROOT, expected)
        except (KeyError, TypeError, ValueError, OSError) as exc:
            print(f"RGC evaluation blocked: invalid execution provenance: {exc}", file=sys.stderr)
            return 2
        return _run_evaluation_in_process(args)

    git_commit = _git_commit()
    worktree_clean = _worktree_clean()
    if args.partition == "hidden" and (git_commit is None or worktree_clean is not True):
        print(
            "RGC evaluation blocked: the hidden partition runs only from a clean git "
            "checkout with a resolvable commit",
            file=sys.stderr,
        )
        return 2

    freeze_relatives = (
        "docs/eval/PROTOCOL-GOLDEN-V1.md",
        "docs/eval/PREREGISTRATION-RGC-v1.md",
        "docs/eval/RUNNER-RGC-v1.md",
        "docs/eval/PROTOCOL-FREEZE.json",
        "evals/ptbr/rgc_eval.py",
        *RUNNER_DEPENDENCIES,
    )
    input_sources = {
        "inputs/cases.jsonl": args.cases,
        "inputs/labels.jsonl": args.labels,
        "inputs/annotation-a.jsonl": args.annotation_a,
        "inputs/annotation-b.jsonl": args.annotation_b,
        "inputs/agreement-report.json": args.agreement_report,
        "inputs/annotation-approval.json": args.annotation_approval,
        "inputs/adjudication-record.json": args.adjudication_record,
        "inputs/development-cases.jsonl": args.development_cases,
        "inputs/development-labels.jsonl": args.development_labels,
        "inputs/documents.jsonl": args.documents,
    }
    sources = {relative: ROOT / relative for relative in freeze_relatives}
    sources.update(input_sources)

    try:
        with tempfile.TemporaryDirectory(prefix="ayorai-rgc-execution-") as temporary:
            snapshot_root = Path(temporary)
            snapshots, snapshot_hashes = _snapshot_files(sources, snapshot_root)
            if _git_commit() != git_commit or _worktree_clean() != worktree_clean:
                raise ValueError(
                    "RGC evaluation blocked: Git checkout identity changed during code capture"
                )
            expected_code = {
                relative: snapshot_hashes[relative]
                for relative in freeze_relatives
                if relative.endswith(".py")
            }
            environment = os.environ.copy()
            environment["AYORAI_RGC_SNAPSHOT_CHILD"] = "1"
            environment["AYORAI_RGC_GIT_ROOT"] = str(ROOT.resolve())
            environment["AYORAI_RGC_EXPECTED_GIT_COMMIT"] = git_commit or ""
            environment["AYORAI_RGC_EXPECTED_WORKTREE_CLEAN"] = str(worktree_clean).lower()
            environment["AYORAI_RGC_EXPECTED_CODE_SHA256"] = json.dumps(
                expected_code, sort_keys=True, separators=(",", ":")
            )
            environment["AYORAI_RGC_EXPECTED_SNAPSHOT_SHA256"] = json.dumps(
                snapshot_hashes, sort_keys=True, separators=(",", ":")
            )
            # Do not inherit a caller-controlled PYTHONPATH. The child imports the
            # package and eval modules from the immutable snapshot before site-packages.
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(snapshot_root / "src"), str(snapshot_root))
            )
            command = [
                sys.executable,
                "-B",
                str(snapshots["evals/ptbr/rgc_eval.py"]),
                "run",
                str(snapshots["inputs/cases.jsonl"]),
                "--labels",
                str(snapshots["inputs/labels.jsonl"]),
                "--annotation-a",
                str(snapshots["inputs/annotation-a.jsonl"]),
                "--annotation-b",
                str(snapshots["inputs/annotation-b.jsonl"]),
                "--agreement-report",
                str(snapshots["inputs/agreement-report.json"]),
                "--annotation-approval",
                str(snapshots["inputs/annotation-approval.json"]),
                "--adjudication-record",
                str(snapshots["inputs/adjudication-record.json"]),
                "--development-cases",
                str(snapshots["inputs/development-cases.jsonl"]),
                "--development-labels",
                str(snapshots["inputs/development-labels.jsonl"]),
                "--documents",
                str(snapshots["inputs/documents.jsonl"]),
                "--mode",
                args.mode,
                "--vocabulary",
                args.vocabulary,
                "--top-k",
                str(args.top_k),
                "--partition",
                args.partition,
                "--granularity",
                args.granularity,
                "--out",
                str(args.out.resolve()),
            ]
            completed = subprocess.run(
                command,
                cwd=snapshot_root,
                env=environment,
                check=False,
            )
            return completed.returncode
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _run_evaluation_in_process(args: argparse.Namespace) -> int:
    """Evaluate in the isolated child whose imports come only from captured code."""
    git_commit = _git_commit()
    worktree_clean = _worktree_clean()
    if os.environ.get("AYORAI_RGC_SNAPSHOT_CHILD") == "1":
        expected_commit = os.environ.get("AYORAI_RGC_EXPECTED_GIT_COMMIT", "")
        expected_clean = os.environ.get("AYORAI_RGC_EXPECTED_WORKTREE_CLEAN")
        if expected_commit != (git_commit or "") or expected_clean != str(worktree_clean).lower():
            print(
                "RGC evaluation blocked: Git checkout identity changed between capture and execution",
                file=sys.stderr,
            )
            return 2
    if args.partition == "hidden" and (git_commit is None or worktree_clean is not True):
        print(
            "RGC evaluation blocked: the hidden partition runs only from a clean git "
            "checkout with a resolvable commit",
            file=sys.stderr,
        )
        return 2

    previous_judge_rules_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="ayorai-rgc-snapshot-") as temporary:
        snapshot_root = Path(temporary)
        freeze_relatives = (
            "docs/eval/PROTOCOL-GOLDEN-V1.md",
            "docs/eval/PREREGISTRATION-RGC-v1.md",
            "docs/eval/RUNNER-RGC-v1.md",
            "docs/eval/PROTOCOL-FREEZE.json",
            "evals/ptbr/rgc_eval.py",
            *RUNNER_DEPENDENCIES,
        )
        sources: dict[str, Path] = {relative: ROOT / relative for relative in freeze_relatives}
        input_sources = {
            "inputs/cases.jsonl": args.cases,
            "inputs/labels.jsonl": args.labels,
            "inputs/annotation-a.jsonl": args.annotation_a,
            "inputs/annotation-b.jsonl": args.annotation_b,
            "inputs/agreement-report.json": args.agreement_report,
            "inputs/annotation-approval.json": args.annotation_approval,
            "inputs/adjudication-record.json": args.adjudication_record,
            "inputs/development-cases.jsonl": args.development_cases,
            "inputs/development-labels.jsonl": args.development_labels,
            "inputs/documents.jsonl": args.documents,
        }
        sources.update(input_sources)
        try:
            snapshots, snapshot_hashes = _snapshot_files(sources, snapshot_root)
            if os.environ.get("AYORAI_RGC_SNAPSHOT_CHILD") == "1":
                expected_snapshot = json.loads(os.environ["AYORAI_RGC_EXPECTED_SNAPSHOT_SHA256"])
                if not isinstance(expected_snapshot, dict):
                    raise ValueError("RGC evaluation blocked: invalid expected snapshot digest map")
                for relative, expected_digest in expected_snapshot.items():
                    if snapshot_hashes.get(relative) != expected_digest:
                        raise ValueError(
                            "RGC evaluation blocked: captured artifact changed between "
                            f"parent and isolated child: {relative}"
                        )

            # Judge 2.0 must load its rule contract from the same captured bytes
            # that the freeze validator hashed, not from its import-time checkout path.
            previous_judge_rules_path = judge2_module._RULES_PATH
            judge2_module._RULES_PATH = snapshots["rules/judge-2.0.0.json"]

            # Freeze and approval validation operate on the captured bytes only.
            protocol_freeze = validate_protocol_freeze(root=snapshot_root)
            annotation_approval = validate_annotation_approval(
                snapshots["inputs/cases.jsonl"],
                snapshots["inputs/labels.jsonl"],
                snapshots["inputs/development-cases.jsonl"],
                snapshots["inputs/development-labels.jsonl"],
                snapshots["inputs/annotation-a.jsonl"],
                snapshots["inputs/annotation-b.jsonl"],
                snapshots["inputs/agreement-report.json"],
                snapshots["inputs/annotation-approval.json"],
                snapshots["inputs/adjudication-record.json"],
            )

            started_at = datetime.now(UTC).isoformat(timespec="seconds")
            documents = load_documents(snapshots["inputs/documents.jsonl"])
            development_cases = _read_jsonl(snapshots["inputs/development-cases.jsonl"])
            development_labels = load_labels(
                snapshots["inputs/development-labels.jsonl"], args.vocabulary
            )
            result = evaluate(
                _read_jsonl(snapshots["inputs/cases.jsonl"]),
                load_labels(snapshots["inputs/labels.jsonl"], args.vocabulary),
                documents,
                development_cases=development_cases,
                development_labels=development_labels,
                mode=args.mode,
                vocabulary=args.vocabulary,
                top_k=args.top_k,
                granularity=args.granularity,
                partition=args.partition,
            )
            generated_at = datetime.now(UTC).isoformat(timespec="seconds")
            input_report = {
                "cases": str(args.cases),
                "cases_sha256": snapshot_hashes["inputs/cases.jsonl"],
                "labels": str(args.labels),
                "labels_sha256": snapshot_hashes["inputs/labels.jsonl"],
                "development_cases": str(args.development_cases),
                "development_cases_sha256": snapshot_hashes["inputs/development-cases.jsonl"],
                "development_labels": str(args.development_labels),
                "development_labels_sha256": snapshot_hashes["inputs/development-labels.jsonl"],
                "documents": str(args.documents),
                "documents_sha256": snapshot_hashes["inputs/documents.jsonl"],
                "annotation_a": str(args.annotation_a),
                "annotation_a_sha256": snapshot_hashes["inputs/annotation-a.jsonl"],
                "annotation_b": str(args.annotation_b),
                "annotation_b_sha256": snapshot_hashes["inputs/annotation-b.jsonl"],
                "agreement_report": str(args.agreement_report),
                "agreement_report_sha256": snapshot_hashes["inputs/agreement-report.json"],
                "annotation_approval": str(args.annotation_approval),
                "annotation_approval_sha256": snapshot_hashes["inputs/annotation-approval.json"],
                "adjudication_record": str(args.adjudication_record),
                "adjudication_record_sha256": snapshot_hashes["inputs/adjudication-record.json"],
            }
            report = {
                "runner_version": RUNNER_VERSION,
                "protocol_freeze": protocol_freeze,
                "annotation_approval": annotation_approval,
                "started_at": started_at,
                "generated_at": generated_at,
                "git_commit": git_commit,
                "worktree_clean": worktree_clean,
                "python": sys.version.split()[0],
                "python_implementation": platform.python_implementation(),
                "package_version": _package_version(),
                "runtime_dependencies": {
                    name: distribution_version(name)
                    for name in ("pydantic", "pydantic-core", "rfc8785")
                },
                "inputs": input_report,
                "config": {
                    "partition": args.partition,
                    "mode": args.mode,
                    "vocabulary": args.vocabulary,
                    "top_k": args.top_k,
                    "granularity": args.granularity,
                    "bm25": {"k1": BM25_K1, "b": BM25_B},
                    "stance_detector": (
                        f"{RuleStanceDetector.component}/{RuleStanceDetector.version}"
                    ),
                    "bootstrap": {
                        "iterations": BOOTSTRAP_ITERATIONS,
                        "seed": SEED,
                        "generator": "RGC-PRNG-1",
                        "percentile": "hyndman-fan-type-7",
                        "primary_unit": ("component" if args.partition == "hidden" else "case"),
                        "sensitivity_units": (
                            ["article_cluster", "case"] if args.partition == "hidden" else []
                        ),
                    },
                    "h1_test": (
                        "sign_flip_by_component" if args.partition == "hidden" else "not_tested"
                    ),
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
            if _git_commit() != git_commit or _worktree_clean() != worktree_clean:
                raise ValueError(
                    "RGC evaluation blocked: checkout identity or worktree state changed "
                    "during the run"
                )

            manifest_path = args.out.with_name(args.out.name + ".manifest.json")
            input_files = {
                "cases_sha256": snapshots["inputs/cases.jsonl"],
                "labels_sha256": snapshots["inputs/labels.jsonl"],
                "development_cases_sha256": snapshots["inputs/development-cases.jsonl"],
                "development_labels_sha256": snapshots["inputs/development-labels.jsonl"],
                "documents_sha256": snapshots["inputs/documents.jsonl"],
                "annotation_a_sha256": snapshots["inputs/annotation-a.jsonl"],
                "annotation_b_sha256": snapshots["inputs/annotation-b.jsonl"],
                "agreement_report_sha256": snapshots["inputs/agreement-report.json"],
                "annotation_approval_sha256": snapshots["inputs/annotation-approval.json"],
                "adjudication_record_sha256": snapshots["inputs/adjudication-record.json"],
            }
            status = _publish_run(
                report,
                args.out,
                manifest_path,
                input_files=input_files,
                root=snapshot_root,
            )
            if status != 0:
                return status
            print(f"run manifest {manifest_path} sha256={_sha256(manifest_path)}")
            metrics = result["metrics"]
            print(
                f"n={metrics['n']} accuracy={metrics['system']['accuracy']} "
                f"baseline_B={metrics['baseline_primary']['accuracy']} "
                f"baseline_A_descriptive={metrics['baseline_descriptive']['accuracy']} "
                f"h1={metrics['primary_criterion']['h1_supported']}"
            )
            return 0
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        finally:
            if previous_judge_rules_path is not None:
                judge2_module._RULES_PATH = previous_judge_rules_path


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

    if args.command == "export-corpus":
        try:
            documents = load_documents(args.documents)
            args.out.write_text(export_strict_corpus(documents), encoding="utf-8")
        except (OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"wrote {len(documents)} documents to {args.out}")
        return 0

    return _run_evaluation(args)


if __name__ == "__main__":
    sys.exit(main())
