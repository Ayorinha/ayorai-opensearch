import json
from pathlib import Path

import typer

from ayorai_attractor.evaluation.golden import evaluate_golden_v0
from ayorai_attractor.models import QualityMode, SearchRequest
from ayorai_attractor.orchestrator import Attractor

app = typer.Typer(help="AYORAI ATTRACTOR OpenSearch CLI.")
engine = Attractor()


@app.command()
def search(
    query: str,
    mode: QualityMode = QualityMode.BALANCED,
    max_agents: int = 5,
) -> None:
    """Run an evidence-first multi-agent search task."""
    result = engine.run(
        SearchRequest(query=query, mode=mode, max_agents=max_agents)
    )
    typer.echo(
        json.dumps(
            result.model_dump(mode="json"),
            indent=2,
            ensure_ascii=False,
        )
    )


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
    golden_path = Path("evals/golden/v0.1.jsonl" if suite == "golden-v0.1" else "evals/golden/v0.jsonl")
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
    typer.echo(json.dumps({
        "suite": suite,
        "out": str(out),
        "global_accuracy": report["global_accuracy"],
        "majority_class_baseline": report["majority_class_baseline"],
    }, ensure_ascii=False))
