# Local Evaluation Workflow

## Install

Create an isolated environment and install the development dependencies:

    python -m venv .venv
    pip install -e ".[dev]"

## Frozen Golden v0

Run the complete 34-case suite:

    mkdir -p reports
    attractor eval --suite golden-v0 --out reports/golden-v0.json

The local report should contain 34 cases and 52 corpus documents. The frozen manifest in evals/golden/MANIFEST.json must remain unchanged for a v0 comparison.

Validate the closed-world fixture before running the suite:

    python scripts/lint_golden.py

## Deterministic Judge suite

Run the explicit six-verdict Judge regression suite:

    python -c 'from pathlib import Path; from ayorai_attractor.evaluation.judge import evaluate_judge_suite; print(evaluate_judge_suite(Path("evals/judge/v0.jsonl")))'

This evaluates Claim → Evidence → Stance → deterministic Judge. The expected verdict is compared only after the Judge returns its prediction.

## Full local gate

Run the same core checks used by CI:

    ruff check .
    mypy src/ayorai_attractor
    pytest --cov=ayorai_attractor --cov-report=term-missing

The CI matrix also executes Python 3.11, 3.12 and 3.13 plus namespace compatibility, Golden v0 regression, Security and CodeQL.

## Interpreting results

Do not compare a local result with the historical 43.3333% baseline unless the exact frozen v0 suite and manifest are used.

For reproducibility, record:

- commit SHA;
- suite name and version;
- corpus manifest SHA-256;
- Python version;
- generated report path.

Golden v0 is synthetic and closed-world. Passing it does not establish real-web factual accuracy or generalization.
