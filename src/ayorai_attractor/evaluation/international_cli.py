"""Command-line entrypoint for the local international benchmark."""
import argparse
from pathlib import Path
from ayorai_attractor.evaluation.international import evaluate

def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a local LLM-AggreFact file")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    args = parser.parse_args()
    evaluate(args.dataset, args.mapping, args.out_json, args.out_md)

if __name__ == "__main__":
    main()
