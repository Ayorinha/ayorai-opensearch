"""P1 authorization preflight must precede encrypted cache access."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts.benchmarks.phase1b import e3_confirm, score_cache


def test_p1_preflight_runs_before_cache_decryption(monkeypatch, tmp_path: Path) -> None:
    events: list[str] = []
    cache_path = tmp_path / "encrypted-cache.json"
    cache_path.write_text(json.dumps({"ciphertext": "synthetic"}), encoding="utf-8")
    output_path = tmp_path / "report.json"

    monkeypatch.setattr(e3_confirm, "preflight_confirm", lambda: events.append("preflight"))
    monkeypatch.setattr(score_cache, "decode_key", lambda: events.append("decode-key") or b"key")
    monkeypatch.setattr(
        score_cache,
        "decrypt_score_cache",
        lambda envelope, key: events.append("decrypt") or {"synthetic": True},
    )
    monkeypatch.setitem(
        score_cache.EXPERIMENTS,
        "e3-confirm-dev-b",
        lambda cache: events.append("experiment") or {"record_count": 0},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score_cache.py",
            "--experiment",
            "e3-confirm-dev-b",
            "--cache",
            str(cache_path),
            "--output",
            str(output_path),
        ],
    )

    score_cache.main()

    assert events == ["preflight", "decode-key", "decrypt", "experiment"]
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"record_count": 0}


def test_p1_preflight_only_never_reads_or_decrypts_cache(monkeypatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(e3_confirm, "preflight_confirm", lambda: events.append("preflight"))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("preflight-only must not access cache material")

    monkeypatch.setattr(score_cache, "decode_key", forbidden)
    monkeypatch.setattr(score_cache, "decrypt_score_cache", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        ["score_cache.py", "--experiment", "e3-confirm-dev-b", "--preflight-only"],
    )

    score_cache.main()

    assert events == ["preflight"]


def test_p1_preflight_failure_stops_before_key_or_cache_access(monkeypatch) -> None:
    def reject() -> None:
        raise RuntimeError("DEC-026 authorization is missing")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cache access must not follow a failed P1 preflight")

    monkeypatch.setattr(e3_confirm, "preflight_confirm", reject)
    monkeypatch.setattr(score_cache, "decode_key", forbidden)
    monkeypatch.setattr(score_cache, "decrypt_score_cache", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score_cache.py",
            "--experiment",
            "e3-confirm-dev-b",
            "--cache",
            "/nonexistent/cache.json",
            "--output",
            "/nonexistent/report.json",
        ],
    )

    with pytest.raises(RuntimeError, match="DEC-026 authorization"):
        score_cache.main()


def test_reserve_lock_hashes_envelope_and_never_decrypts(monkeypatch, tmp_path: Path) -> None:
    import hashlib

    cache_path = tmp_path / "encrypted-cache.json"
    cache_path.write_bytes(b'{"ciphertext": "synthetic"}')
    reservation = tmp_path / "reservation.json"
    seen: dict[str, object] = {}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("the reserve step must never read the key or decrypt")

    def fake_reserve(path: Path, envelope_sha256: str) -> dict[str, str]:
        seen.update(path=path, envelope=envelope_sha256)
        return {"ref": "refs/heads/p1-dev-b-confirmation-lock", "sha": "a" * 40, "run_id": "1"}

    monkeypatch.setattr(e3_confirm, "preflight_confirm", lambda: None)
    monkeypatch.setattr(e3_confirm, "reserve_lock", fake_reserve)
    monkeypatch.setattr(score_cache, "decode_key", forbidden)
    monkeypatch.setattr(score_cache, "decrypt_score_cache", forbidden)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score_cache.py",
            "--experiment",
            "e3-confirm-dev-b",
            "--cache",
            str(cache_path),
            "--reserve-lock",
            str(reservation),
        ],
    )
    score_cache.main()
    assert seen == {
        "path": reservation,
        "envelope": hashlib.sha256(cache_path.read_bytes()).hexdigest(),
    }


def test_validate_cache_only_writes_nothing_and_computes_no_outcome(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    cache_path = tmp_path / "encrypted-cache.json"
    cache_path.write_text(json.dumps({"ciphertext": "synthetic"}), encoding="utf-8")
    events: list[str] = []
    monkeypatch.setattr(e3_confirm, "preflight_confirm", lambda: None)
    monkeypatch.setattr(score_cache, "decode_key", lambda: b"key")
    monkeypatch.setattr(score_cache, "decrypt_score_cache", lambda envelope, key: {"x": 1})
    monkeypatch.setattr(
        e3_confirm,
        "validate_cache",
        lambda cache: events.append("validate") or {"cache_preflight": "passed"},
    )
    monkeypatch.setitem(
        score_cache.EXPERIMENTS,
        "e3-confirm-dev-b",
        lambda cache: pytest.fail("validation must not run the experiment"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score_cache.py",
            "--experiment",
            "e3-confirm-dev-b",
            "--cache",
            str(cache_path),
            "--validate-cache-only",
        ],
    )
    score_cache.main()
    assert events == ["validate"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["encrypted-cache.json"]
    assert json.loads(capsys.readouterr().out)["cache_preflight"] == "passed"


@pytest.mark.parametrize("flag", ["--validate-cache-only", "--preflight-only"])
def test_p1_modes_are_rejected_for_other_experiments(monkeypatch, flag: str) -> None:
    monkeypatch.setattr(
        sys, "argv", ["score_cache.py", "--experiment", "replay-calibration-v2", flag]
    )
    with pytest.raises(SystemExit):
        score_cache.main()
