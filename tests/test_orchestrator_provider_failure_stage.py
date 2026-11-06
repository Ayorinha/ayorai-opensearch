from __future__ import annotations

from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor


def test_provider_initialization_failure_has_no_retrieval_stage(
    monkeypatch,
) -> None:
    def fail_provider_initialization() -> None:
        raise RuntimeError("synthetic provider initialization failure")

    monkeypatch.setattr(
        "ayorai_attractor.orchestrator.build_default_provider",
        fail_provider_initialization,
    )

    response = Attractor().run(SearchRequest(query="synthetic provider failure"))

    assert len(response.failures) == 1
    failure = response.failures[0]
    assert failure.stage is None
    assert failure.message == "synthetic provider initialization failure"
