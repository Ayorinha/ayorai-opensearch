"""P1 authorization preflight must precede encrypted cache access."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts.benchmarks.phase1b import e3_confirm, score_cache


def test_p1_preflight_runs_before_cache_decryption(
    monkeypatch, tmp_path: Path
) -> None:
    events: list[str] = []
    cache_path = tmp_path / "encrypted-cache.json"
    cache_path.write_text(json.dumps({"ciphertext": "synthetic"}), encoding="utf-8")
    output_path = tmp_path / "report.json"

    monkeypatch.setattr(
        e3_confirm, "preflight_confirm", lambda: events.append("preflight")
    )
    monkeypatch.setattr(
        score_cache, "decode_key", lambda: events.append("decode-key") or b"key"
    )
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
    monkeypatch.setattr(
        e3_confirm, "preflight_confirm", lambda: events.append("preflight")
    )

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

    import pytest

    with pytest.raises(RuntimeError, match="DEC-026 authorization"):
        score_cache.main()
