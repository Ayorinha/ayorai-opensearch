import pytest

from ayorai_attractor.replay import ReplayBundle
from ayorai_attractor.replay_store import ReplayStore


def test_replay_store_round_trip_and_deduplication(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))
    bundle = ReplayBundle.build(
        "tr_replay",
        [{"event": "verified", "value": "ok"}],
    )

    assert store.put(bundle) == bundle.digest
    assert store.put(bundle) == bundle.digest

    loaded = store.get(bundle.digest)
    assert loaded == bundle
    assert loaded is not None
    assert loaded.verify()


def test_replay_store_returns_none_for_unknown_digest(tmp_path) -> None:
    assert ReplayStore(str(tmp_path)).get("0" * 64) is None


def test_replay_store_rejects_invalid_digest(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))

    with pytest.raises(ValueError):
        store.get("../outside")

    with pytest.raises(ValueError):
        store.get("ABC")


def test_replay_store_rejects_digest_mismatch(tmp_path) -> None:
    store = ReplayStore(str(tmp_path))
    bundle = ReplayBundle.build(
        "tr_replay",
        [{"event": "verified", "value": "ok"}],
    )
    store.put(bundle)

    source = tmp_path / f"{bundle.digest}.json"
    target = tmp_path / f"{'f' * 64}.json"
    target.write_bytes(source.read_bytes())

    with pytest.raises(ValueError, match="mismatch"):
        store.get("f" * 64)
