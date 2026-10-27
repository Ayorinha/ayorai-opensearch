"""Tests for scripts/normalize_sdist.py (deterministic sdist repack)."""

from __future__ import annotations

import gzip
import importlib.util
import io
import sys
import tarfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
EPOCH = 1_700_000_000


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "normalize_sdist", ROOT / "scripts/normalize_sdist.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ns = _load()


def _make_tar(
    files: list[tuple[str, bytes, int]],
    *,
    mtime: int,
    owner: str = "runner",
    gz_mtime: int | None = None,
    extra: list[tarfile.TarInfo] | None = None,
    reverse: bool = False,
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as out:
        root = tarfile.TarInfo("pkg-1.0")
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = mtime
        root.uid = 123
        root.gid = 456
        root.uname = owner
        root.gname = owner
        out.addfile(root)
        for name, payload, mode in reversed(files) if reverse else files:
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = mode
            info.mtime = mtime
            info.uid = 1001
            info.gid = 2002
            info.uname = owner
            info.gname = owner
            out.addfile(info, io.BytesIO(payload))
        for info in extra or []:
            out.addfile(info)
    gz = io.BytesIO()
    with gzip.GzipFile(
        filename="pkg-1.0.tar", mode="wb", fileobj=gz, mtime=gz_mtime or mtime
    ) as handle:
        handle.write(buffer.getvalue())
    return gz.getvalue()


FILES = [
    ("pkg-1.0/PKG-INFO", b"Name: pkg\n", 0o644),
    ("pkg-1.0/run.sh", b"#!/bin/sh\necho ok\n", 0o755),
    ("pkg-1.0/src/pkg/__init__.py", b"VALUE = 1\n", 0o644),
    ("pkg-1.0/private.txt", b"private\n", 0o600),
    ("pkg-1.0/tool.sh", b"#!/bin/sh\n", 0o711),
]


def _members(data: bytes) -> dict[str, tuple[int, int, int, int, str, str, bytes | None]]:
    result: dict[str, tuple[int, int, int, int, str, str, bytes | None]] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            handle = archive.extractfile(member) if member.isfile() else None
            result[member.name] = (
                member.mode,
                int(member.mtime),
                member.uid,
                member.gid,
                member.uname,
                member.gname,
                handle.read() if handle else None,
            )
    return result


def test_same_content_different_metadata_gives_identical_bytes() -> None:
    first = _make_tar(FILES, mtime=1_790_000_000, owner="alice")
    second = _make_tar(FILES, mtime=1_790_000_555, owner="bob", gz_mtime=1, reverse=True)
    assert first != second
    assert ns.normalize_bytes(first, EPOCH) == ns.normalize_bytes(second, EPOCH)


def test_same_input_produces_identical_bytes_on_two_runs() -> None:
    source = _make_tar(FILES, mtime=1_790_000_000, owner="alice")
    assert ns.normalize_bytes(source, EPOCH) == ns.normalize_bytes(source, EPOCH)


def test_idempotent() -> None:
    once = ns.normalize_bytes(_make_tar(FILES, mtime=1_790_000_000), EPOCH)
    assert ns.normalize_bytes(once, EPOCH) == once


def test_content_modes_and_all_metadata_normalized() -> None:
    normalized = ns.normalize_bytes(_make_tar(FILES, mtime=1_790_000_000), EPOCH)
    members = _members(normalized)
    for name, payload, original_mode in FILES:
        got_mode, got_mtime, got_uid, got_gid, got_uname, got_gname, got_payload = members[name]
        assert got_payload == payload
        assert got_mode == (0o755 if original_mode & 0o111 else 0o644)
        assert (got_mtime, got_uid, got_gid, got_uname, got_gname) == (
            EPOCH,
            0,
            0,
            "",
            "",
        )
    assert list(members) == sorted(members)
    header = gzip.GzipFile(fileobj=io.BytesIO(normalized))
    header.read()
    assert header.mtime == EPOCH


def test_epoch_changes_output() -> None:
    data = _make_tar(FILES, mtime=1_790_000_000)
    assert ns.normalize_bytes(data, EPOCH) != ns.normalize_bytes(data, EPOCH + 1)


def _link(name: str, target: str, *, symbolic: bool = True) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE if symbolic else tarfile.LNKTYPE
    info.linkname = target
    return info


@pytest.mark.parametrize(
    ("files", "extra"),
    [
        ([("../evil.py", b"x", 0o644)], None),
        ([("/abs/evil.py", b"x", 0o644)], None),
        ([("C:/Windows/evil.py", b"x", 0o644)], None),
        ([("pkg-1.0/C:/Windows/evil.py", b"x", 0o644)], None),
        ([("pkg-1.0/a/../../evil.py", b"x", 0o644)], None),
        ([("outside-root/evil.py", b"x", 0o644)], None),
        ([("pkg-1.0/dup.py", b"1", 0o644), ("pkg-1.0/dup.py", b"2", 0o644)], None),
        ([], [_link("pkg-1.0/escape", "../../etc/passwd")]),
        ([], [_link("pkg-1.0/abs", "/etc/passwd")]),
        ([], [_link("pkg-1.0/windows", "C:/Windows/system.ini")]),
        ([], [_link("pkg-1.0/hard", "../outside", symbolic=False)]),
    ],
)
def test_rejects_unsafe_entries(
    files: list[tuple[str, bytes, int]], extra: list[tarfile.TarInfo] | None
) -> None:
    with pytest.raises(ns.NormalizationError):
        ns.normalize_bytes(_make_tar(files, mtime=1, extra=extra), EPOCH)


def test_rejects_device_and_fifo() -> None:
    device = tarfile.TarInfo("pkg-1.0/device")
    device.type = tarfile.CHRTYPE
    fifo = tarfile.TarInfo("pkg-1.0/pipe")
    fifo.type = tarfile.FIFOTYPE
    for special in (device, fifo):
        with pytest.raises(ns.NormalizationError):
            ns.normalize_bytes(_make_tar(FILES, mtime=1, extra=[special]), EPOCH)


def test_internal_symlink_allowed() -> None:
    normalized = ns.normalize_bytes(
        _make_tar(FILES, mtime=1, extra=[_link("pkg-1.0/alias.py", "src/pkg/__init__.py")]),
        EPOCH,
    )
    with tarfile.open(fileobj=io.BytesIO(normalized), mode="r:gz") as archive:
        assert archive.getmember("pkg-1.0/alias.py").linkname == "src/pkg/__init__.py"


def test_internal_hardlink_allowed() -> None:
    normalized = ns.normalize_bytes(
        _make_tar(
            FILES,
            mtime=1,
            extra=[_link("pkg-1.0/hard-alias", "pkg-1.0/PKG-INFO", symbolic=False)],
        ),
        EPOCH,
    )
    with tarfile.open(fileobj=io.BytesIO(normalized), mode="r:gz") as archive:
        assert archive.getmember("pkg-1.0/hard-alias").linkname == "pkg-1.0/PKG-INFO"


def test_rejects_non_archive() -> None:
    with pytest.raises(ns.NormalizationError):
        ns.normalize_bytes(b"not a tarball", EPOCH)


@pytest.mark.parametrize("value", [None, "", "abc", "-5", "1.5"])
def test_source_date_epoch_validation(value: str | None) -> None:
    env = {} if value is None else {"SOURCE_DATE_EPOCH": value}
    with pytest.raises(ns.NormalizationError):
        ns.source_date_epoch(env)
    assert ns.source_date_epoch({"SOURCE_DATE_EPOCH": "42"}) == 42


def test_cli_streams_source_without_path_read_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "pkg-1.0.tar.gz"
    source.write_bytes(_make_tar(FILES, mtime=1_790_000_000))
    expected = ns.normalize_bytes(source.open("rb").read(), EPOCH)
    target = tmp_path / "out.tar.gz"
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(EPOCH))

    def forbidden_read_bytes(self: Path) -> bytes:
        raise AssertionError("CLI must stream source rather than call Path.read_bytes")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    assert ns.main([str(source), str(target)]) == 0
    with target.open("rb") as normalized:
        assert normalized.read() == expected
    assert ns.main([str(source)]) == 2
