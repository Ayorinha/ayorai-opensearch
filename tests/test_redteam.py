from ayorai_attractor.redteam import (
    RED_TEAM_CASES,
    ThreatClass,
    evaluate_red_team_case,
)


def test_red_team_corpus_is_non_empty_and_unique() -> None:
    ids = [case.case_id for case in RED_TEAM_CASES]
    assert ids
    assert len(ids) == len(set(ids))


def test_red_team_covers_core_threat_classes() -> None:
    threats = {case.threat for case in RED_TEAM_CASES}
    assert threats == {
        ThreatClass.PROMPT_INJECTION,
        ThreatClass.EVIDENCE_POISONING,
        ThreatClass.CITATION_MANIPULATION,
        ThreatClass.SECRET_EXPOSURE,
    }


def test_every_case_has_an_explicit_safe_action() -> None:
    assert all(evaluate_red_team_case(case) for case in RED_TEAM_CASES)
