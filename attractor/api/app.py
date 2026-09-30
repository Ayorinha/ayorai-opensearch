from fastapi import FastAPI

from attractor.models import SearchRequest, SearchResponse
from attractor.orchestrator import Attractor

app = FastAPI(
    title="AYORAI ATTRACTOR",
    version="0.1.0",
    description="Adaptive multi-agent intelligence and verification engine.",
)
engine = Attractor()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ayorai-attractor"}


@app.post("/v1/opensearch", response_model=SearchResponse)
def opensearch(request: SearchRequest) -> SearchResponse:
    return engine.run(request)
