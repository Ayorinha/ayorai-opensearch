"""Deterministically repack a source distribution (sdist) archive.

The normalizer fixes member order and non-semantic metadata while streaming file
contents through temporary files. It never extracts archive paths onto the
filesystem and does not retain the archive or member payloads in RAM.

- PAX tar format; entries sorted by name; no inherited PAX headers;
- file modes normalized to 0644 or 0755, directories to 0755;
- mtime set to SOURCE_DATE_EPOCH; uid/gid 0; empty user/group names;
- gzip header mtime set to SOURCE_DATE_EPOCH and filename empty.

Unsafe paths, entries outside the single sdist root, duplicate members, links
outside that root, devices and FIFOs are rejected.

Usage: SOURCE_DATE_EPOCH=<int> python scripts/normalize_sdist.py <input.tar.gz> <output.tar.gz>
"""

from __future__ import annotations

import gzip
import io
import os
import posixpath
import re
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import BinaryIO


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


def _check_name(name: str) -> list[str]:
    if not name or name.startswith("/") or "\\" in name:
        raise NormalizationError(f"unsafe entry name: {name!r}")
    parts = name.rstrip("/").split("/")
    if any(part in ("", ".", "..") or re.match(r"^[A-Za-z]:", part) for part in parts):
        raise NormalizationError(f"unsafe entry name: {name!r}")
    return parts


def _check_link(member: tarfile.TarInfo, root: str) -> None:
    target = member.linkname
    target_parts = _check_name(target)
    if member.issym():
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(member.name), target))
    else:
        # Tar hard-link names are archive-root-relative.
        resolved = posixpath.normpath(target)
    if resolved != root and not resolved.startswith(root + "/"):
        raise NormalizationError(f"link leaves the sdist root: {member.name!r} -> {target!r}")
    if not target_parts or target.startswith("/"):
        raise NormalizationError(f"unsafe link target in {member.name!r}: {target!r}")


def _normalized_mode(member: tarfile.TarInfo) -> int:
    if member.isdir():
        return 0o755
    return 0o755 if member.mode & 0o111 else 0o644


def _normalize_stream(source: BinaryIO, target: BinaryIO, epoch: int) -> None:
    # Store payloads on disk so memory usage does not grow with archive size.
    with tempfile.TemporaryDirectory(prefix="normalize-sdist-") as temp_dir:
        entries: list[tuple[tarfile.TarInfo, str | None]] = []
        seen: set[str] = set()
        root: str | None = None
        try:
            with tarfile.open(fileobj=source, mode="r|gz") as archive:
                for member in archive:
                    parts = _check_name(member.name)
                    key = member.name.rstrip("/")
                    if key in seen:
                        raise NormalizationError(f"duplicate entry: {member.name!r}")
                    seen.add(key)

                    if root is None:
                        root = parts[0]
                    if parts[0] != root:
                        raise NormalizationError(
                            f"entry outside the sdist root {root!r}: {member.name!r}"
                        )
                    if len(parts) == 1 and not member.isdir():
                        raise NormalizationError(
                            f"non-directory member at sdist root: {member.name!r}"
                        )

                    if member.isfile():
                        handle = archive.extractfile(member)
                        if handle is None:
                            raise NormalizationError(f"unreadable file entry: {member.name!r}")
                        payload_path = os.path.join(temp_dir, f"payload-{len(entries)}")
                        with open(payload_path, "wb") as payload_file:
                            shutil.copyfileobj(handle, payload_file, length=1024 * 1024)
                        entries.append((member, payload_path))
                    elif member.isdir():
                        entries.append((member, None))
                    elif member.issym() or member.islnk():
                        _check_link(member, root)
                        entries.append((member, None))
                    else:
                        raise NormalizationError(f"unsupported entry type: {member.name!r}")
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise NormalizationError(f"cannot read archive: {exc}") from exc

        if root is None:
            raise NormalizationError("archive is empty")

        entries.sort(key=lambda item: item[0].name.rstrip("/"))
        with gzip.GzipFile(fileobj=target, filename="", mode="wb", mtime=epoch) as gz:
            with tarfile.open(fileobj=gz, mode="w|", format=tarfile.PAX_FORMAT) as out:
                for member, payload_path in entries:
                    info = tarfile.TarInfo(member.name.rstrip("/"))
                    info.type = member.type
                    info.mode = _normalized_mode(member)
                    info.linkname = member.linkname
                    info.mtime = epoch
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.pax_headers = {}
                    if payload_path is not None:
                        info.size = member.size
                        with open(payload_path, "rb") as payload_file:
                            out.addfile(info, payload_file)
                    else:
                        info.size = 0
                        out.addfile(info)


def normalize_bytes(data: bytes, epoch: int) -> bytes:
    """Return normalized sdist bytes; the CLI uses the streaming file path."""
    source = io.BytesIO(data)
    target = io.BytesIO()
    _normalize_stream(source, target, epoch)
    return target.getvalue()


def normalize_file(source: Path, target: Path, epoch: int) -> None:
    """Normalize a file using bounded-memory streaming and atomic replacement."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        with source.open("rb") as source_file, temporary_path.open("wb") as target_file:
            _normalize_stream(source_file, target_file, epoch)
        os.replace(temporary_path, target)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    source, target = Path(args[0]), Path(args[1])
    try:
        normalize_file(source, target, source_date_epoch())
    except (NormalizationError, OSError) as exc:
        print(f"normalize_sdist: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
