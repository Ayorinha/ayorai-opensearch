from ayorai_attractor.replay import ReplayBundle


def test_replay_bundle_is_content_addressed() -> None:
    bundle = ReplayBundle.build(
        "tr_1",
        [{"step": "judge", "decision": "verified"}],
    )
    assert bundle.verify()
    assert len(bundle.digest) == 64


def test_replay_digest_changes_when_event_changes() -> None:
    first = ReplayBundle.build("tr_1", [{"step": "judge", "decision": "verified"}])
    second = ReplayBundle.build("tr_1", [{"step": "judge", "decision": "supported"}])
    assert first.digest != second.digest
