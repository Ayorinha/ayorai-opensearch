"""Reproduce the exploratory PT-CP DEV observation behind PROTOCOL-PASSAGE-RELATION-v0.

EXPLORATORY ONLY. Reads the DEV split of evals/pt-cp-audit (already used to develop the
stance rules) and never the TEST split. Its numbers motivate the protocol; they are not
evidence of any improvement and must not be used to tune or confirm a variant.

Document: the current text of every Parte Geral provision, one per line. Cases: DEV
cases labelled supports/contradicts, whose gold provision is the relevant one (the
neutral cases were built as wrong-retrieval pairs and have no end-to-end gold).

Usage:
    python -m evals.passage_relation.exploratory_ptcp_dev
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from ayorai_attractor.verification.document_check import CheckDocumentInput, check_documents

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "evals" / "pt-cp-audit"
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


def measure() -> dict[str, Any]:
    document, spans = _document()
    rows = [json.loads(line) for line in (AUDIT / "cases.jsonl").read_text("utf-8").splitlines()]
    cases = [r for r in rows if r["split"] == "dev" and r["label"] in BEST]
    if any(case["split"] != "dev" for case in cases):  # defensive: TEST is never read
        raise RuntimeError("only the DEV split may be used")
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
