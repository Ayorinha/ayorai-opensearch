import json
from pathlib import Path

import typer
from pydantic import ValidationError

from ayorai_attractor.evaluation.golden import evaluate_golden_v0
from ayorai_attractor.models import QualityMode, SearchRequest
from ayorai_attractor.orchestrator import Attractor

app = typer.Typer(help="AYORAI ATTRACTOR OpenSearch CLI.")
engine = Attractor()

# Exit codes of ``search``. A completed run exits 0 whether or not a verdict was
# adjudicated: ``verdict_authority: not_adjudicated`` describes the result, it is
# not an execution error.
EXIT_OK = 0
EXIT_OPERATION_FAILED = 1  # operation_status == "failed" (e.g. provider unavailable)
EXIT_INVALID_INPUT = 2  # the request did not validate; same code Click uses for usage errors


@app.command()
def search(
    query: str,
    mode: QualityMode = QualityMode.BALANCED,
    max_agents: int = 5,
) -> None:
    """Run the configured search/provider pipeline and return its structured result.

    Exit status: 0 when the operation completed (including results that were not
    adjudicated), 1 when ``operation_status`` is ``failed``, 2 for invalid input.
    """
    try:
        request = SearchRequest(query=query, mode=mode, max_agents=max_agents)
    except ValidationError as exc:
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"]) or "request"
            typer.echo(f"invalid {field}: {error['msg']}", err=True)
        raise typer.Exit(EXIT_INVALID_INPUT) from exc
    result = engine.run(request)
    typer.echo(
        json.dumps(
            result.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
    )
    if result.operation_status == "failed":
        raise typer.Exit(EXIT_OPERATION_FAILED)


@app.command(name="eval")
def eval_suite(
    suite: str = typer.Option("golden-v0", "--suite"),
    out: Path = typer.Option(  # noqa: B008
        Path("reports/eval-golden-v0.json"), "--out"
    ),
) -> None:
    """Run a deterministic evaluation suite."""
    if suite not in {"golden-v0", "golden-v0.1", "smoke-v0"}:
        raise typer.BadParameter("Only golden-v0, golden-v0.1 and smoke-v0 are implemented.")
    golden_path = Path(
        "evals/golden/v0.1.jsonl" if suite == "golden-v0.1" else "evals/golden/v0.jsonl"
    )
    report = evaluate_golden_v0(
        golden_path,
        Path("evals/corpus/documents.jsonl"),
        suite=suite,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    typer.echo(
        json.dumps(
            {
                "suite": suite,
                "out": str(out),
                "global_accuracy": report["global_accuracy"],
                "majority_class_baseline": report["majority_class_baseline"],
            },
            ensure_ascii=False,
        )
    )


def opensearch_entrypoint() -> None:
    """Console script ``opensearch``: the ``search`` command on its own."""
    typer.run(search)


if __name__ == "__main__":
    app()
