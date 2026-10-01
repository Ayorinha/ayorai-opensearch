import pytest

from ayorai_attractor.durable import WorkflowState


def test_checkpoint_round_trip() -> None:
    state = WorkflowState("wf-1", 2, ("plan", "research"))
    assert WorkflowState.resume(state.checkpoint()) == state


def test_checkpoint_rejects_missing_fields() -> None:
    with pytest.raises(ValueError):
        WorkflowState.resume({"workflow_id": "wf-1"})
