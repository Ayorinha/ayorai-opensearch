"""Capture official source documents byte-for-byte and record provenance.

Used for the PT-BR RGC benchmark under DEC-002. Each target URL is
downloaded without any transformation; the exact bytes are stored and a
manifest records URL, final URL, HTTP status, content type, size,
SHA-256 and the UTC capture time. Nothing here interprets the content.

Usage:
    python scripts/capture_sources.py evals/ptbr/capture/targets.json \
        evals/ptbr/sources/raw
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 AYORAI-ATTRACTOR-source-capture"
)
EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "application/xhtml+xml": ".html",
    "text/plain": ".txt",
}


def _extension(content_type: str) -> str:
    base = content_type.split(";", 1)[0].strip().lower()
    return EXTENSIONS.get(base, ".bin")


def capture(target: dict[str, str], out_dir: Path) -> dict[str, object]:
    request = urllib.request.Request(target["url"], headers={"User-Agent": USER_AGENT})
    record: dict[str, object] = {"id": target["id"], "url": target["url"]}
    started = dt.datetime.now(dt.timezone.utc)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            body = response.read()
            content_type = response.headers.get("Content-Type", "")
            record.update(
                status=response.status,
                final_url=response.geturl(),
                content_type=content_type,
                last_modified=response.headers.get("Last-Modified"),
            )
    except urllib.error.HTTPError as exc:
        record.update(status=exc.code, error=f"HTTPError: {exc.reason}")
        return record
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        record.update(status=None, error=f"{type(exc).__name__}: {exc}")
        return record

    path = out_dir / f"{target['id']}{_extension(str(record['content_type']))}"
    path.write_bytes(body)
    record.update(
        retrieved_at=started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        artifact_path=path.as_posix(),
        size_bytes=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
    )
    return record


def main() -> int:
    targets_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    targets = json.loads(targets_path.read_text(encoding="utf-8"))["targets"]
    records = []
    for target in targets:
        records.append(capture(target, out))
        time.sleep(1)  # be polite to public servers
    manifest = {
        "capture_method": "scripts/capture_sources.py via urllib (exact bytes, no normalization)",
        "runner": {
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_url": (
                f"{os.environ.get('GITHUB_SERVER_URL')}/{os.environ.get('GITHUB_REPOSITORY')}"
                f"/actions/runs/{os.environ.get('GITHUB_RUN_ID')}"
                if os.environ.get("GITHUB_RUN_ID")
                else None
            ),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "platform": platform.platform(),
        },
        "records": records,
    }
    (out / "CAPTURE-MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for r in records:
        print(r["id"], r.get("status"), r.get("content_type"), r.get("size_bytes"), r.get("sha256") or r.get("error"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
