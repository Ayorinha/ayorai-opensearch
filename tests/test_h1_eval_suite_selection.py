from __future__ import annotations

import pytest

from ayorai_attractor.evaluation.h1_suites import (
    GOLDEN_SUITES,
    select_golden_suites,
)


def test_both_selection_preserves_comparative_default() -> None:
    assert select_golden_suites("both") == GOLDEN_SUITES
    assert GOLDEN_SUITES == ("golden-v0", "golden-v0.1")


@pytest.mark.parametrize("suite", GOLDEN_SUITES)
def test_single_suite_selection_runs_only_requested_suite(suite: str) -> None:
    assert select_golden_suites(suite) == (suite,)


def test_unknown_suite_selection_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported Golden suite"):
        select_golden_suites("golden-v9")
