import json

import typer

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
