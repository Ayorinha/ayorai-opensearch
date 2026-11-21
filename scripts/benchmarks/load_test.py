"""Closed-loop load test for a running AYORAI ATTRACTOR instance (standard library only).

Each of N workers keeps one HTTP/1.1 connection and sends requests back to back
for D seconds. The report has throughput, latency percentiles (nearest rank),
status counts and transport errors, as JSON.

    ATTRACTOR_LOAD_KEY=... python scripts/benchmarks/load_test.py \\
        --url http://127.0.0.1:8000 --scenario check --concurrency 8 --duration 30

Scenarios use fixed synthetic text only. The key is read from the environment
and never printed.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import threading
import time
from typing import Any
from urllib.parse import urlsplit

_DOCUMENT = (
    "Relatório sintético. A receita líquida da Empresa Sintética foi de R$ 10 milhões em 2025. "
    "O lucro operacional foi de R$ 2 milhões. A empresa tinha 120 funcionários no fim do ano. "
) * 20

SCENARIOS: dict[str, tuple[str, str, dict[str, Any] | None]] = {
    "health": ("GET", "/health", None),
    "check": (
        "POST",
        "/v1/check",
        {
            "claims": [
                "A receita líquida foi de R$ 10 milhões em 2025.",
                "O lucro operacional foi de R$ 3 milhões.",
            ],
            "documents": [{"id": "relatorio", "text": _DOCUMENT, "url": "https://example.test/r"}],
        },
    ),
    "audit": ("POST", "/v1/audit", {"query": "receita da Empresa Sintética em 2025"}),
}


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * quantile + 0.999999))
    return ordered[rank - 1]


def run(url: str, scenario: str, concurrency: int, duration: float, key: str) -> dict[str, Any]:
    method, path, body = SCENARIOS[scenario]
    payload = None if body is None else json.dumps(body).encode("utf-8")
    parts = urlsplit(url)
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    latencies: list[float] = []
    statuses: dict[str, int] = {}
    errors: dict[str, int] = {}
    lock = threading.Lock()
    deadline = time.perf_counter() + duration

    def worker() -> None:
        connection = http.client.HTTPConnection(parts.hostname or "127.0.0.1", parts.port or 80)
        local_latencies: list[float] = []
        local_statuses: dict[str, int] = {}
        local_errors: dict[str, int] = {}
        while time.perf_counter() < deadline:
            started = time.perf_counter()
            try:
                connection.request(method, path, body=payload, headers=headers)
                response = connection.getresponse()
                response.read()
                local_latencies.append(time.perf_counter() - started)
                code = str(response.status)
                local_statuses[code] = local_statuses.get(code, 0) + 1
                if response.getheader("Connection", "").lower() == "close":
                    connection.close()
                    connection = http.client.HTTPConnection(
                        parts.hostname or "127.0.0.1", parts.port or 80
                    )
            except (OSError, http.client.HTTPException) as exc:
                name = type(exc).__name__
                local_errors[name] = local_errors.get(name, 0) + 1
                connection.close()
                connection = http.client.HTTPConnection(
                    parts.hostname or "127.0.0.1", parts.port or 80
                )
        connection.close()
        with lock:
            latencies.extend(local_latencies)
            for code, count in local_statuses.items():
                statuses[code] = statuses.get(code, 0) + count
            for name, count in local_errors.items():
                errors[name] = errors.get(name, 0) + count

    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started
    completed = len(latencies)
    report: dict[str, Any] = {
        "scenario": scenario,
        "concurrency": concurrency,
        "duration_s": round(elapsed, 2),
        "requests": completed,
        "throughput_rps": round(completed / elapsed, 1) if elapsed else 0.0,
        "statuses": dict(sorted(statuses.items())),
        "transport_errors": dict(sorted(errors.items())),
    }
    if latencies:
        report["latency_ms"] = {
            name: round(percentile(latencies, q) * 1000, 1)
            for name, q in (("p50", 0.50), ("p95", 0.95), ("p99", 0.99), ("max", 1.0))
        }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="check")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--duration", type=float, default=20.0)
    args = parser.parse_args(argv)
    if args.concurrency < 1 or args.duration <= 0:
        parser.error("concurrency must be >= 1 and duration > 0")
    key = os.environ.get("ATTRACTOR_LOAD_KEY", "")
    print(json.dumps(run(args.url, args.scenario, args.concurrency, args.duration, key)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
