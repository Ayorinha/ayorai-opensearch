from ayorai_attractor.evaluation.stats import (
    bootstrap_accuracy,
    confusion_matrix,
    mcnemar_exact_pvalue,
)


def test_confusion_matrix_has_fixed_six_by_six_shape() -> None:
    matrix = confusion_matrix(
        ["VERIFIED", "SUPPORTED", "REFUTED"],
        ["VERIFIED", "REFUTED", "REFUTED"],
    )
    assert list(matrix) == [
        "VERIFIED",
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNVERIFIED",
        "REFUTED",
        "CONFLICTING",
    ]
    assert all(list(row) == list(matrix) for row in matrix.values())
    assert matrix["VERIFIED"]["VERIFIED"] == 1
    assert matrix["SUPPORTED"]["REFUTED"] == 1


def test_bootstrap_accuracy_is_reproducible() -> None:
    data = ["VERIFIED", "SUPPORTED", "REFUTED", "UNVERIFIED"]
    result_a = bootstrap_accuracy(data, data, iterations=1000, seed=7)
    result_b = bootstrap_accuracy(data, data, iterations=1000, seed=7)
    assert result_a == result_b == (1.0, 1.0)


def test_mcnemar_is_one_when_predictions_are_identical() -> None:
    data = ["VERIFIED", "SUPPORTED", "REFUTED"]
    assert mcnemar_exact_pvalue(data, data, data) == 1.0


def test_mcnemar_detects_maximally_discordant_pair() -> None:
    expected = ["VERIFIED"] * 10
    first = ["VERIFIED"] * 5 + ["SUPPORTED"] * 5
    second = ["SUPPORTED"] * 10
    assert mcnemar_exact_pvalue(expected, first, second) < 0.1
