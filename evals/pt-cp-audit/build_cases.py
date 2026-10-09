"""Build the PT-CP-Audit simulation: AI legal-assistant claims vs. the real Penal Code.

Evidence is always the verbatim, current text of a provision of the Brazilian
Penal Code (Decreto-Lei 2.848/1940, Parte Geral), captured from planalto.gov.br
on 2026-09-15 by the public-domain dataset wagnermarques/legis-dados
(commit 3951145d42cce0f575a075551e239e2968e764dd). Official legal texts are not
protected by copyright (Lei 9.610/1998, art. 8º, IV).

Labels are by construction against that text:
- supports: the claim restates the provision (AI-style paraphrase);
- contradicts: the claim states something the provision rules out (wrong number,
  outdated rule, negation, inverted direction, wrong actor) — typical assistant
  hallucinations;
- neutral: the evidence is a different, related provision that does not decide
  the claim (a retrieval mistake an auditor must not accept as support).

A second, mechanical block mutates numbers written as "N (extenso)" in the
provisions: the verbatim text supports itself; the mutated text contradicts it.

The split into dev/test is by provision (all cases sharing an evidence provision
go to the same split), deterministic with seed 20261003.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "cp-parte-geral-dispositivos.json"
OUT = HERE / "cases.jsonl"
SOURCE_URL = "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"
DATASET = "github.com/wagnermarques/legis-dados@3951145d42cce0f575a075551e239e2968e764dd"
SEED = 20261003
TEST_FRACTION = 0.5

S, C = "supports", "contradicts"
HAND_CASES = HERE / "hand_cases.jsonl"


def _hand() -> list[tuple[str, str, str, str]]:
    """Hand-written claims: (evidence provision id, label, difficulty type, claim)."""
    rows = [json.loads(line) for line in HAND_CASES.read_text(encoding="utf-8").splitlines()]
    return [(r["evidence_id"], r["label"], r["type"], r["claim"]) for r in rows]


NUMBER_WORDS = {
    1: "um",
    2: "dois",
    3: "três",
    4: "quatro",
    5: "cinco",
    6: "seis",
    8: "oito",
    10: "dez",
    12: "doze",
    15: "quinze",
    18: "dezoito",
    20: "vinte",
    21: "vinte e um",
    25: "vinte e cinco",
    30: "trinta",
    40: "quarenta",
    45: "quarenta e cinco",
    50: "cinquenta",
    60: "sessenta",
    70: "setenta",
    360: "trezentos e sessenta",
    400: "quatrocentos",
}
MUTATION = {
    1: 2,
    2: 3,
    3: 5,
    4: 6,
    5: 10,
    6: 8,
    8: 10,
    10: 15,
    12: 18,
    18: 21,
    21: 25,
    40: 30,
    70: 60,
    360: 400,
}
PAIR_RE = re.compile(r"\b(\d{1,3}) \(([a-zà-ú ]+)\)")


def _text(provisions: dict[str, dict], pid: str) -> str:
    return str(provisions[pid]["versoes"][-1]["texto"])


def _mutations(provisions: dict[str, dict]) -> list[tuple[str, str, str, str]]:
    out: list[tuple[str, str, str, str]] = []
    for pid in provisions:
        text = _text(provisions, pid)
        match = next((m for m in PAIR_RE.finditer(text) if int(m.group(1)) in MUTATION), None)
        if match is None:
            continue
        old = int(match.group(1))
        new = MUTATION[old]
        mutated = text[: match.start()] + f"{new} ({NUMBER_WORDS[new]})" + text[match.end() :]
        out.append((pid, S, "verbatim", text))
        out.append((pid, C, "mutacao-numero", mutated))
    return out


def build() -> list[dict]:
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    provisions = {str(item["id"]): item for item in raw}
    rows = [(pid, lab, typ, claim, "hand") for pid, lab, typ, claim in _hand()]
    rows += [(pid, lab, typ, claim, "mutation") for pid, lab, typ, claim in _mutations(provisions)]
    evidence_ids = sorted({row[0] for row in rows})
    rng = random.Random(SEED)
    shuffled = evidence_ids[:]
    rng.shuffle(shuffled)
    test_ids = set(shuffled[: round(len(shuffled) * TEST_FRACTION)])
    cases = []
    for index, (pid, label, kind, claim, origin) in enumerate(rows, start=1):
        if pid not in provisions:
            raise KeyError(pid)
        version = provisions[pid]["versoes"][-1]
        cases.append(
            {
                "id": f"cp-{index:03d}",
                "split": "test" if pid in test_ids else "dev",
                "origin": origin,
                "type": kind,
                "label": label,
                "claim": claim,
                "evidence_id": pid,
                "evidence_label": provisions[pid]["rotulo"],
                "evidence": version["texto"],
                "source_url": SOURCE_URL,
                "captured_at": version["capturadoEm"],
                "dataset": DATASET,
            }
        )
    return cases


def main() -> None:
    cases = build()
    OUT.write_text(
        "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases), encoding="utf-8"
    )
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"cases={len(cases)} sha256={digest}")


if __name__ == "__main__":
    main()
