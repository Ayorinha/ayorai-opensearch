#!/usr/bin/env python3
"""Segmentation equivalence check between two NLTK versions (P4-01, nltk upgrade).

Runs ``sent_tokenize`` and ``word_tokenize`` (the two functions the Phase 1b shards use,
see ``run_shard._document_chunks``) with the pinned ``punkt_tab`` data on a deterministic
corpus and writes one SHA-256 per text and per function. Run it once under each NLTK
version and compare the two reports with ``--compare``.

The corpus holds no benchmark data (no DEV, no TEST): hand-written edge cases, the
repository's own prose (docs, README, CHANGELOG) and seeded synthetic text built from
the constructs the tokenizers treat specially (abbreviations, decimals, quotes,
apostrophes, brackets, ellipses, newlines, Unicode punctuation).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SEED = 20261128
SYNTHETIC_COUNT = 20_000

EDGE_CASES = [
    "Dr. Smith went to Washington. He arrived at 3 p.m. on Jan. 5th.",
    "The U.S. economy grew 2.5% in Q3. Analysts, e.g. Mr. Jones, disagreed.",
    "It costs $4.50... or so they say. Really?! Yes.",
    "'Tis the season. 'Hello,' she said. He said 'no'.",
    "They're here; we've seen 'em. Don't you know? I'd've gone.",
    "'model' and 'a' and 'quoted words' in single quotes.",
    "rock 'n' roll, the '90s, and 'twas brillig.",
    "\"Double quotes,\" he said. ``Backticks'' too. «Guillemets» and “curly”.",
    "Lists: (a) first; (b) second [see Fig. 2]; {c} third <d> fourth.",
    "Line one\nLine two without period\n\nNew paragraph. Next sentence.",
    "Version 3.10.4 of the lib vs. v2.0. See https://example.org/a.b?c=d#e. Done.",
    "Numbers like 1,000,000 and 3.14159 and 1e-5 and -42 stay intact.",
    "Em—dash and en–dash and figure‒dash and horizontal―bar.",
    "Ellipsis… unicode. And ... ascii. And . . . spaced.",
    "Mixed: São Paulo, 12 de março de 2024. A Sra. Silva chegou às 10h.",
    "Contractions: can't won't shouldn't ain't y'all ma'am o'clock.",
    "Hyphen-ated words and under_scores and CamelCase and ALLCAPS.",
    "Trailing quote.' Next one.\" And (parenthetical.) Then end.",
    "Q: What? A: That! B: Which... C: None.",
    "#hashtag @mention $money 50% & more * stars * here.",
    "",
    "   ",
    "No final punctuation",
    "'",
    "''",
    "a 'b' c 'de' f 'ghi' j",
    "He said: 'It's John's book, isn't it?'",
    "'I'm sure,' she said, 'that you're right.'",
]

VOCAB = [
    "the",
    "model",
    "claim",
    "document",
    "evidence",
    "Dr.",
    "Mr.",
    "Mrs.",
    "U.S.",
    "e.g.",
    "i.e.",
    "etc.",
    "vs.",
    "No.",
    "Fig.",
    "Inc.",
    "Ltd.",
    "St.",
    "Jan.",
    "p.m.",
    "3.5",
    "1,200",
    "$4.50",
    "50%",
    "2026",
    "'s",
    "n't",
    "'re",
    "'ll",
    "'d",
    "'m",
    "'ve",
    "it's",
    "don't",
    "'quoted'",
    "'a'",
    "'tis",
    '"x"',
    "``y''",
    "(z)",
    "[w]",
    "{v}",
    "<u>",
    "—",
    "–",
    "…",
    "...",
    ";",
    ":",
    ",",
    "?",
    "!",
    "!?",
    "«",
    "»",
    "“",
    "”",
    "‘",
    "’",
    "São",
    "ação",
    "naïve",
    "café",
    "x-ray",
    "e-mail",
    "a.m.",
    "Ph.D.",
    "U.K.",
    "N.Y.",
    "approx.",
]
ENDINGS = [".", "?", "!", "...", ".'", '."', ".)", "", "\n", ".\n\n"]


def _repository_prose() -> list[str]:
    paths = [ROOT / "README.md", ROOT / "CHANGELOG.md", *sorted((ROOT / "docs").rglob("*.md"))]
    texts: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        texts.append(content)
        texts.extend(part for part in content.split("\n\n") if part.strip())
    return texts


def _synthetic() -> list[str]:
    rng = random.Random(SEED)
    texts = []
    for _ in range(SYNTHETIC_COUNT):
        sentences = []
        for _ in range(rng.randint(1, 6)):
            words = [rng.choice(VOCAB) for _ in range(rng.randint(1, 18))]
            if rng.random() < 0.3:
                words[0] = words[0].capitalize()
            sentences.append(" ".join(words) + rng.choice(ENDINGS))
        texts.append(rng.choice([" ", "  ", "\n", " "]).join(sentences))
    return texts


def corpus(kind: str = "full") -> list[tuple[str, str]]:
    """``full`` adds the repository's prose; ``fixed`` (edge + synthetic) never changes."""
    items = [("edge", text) for text in EDGE_CASES]
    if kind == "full":
        items += [("repository", text) for text in _repository_prose()]
    items += [("synthetic", text) for text in _synthetic()]
    return items


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _tokenizers(implementation: str, data_dir: Path) -> tuple[Any, Any, str]:
    if implementation == "vendored":
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from scripts.benchmarks.phase1b import vendor_nltk

        vendor_nltk.configure(data_dir)
        version = f"vendored-{vendor_nltk.NLTK_VERSION}"
        return vendor_nltk.sent_tokenize, vendor_nltk.word_tokenize, version
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize

    nltk.data.path[:] = [str(data_dir)]
    return sent_tokenize, word_tokenize, nltk.__version__


def run(data_dir: Path, implementation: str = "nltk", kind: str = "full") -> dict[str, Any]:
    sent_tokenize, word_tokenize, version = _tokenizers(implementation, data_dir)
    rows = []
    for index, (source, text) in enumerate(corpus(kind)):
        sentences = sent_tokenize(text)
        rows.append(
            {
                "index": index,
                "source": source,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "sent_tokenize": _digest(sentences),
                "word_tokenize": _digest(word_tokenize(text)),
                # What the FactCG protocol counts: words per sentence.
                "words_per_sentence": _digest([len(word_tokenize(s)) for s in sentences]),
            }
        )
    return {
        "nltk_version": version,
        "corpus": kind,
        "python": sys.version.split()[0],
        "seed": SEED,
        "items": len(rows),
        "by_source": {
            s: sum(1 for r in rows if r["source"] == s) for s in ("edge", "repository", "synthetic")
        },
        "corpus_sha256": _digest([r["text_sha256"] for r in rows]),
        "results_sha256": {
            key: _digest([r[key] for r in rows])
            for key in ("sent_tokenize", "word_tokenize", "words_per_sentence")
        },
        "rows": rows,
    }


def compare(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    if first["corpus_sha256"] != second["corpus_sha256"]:
        raise SystemExit("the two reports were run on different corpora")
    texts = dict(enumerate(text for _, text in corpus(first.get("corpus", "full"))))
    differences: dict[str, list[dict[str, Any]]] = {}
    for key in ("sent_tokenize", "word_tokenize", "words_per_sentence"):
        rows = [
            {"index": a["index"], "source": a["source"], "text": texts[a["index"]][:200]}
            for a, b in zip(first["rows"], second["rows"], strict=True)
            if a[key] != b[key]
        ]
        differences[key] = rows
    return {
        "versions": [first["nltk_version"], second["nltk_version"]],
        "items": first["items"],
        "corpus_sha256": first["corpus_sha256"],
        "equivalent": {key: not rows for key, rows in differences.items()},
        "difference_counts": {key: len(rows) for key, rows in differences.items()},
        "examples": {key: rows[:20] for key, rows in differences.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, type=Path, metavar=("BASELINE", "CANDIDATE"))
    parser.add_argument("--implementation", choices=["nltk", "vendored"], default="nltk")
    parser.add_argument("--corpus", choices=["full", "fixed"], default="full")
    parser.add_argument(
        "--expect",
        type=Path,
        help="fixture with corpus_sha256 and results_sha256; exit 1 unless the run matches",
    )
    args = parser.parse_args()
    if args.compare:
        first, second = (json.loads(p.read_text(encoding="utf-8")) for p in args.compare)
        result = compare(first, second)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        print(text)
        raise SystemExit(0 if all(result["equivalent"].values()) else 1)
    if not args.data_dir or not args.output:
        parser.error("--data-dir and --output are required unless --compare is given")
    report = run(args.data_dir, args.implementation, args.corpus)
    args.output.write_text(json.dumps(report, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {k: v for k, v in report.items() if k != "rows"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.expect:
        expected = json.loads(args.expect.read_text(encoding="utf-8"))
        matches = (
            report["corpus_sha256"] == expected["corpus_sha256"]
            and report["results_sha256"] == expected["results_sha256"]
        )
        print(json.dumps({"matches_reference": matches}))
        raise SystemExit(0 if matches else 1)


if __name__ == "__main__":
    main()
