from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from ayorai_attractor.evaluation.stats import (
    VERDICT_ORDER,
    balanced_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


@settings(max_examples=100, deadline=None)
@given(
    rows=st.lists(
        st.tuples(st.sampled_from(VERDICT_ORDER), st.sampled_from(VERDICT_ORDER)),
        min_size=1,
        max_size=40,
    )
)
def test_confusion_matrix_always_conserves_generated_rows(
    rows: list[tuple[str, str]],
) -> None:
    expected = [gold for gold, _ in rows]
    predicted = [guess for _, guess in rows]
    matrix = confusion_matrix(expected, predicted)
    assert sum(sum(row.values()) for row in matrix.values()) == len(rows)
    assert sum(matrix[label][label] for label in VERDICT_ORDER) == sum(
        gold == guess for gold, guess in rows
    )


@settings(max_examples=100, deadline=None)
@given(
    rows=st.lists(
        st.tuples(st.sampled_from(VERDICT_ORDER), st.sampled_from(VERDICT_ORDER)),
        min_size=1,
        max_size=40,
    )
)
def test_balanced_accuracy_stays_within_probability_bounds(
    rows: list[tuple[str, str]],
) -> None:
    expected = [gold for gold, _ in rows]
    predicted = [guess for _, guess in rows]
    score = balanced_accuracy(expected, predicted)
    assert 0.0 <= score <= 1.0


@settings(max_examples=100, deadline=None)
@given(
    rows=st.lists(
        st.tuples(
            st.sampled_from(VERDICT_ORDER),
            st.sampled_from(VERDICT_ORDER),
            st.sampled_from(VERDICT_ORDER),
        ),
        min_size=0,
        max_size=40,
    )
)
def test_mcnemar_is_bounded_and_symmetric_for_generated_predictions(
    rows: list[tuple[str, str, str]],
) -> None:
    gold = [item[0] for item in rows]
    predicted_a = [item[1] for item in rows]
    predicted_b = [item[2] for item in rows]
    p_ab = mcnemar_exact_pvalue(gold, predicted_a, predicted_b)
    p_ba = mcnemar_exact_pvalue(gold, predicted_b, predicted_a)
    assert 0.0 <= p_ab <= 1.0
    assert p_ab == p_ba
