"""Reproduce the exploratory PT-CP DEV observation behind PROTOCOL-PASSAGE-RELATION-v0.

EXPLORATORY ONLY. Uses the DEV split of evals/pt-cp-audit (already used to develop the
stance rules). TEST records are never read: the cases come from the byte ranges listed
in ptcp_dev_index.json, each checked against its SHA-256 and its "split" field, and no
other byte of cases.jsonl is read. Its numbers motivate the protocol; they are not
evidence of any improvement and must not be used to tune or confirm a variant.

Document: the current text of every Parte Geral provision, one per line. Cases: DEV
cases labelled supports/contradicts, whose gold provision is the relevant one (the
neutral cases were built as wrong-retrieval pairs and have no end-to-end gold).

Usage:
    python -m evals.passage_relation.exploratory_ptcp_dev
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, BinaryIO

from ayorai_attractor.verification.document_check import CheckDocumentInput, check_documents

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "evals" / "pt-cp-audit"
DEV_INDEX = Path(__file__).resolve().parent / "ptcp_dev_index.json"
# ADR-002 needs two independent support clusters for SUPPORTED; one document gives at
# most PARTIALLY_SUPPORTED, which is the best attainable outcome here.
BEST = {"supports": "partially_supported", "contradicts": "refuted"}


def _document() -> tuple[CheckDocumentInput, list[tuple[int, int, str]]]:
    items = json.loads((AUDIT / "cp-parte-geral-dispositivos.json").read_text("utf-8"))
    lines: list[str] = []
    spans: list[tuple[int, int, str]] = []
    position = 0
    for item in items:
        current = [v for v in item["versoes"] if v.get("vigenteAte") is None]
        if not current or not current[-1].get("texto"):
            continue
        text = f"{item.get('rotulo', '')} {current[-1]['texto']}".strip()
        spans.append((position, position + len(text), item["id"]))
        lines.append(text)
        position += len(text) + 1
    return CheckDocumentInput(id="cp-parte-geral", text="\n".join(lines)), spans


def dev_cases(
    index_path: Path = DEV_INDEX, opener: Callable[[Path], BinaryIO] | None = None
) -> list[dict[str, Any]]:
    """Read only the indexed DEV byte ranges of cases.jsonl, verifying each one."""

    index = json.loads(index_path.read_text("utf-8"))
    source = ROOT / index["source"]
    if source.stat().st_size != index["source_size"]:
        raise RuntimeError(f"{index['source']} changed since the DEV index was built")
    cases = []
    with (opener or (lambda path: path.open("rb")))(source) as handle:
        for entry in index["lines"]:
            handle.seek(entry["offset"])
            raw = handle.read(entry["length"])
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise RuntimeError(f"{entry['id']}: bytes differ from the DEV index")
            case = json.loads(raw)
            if case["id"] != entry["id"] or case["split"] != "dev" or case["label"] not in BEST:
                raise RuntimeError(f"{entry['id']}: not a DEV supports/contradicts case")
            cases.append(case)
    return cases


def measure() -> dict[str, Any]:
    document, spans = _document()
    cases = dev_cases()
    verdicts: Counter[str] = Counter()
    stance_gold: Counter[str] = Counter()
    stance_other: Counter[str] = Counter()
    gold_found = best = 0
    for case in cases:
        (result,) = check_documents([document], claims=[case["claim"]]).results
        verdicts[f"{case['label']}->{result.verdict}"] += 1
        best += result.verdict == BEST[case["label"]]
        found = False
        for evidence in result.evidence:
            provisions = {a for s, e, a in spans if s < evidence.end and evidence.start < e}
            gold = any(
                a == case["evidence_id"] or a.startswith(case["evidence_id"] + "-")
                for a in provisions
            )
            found |= gold
            (stance_gold if gold else stance_other)[f"{case['label']}:{evidence.stance}"] += 1
        gold_found += found
    return {
        "exploratory": True,
        "split": "dev",
        "cases": len(cases),
        "gold_provision_among_evidence": gold_found,
        "best_attainable_verdict": best,
        "verdicts": dict(sorted(verdicts.items())),
        "stance_on_gold_provision": dict(sorted(stance_gold.items())),
        "stance_on_other_provisions": dict(sorted(stance_other.items())),
    }


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2, ensure_ascii=False))
