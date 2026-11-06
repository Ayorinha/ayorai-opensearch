"""CLI for local international benchmark evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from ayorai_attractor.evaluation.international import evaluate


def main() -> None:
    """Parse arguments and run the component evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate a local LLM-AggreFact file")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    parser.add_argument(
        "--code-sha",
        required=True,
        help="Code revision SHA supplied by caller (e.g. GitHub Actions)",
    )
    args = parser.parse_args()
    evaluate(
        args.dataset,
        args.mapping,
        args.out_json,
        args.out_md,
        code_sha=args.code_sha,
    )


if __name__ == "__main__":
    main()
