from ayorai_attractor.models import Failure, FailureStage, FailureType


class FailureEngine:
    def __init__(self) -> None:
        self.failures: list[Failure] = []

    def record(
        self,
        failure_type: FailureType,
        message: str,
        recoverable: bool = True,
        *,
        stage: FailureStage | None = None,
    ) -> Failure:
        if stage is not None:
            message = f"[stage:{stage.value}] {message}"
        failure = Failure(
            type=failure_type,
            message=message,
            recoverable=recoverable,
        )
        self.failures.append(failure)
        return failure

    def has_blocking_failure(self) -> bool:
        return any(not failure.recoverable for failure in self.failures)
