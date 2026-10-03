from pathlib import Path

import pytest

from ayorai_attractor.evaluation import golden


def _repo(tmp_path: Path) -> Path:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    return git_dir


def test_prefers_github_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    assert golden._git_sha() == "a" * 40


def test_resolves_loose_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    git_dir = _repo(tmp_path)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "refs" / "heads" / "main").write_text("b" * 40 + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert golden._git_sha() == "b" * 40


def test_resolves_packed_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    git_dir = _repo(tmp_path)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(
        "# pack-refs with: peeled\n" + "c" * 40 + " refs/heads/main\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    assert golden._git_sha() == "c" * 40


def test_detached_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    git_dir = _repo(tmp_path)
    (git_dir / "HEAD").write_text("d" * 40 + "\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert golden._git_sha() == "d" * 40


def test_unknown_without_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.chdir(tmp_path)
    assert golden._git_sha() == "unknown"
