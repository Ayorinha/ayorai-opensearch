"""Minimal durable orchestration state for R9.

The state is JSON-serializable and can be checkpointed after every step.
Recovery never advances the workflow implicitly.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowState:
    workflow_id: str
    step: int
    completed: tuple[str, ...]
    status: str = "running"

    def checkpoint(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "step": self.step,
            "completed": list(self.completed),
            "status": self.status,
        }

    @classmethod
    def resume(cls, payload: dict[str, object]) -> "WorkflowState":
        required = {"workflow_id", "step", "completed", "status"}
        if set(payload) != required:
            raise ValueError("invalid workflow checkpoint")
        workflow_id = payload["workflow_id"]
        step = payload["step"]
        completed = payload["completed"]
        status = payload["status"]
        if not isinstance(workflow_id, str) or not isinstance(step, int):
            raise ValueError("invalid workflow checkpoint types")
        if not isinstance(completed, list) or not all(
            isinstance(item, str) for item in completed
        ):
            raise ValueError("invalid completed-step list")
        if not isinstance(status, str):
            raise ValueError("invalid workflow status")
        return cls(workflow_id, step, tuple(completed), status)
