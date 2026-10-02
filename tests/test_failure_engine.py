import pytest

from ayorai_attractor.failure_engine.core import FailureEngine
from ayorai_attractor.models import FailureType


@pytest.mark.parametrize(
    "failure_type",
    [
        FailureType.TIMEOUT,
        FailureType.RATE_LIMIT,
        FailureType.EMPTY_RESPONSE,
        FailureType.CONTRADICTORY_RESULT,
    ],
)
def test_recoverable_failure_types_record_without_blocking(
    failure_type: FailureType,
) -> None:
    engine = FailureEngine()

    failure = engine.record(failure_type, "temporary provider condition")

    assert failure.type is failure_type
    assert failure.recoverable is True
    assert engine.failures == [failure]
    assert engine.has_blocking_failure() is False


@pytest.mark.parametrize(
    "failure_type",
    [
        FailureType.TIMEOUT,
        FailureType.RATE_LIMIT,
        FailureType.EMPTY_RESPONSE,
        FailureType.CONTRADICTORY_RESULT,
    ],
)
def test_same_failure_type_can_be_promoted_to_blocking(
    failure_type: FailureType,
) -> None:
    engine = FailureEngine()
    engine.record(failure_type, "fatal condition", recoverable=False)

    assert engine.has_blocking_failure() is True


def test_blocking_failure_is_sticky_until_a_new_engine_is_created() -> None:
    engine = FailureEngine()
    engine.record(FailureType.TIMEOUT, "fatal timeout", recoverable=False)
    engine.record(FailureType.RATE_LIMIT, "recoverable rate limit", recoverable=True)

    assert engine.has_blocking_failure() is True
    assert [item.type for item in engine.failures] == [
        FailureType.TIMEOUT,
        FailureType.RATE_LIMIT,
    ]
