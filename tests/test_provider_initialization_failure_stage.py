from ayorai_attractor.models import SearchRequest
from ayorai_attractor.orchestrator import Attractor


def test_provider_initialization_failure_keeps_stage_none_and_message(monkeypatch) -> None:
    message = "synthetic provider initialization failure"

    def fail_provider():
        raise RuntimeError(message)

    monkeypatch.setattr(
        "ayorai_attractor.orchestrator.build_default_provider",
        fail_provider,
    )

    response = Attractor().run(SearchRequest(query="synthetic query"))

    assert response.operation_status == "failed"
    assert len(response.failures) == 1
    assert response.failures[0].stage is None
    assert response.failures[0].message == message
