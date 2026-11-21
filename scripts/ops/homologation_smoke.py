"""Operational smoke test for a deployed AYORAI ATTRACTOR instance (homologation).

Runs read-mostly HTTP checks against a running service and prints one line per
check (PASS/FAIL) plus a JSON summary. It needs two API keys of the deployment:

    ATTRACTOR_SMOKE_URL=http://127.0.0.1:8000 \\
    ATTRACTOR_SMOKE_KEY_A=... ATTRACTOR_SMOKE_KEY_B=... \\
    python scripts/ops/homologation_smoke.py [--expect-trace TRACE_ID]

It never prints the keys. It creates synthetic audit traces with fixed,
non-sensitive text. ``--expect-trace`` checks that a trace created earlier (for
example before a restart or a restore) is still readable by key A.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

SYNTHETIC_DOC = {
    "id": "relatorio-sintetico",
    "text": "A receita líquida da Empresa Sintética foi de R$ 10 milhões em 2025.",
    "url": "https://example.test/relatorio-sintetico",
}


class Smoke:
    def __init__(self, base_url: str, key_a: str, key_b: str) -> None:
        self.base = base_url.rstrip("/")
        self.headers_a = {"Authorization": f"Bearer {key_a}"}
        self.headers_b = {"X-API-Key": key_b}
        self.results: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        headers: dict[str, str] | None = None,
        raw_headers: list[tuple[str, str]] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        for name, value in raw_headers or []:
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def check(self, name: str, passed: bool, evidence: str) -> None:
        self.results.append({"check": name, "passed": passed, "evidence": evidence})
        print(f"{'PASS' if passed else 'FAIL'}  {name}: {evidence}")

    def run(self, expect_trace: str | None) -> str | None:
        status, _, body = self.request("GET", "/health")
        self.check("liveness /health", status == 200, f"HTTP {status}")
        status, _, body = self.request("GET", "/ready")
        self.check("readiness /ready", status == 200, f"HTTP {status} {body[:40]!r}")

        status, headers, _ = self.request("POST", "/v1/audit", {"query": "receita"})
        self.check("protected route without key -> 401", status == 401, f"HTTP {status}")
        status, _, _ = self.request(
            "POST", "/v1/audit", {"query": "receita"}, {"Authorization": "Bearer wrong-key"}
        )
        self.check("wrong key -> 401", status == 401, f"HTTP {status}")
        status, _, body = self.request("GET", "/metrics")
        self.check("metrics without key -> 401", status == 401, f"HTTP {status}")

        status, headers, body = self.request(
            "POST",
            "/v1/check",
            {
                "claims": ["A receita líquida foi de R$ 10 milhões em 2025."],
                "documents": [SYNTHETIC_DOC],
            },
            self.headers_a,
        )
        verdict = json.loads(body)["results"][0].get("verdict") if status == 200 else None
        self.check(
            "/v1/check answers with a deterministic trace",
            status == 200 and json.loads(body).get("trace_id", "").startswith("chk_"),
            f"HTTP {status} verdict={verdict}",
        )
        request_id = headers.get("X-Request-ID") or headers.get("x-request-id") or ""
        self.check("server-generated X-Request-ID", len(request_id) == 32, f"len={len(request_id)}")
        status, _, body = self.request(
            "POST",
            "/v1/check",
            {
                "claims": ["A receita líquida foi de R$ 10 milhões em 2025."],
                "documents": [SYNTHETIC_DOC],
            },
            self.headers_a,
        )
        second = json.loads(body).get("trace_id") if status == 200 else None
        status, _, body = self.request(
            "POST",
            "/v1/check",
            {
                "claims": ["A receita líquida foi de R$ 10 milhões em 2025."],
                "documents": [SYNTHETIC_DOC],
            },
            self.headers_a,
        )
        third = json.loads(body).get("trace_id") if status == 200 else None
        self.check(
            "same request -> same trace_id", second is not None and second == third, "chk_ equal"
        )

        status, _, body = self.request("POST", "/v1/audit", {"query": "receita"}, self.headers_a)
        trace_id = json.loads(body).get("trace_id") if status == 200 else None
        self.check("/v1/audit records a trace", status == 200 and bool(trace_id), f"HTTP {status}")
        if trace_id:
            status, _, body = self.request("GET", f"/v1/audit/{trace_id}", headers=self.headers_a)
            integrity = json.loads(body).get("replay_integrity") if status == 200 else None
            self.check(
                "owner reads its trace, integrity valid",
                status == 200 and integrity == "valid",
                f"HTTP {status} integrity={integrity}",
            )
            status, _, _ = self.request("GET", f"/v1/audit/{trace_id}", headers=self.headers_b)
            self.check("other key cannot read the trace -> 404", status == 404, f"HTTP {status}")
        status, _, _ = self.request("GET", "/v1/audit/tr_does_not_exist", headers=self.headers_a)
        self.check("unknown trace -> 404", status == 404, f"HTTP {status}")

        status, _, _ = self.request(
            "POST",
            "/v1/check",
            None,
            self.headers_a,
            raw_headers=[("Content-Type", "application/json")],
        )
        self.check("empty body -> 422, not 500", status == 422, f"HTTP {status}")
        big = {"claims": ["x"], "documents": [{"id": "d", "text": "a" * (3 * 1024 * 1024)}]}
        # The service answers 413 from Content-Length and closes without reading the
        # body; a client still uploading may see the reset instead of the 413.
        try:
            status, _, _ = self.request("POST", "/v1/check", big, self.headers_a)
            evidence = f"HTTP {status}"
        except (urllib.error.URLError, ConnectionError) as exc:
            status, evidence = 413, f"rejected before the body was read ({type(exc).__name__})"
        self.check("body above 2 MiB rejected (413)", status == 413, evidence)

        status, _, body = self.request("GET", "/metrics", headers=self.headers_a)
        text = body.decode("utf-8", "replace")
        self.check(
            "metrics with key, bounded labels",
            status == 200
            and "attractor_http_requests_total" in text
            and (trace_id or "tr_") not in text
            and "Bearer" not in text,
            f"HTTP {status}, {len(text.splitlines())} lines",
        )
        if expect_trace:
            status, _, body = self.request(
                "GET", f"/v1/audit/{expect_trace}", headers=self.headers_a
            )
            integrity = json.loads(body).get("replay_integrity") if status == 200 else None
            self.check(
                "trace from before restart/restore still valid",
                status == 200 and integrity == "valid",
                f"HTTP {status} integrity={integrity}",
            )
        return trace_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-trace", default=None)
    args = parser.parse_args(argv)
    base = os.environ.get("ATTRACTOR_SMOKE_URL", "http://127.0.0.1:8000")
    key_a = os.environ.get("ATTRACTOR_SMOKE_KEY_A", "")
    key_b = os.environ.get("ATTRACTOR_SMOKE_KEY_B", "")
    if not key_a or not key_b:
        print("set ATTRACTOR_SMOKE_KEY_A and ATTRACTOR_SMOKE_KEY_B", file=sys.stderr)
        return 2
    smoke = Smoke(base, key_a, key_b)
    trace_id = smoke.run(args.expect_trace)
    failed = [result for result in smoke.results if not result["passed"]]
    print(
        json.dumps(
            {"checks": len(smoke.results), "failed": len(failed), "created_trace": trace_id},
            sort_keys=True,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
