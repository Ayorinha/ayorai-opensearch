from __future__ import annotations

import pytest

from ayorai_attractor.verification.security import (
    assert_no_secret,
    contains_secret,
)


@pytest.mark.parametrize(
    "container",
    [
        ["antes", "token-secreto", "depois"],
        ("antes", {"campo": "token-secreto"}),
        {"token-secreto", "valor-publico"},
        frozenset({"valor-publico", "token-secreto"}),
        {"token-secreto": "valor-publico"},
        {"evidence": {"excerpt": "O documento contém token-secreto."}},
        {"report": [{"message": "Falha: token-secreto"}]},
    ],
)
def test_contains_secret_finds_exact_secret_recursively(container: object) -> None:
    assert contains_secret(container, "token-secreto")


@pytest.mark.parametrize(
    "value",
    [
        "O documento foi conferido.",
        {"evidence": {"excerpt": "A dívida foi quitada."}},
        {"report": [{"status": "abstain/no_answer"}]},
        42,
        None,
        False,
        ["texto público", 7, None],
    ],
)
def test_contains_secret_avoids_false_positives(value: object) -> None:
    assert not contains_secret(value, "token-secreto")


def test_contains_secret_checks_dictionary_keys_and_values() -> None:
    assert contains_secret({"token-secreto": "valor público"}, "token-secreto")
    assert contains_secret({"campo": "token-secreto"}, "token-secreto")


def test_secret_detection_handles_portuguese_evidence_and_report_fields() -> None:
    response = {
        "verdict": "UNVERIFIED",
        "evidence": [
            {
                "source": "documento de teste",
                "excerpt": "A senha temporária é token-secreto.",
            }
        ],
        "report": {
            "resumo": "A evidência contém token-secreto e deve ser bloqueada.",
        },
    }
    assert contains_secret(response, "token-secreto")
    with pytest.raises(ValueError, match="response contains an evaluation secret"):
        assert_no_secret(response, "token-secreto")


def test_assert_no_secret_accepts_response_without_secret() -> None:
    assert_no_secret(
        {"verdict": "SUPPORTED", "evidence": [{"excerpt": "A receita foi publicada."}]},
        "token-secreto",
    )


def test_assert_no_secret_rejects_secret_in_nested_response() -> None:
    with pytest.raises(ValueError, match="response contains an evaluation secret"):
        assert_no_secret(
            {"report": {"details": ["ok", {"secret": "token-secreto"}]}},
            "token-secreto",
        )
