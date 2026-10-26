"""Deterministically repack a source distribution (sdist) archive.

The setuptools sdist embeds the checkout file mtimes and the gzip header mtime, so two
builds of the same commit differ in bytes even when the content is identical. This
script rewrites only non-semantic packaging metadata:

- entries sorted by name, PAX format, no extra PAX headers;
- mtime set to ``SOURCE_DATE_EPOCH``; uid/gid 0; empty user and group names;
- gzip header with ``mtime=SOURCE_DATE_EPOCH`` and an empty file name.

Names, file contents, directory structure and permission modes are preserved. The
archive is read in memory and never extracted to disk. Unsafe entries (absolute
paths, ``..`` components, duplicates, links leaving the archive root, devices and
FIFOs) are rejected.

Usage: SOURCE_DATE_EPOCH=<int> python scripts/normalize_sdist.py <input.tar.gz> <output.tar.gz>
"""

from __future__ import annotations

import gzip
import io
import os
import posixpath
import sys
import tarfile
from pathlib import Path


class NormalizationError(ValueError):
    """Raised when the input archive or environment is not acceptable."""


def source_date_epoch(environ: dict[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    raw = env.get("SOURCE_DATE_EPOCH", "").strip()
    if not raw:
        raise NormalizationError("SOURCE_DATE_EPOCH is not set")
    if not raw.isdigit():
        raise NormalizationError(f"SOURCE_DATE_EPOCH must be a non-negative integer: {raw!r}")
    return int(raw)


def _check_name(name: str) -> None:
    if not name or name.startswith("/") or "\\" in name:
        raise NormalizationError(f"unsafe entry name: {name!r}")
    parts = name.rstrip("/").split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise NormalizationError(f"unsafe entry name: {name!r}")


def _check_link(member: tarfile.TarInfo) -> None:
    target = member.linkname
    if not target or target.startswith("/"):
        raise NormalizationError(f"unsafe link target in {member.name!r}: {target!r}")
    if member.issym():
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(member.name), target))
    else:
        resolved = posixpath.normpath(target)
    if resolved == ".." or resolved.startswith("../") or resolved.startswith("/"):
        raise NormalizationError(f"link leaves the archive root: {member.name!r} -> {target!r}")


def normalize_bytes(data: bytes, epoch: int) -> bytes:
    """Return the normalized ``.tar.gz`` bytes for the sdist given as ``data``."""
    entries: list[tuple[tarfile.TarInfo, bytes | None]] = []
    seen: set[str] = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            for member in archive.getmembers():
                _check_name(member.name)
                key = member.name.rstrip("/")
                if key in seen:
                    raise NormalizationError(f"duplicate entry: {member.name!r}")
                seen.add(key)
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise NormalizationError(f"unreadable file entry: {member.name!r}")
                    entries.append((member, handle.read()))
                elif member.isdir():
                    entries.append((member, None))
                elif member.issym() or member.islnk():
                    _check_link(member)
                    entries.append((member, None))
                else:
                    raise NormalizationError(f"unsupported entry type: {member.name!r}")
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise NormalizationError(f"cannot read archive: {exc}") from exc

    entries.sort(key=lambda item: item[0].name)
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as out:
        for member, payload in entries:
            info = tarfile.TarInfo(member.name)
            info.type = member.type
            info.mode = member.mode
            info.linkname = member.linkname
            info.mtime = epoch
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            if payload is not None:
                info.size = len(payload)
                out.addfile(info, io.BytesIO(payload))
            else:
                info.size = 0
                out.addfile(info)

    gz_buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=gz_buffer, mtime=epoch) as gz:
        gz.write(tar_buffer.getvalue())
    return gz_buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    source, target = Path(args[0]), Path(args[1])
    try:
        epoch = source_date_epoch()
        normalized = normalize_bytes(source.read_bytes(), epoch)
    except (NormalizationError, OSError) as exc:
        print(f"normalize_sdist: {exc}", file=sys.stderr)
        return 1
    target.write_bytes(normalized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
