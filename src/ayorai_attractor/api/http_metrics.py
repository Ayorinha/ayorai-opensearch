"""Process-local HTTP metrics in the Prometheus text format (exposed at GET /metrics).

Labels are bounded: the route label comes from ``request_context._route_label``,
which maps every unknown client path to ``unmatched``, and the status label is
the numeric HTTP status. No request content, principal, key or trace ID is ever
a label. Counters are per process: with several workers or replicas, aggregate
them in Prometheus (``sum by (route)``).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Sequence

from ayorai_attractor import __version__

# Seconds. Fixed buckets so dashboards and SLO queries are stable across versions.
LATENCY_BUCKETS: tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


# The method comes from the client; anything else is folded into "OTHER" so a
# client cannot create an unbounded number of series.
_KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format(value: float) -> str:
    return repr(float(value)) if not float(value).is_integer() else str(int(value))


class HttpMetrics:
    """Thread-safe counters and a latency histogram per route."""

    def __init__(self, buckets: Sequence[float] = LATENCY_BUCKETS) -> None:
        if list(buckets) != sorted(set(buckets)) or not buckets:
            raise ValueError("buckets must be strictly increasing")
        self._buckets = tuple(buckets)
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = {}
        self._bucket_counts: dict[str, list[int]] = {}
        self._duration_sum: dict[str, float] = {}
        self._duration_count: dict[str, int] = {}
        self._audit_record_failures = 0
        self._api_keys_reload_failures = 0
        self._started = time.time()

    def observe(self, route: str, method: str, status: int, duration_seconds: float) -> None:
        duration = max(0.0, duration_seconds)
        method = method if method in _KNOWN_METHODS else "OTHER"
        status = status if 100 <= status <= 599 else 0
        with self._lock:
            key = (route, method, status)
            self._requests[key] = self._requests.get(key, 0) + 1
            counts = self._bucket_counts.setdefault(route, [0] * len(self._buckets))
            for index, bound in enumerate(self._buckets):
                if duration <= bound:
                    counts[index] += 1
            self._duration_sum[route] = self._duration_sum.get(route, 0.0) + duration
            self._duration_count[route] = self._duration_count.get(route, 0) + 1

    def audit_record_failed(self) -> None:
        with self._lock:
            self._audit_record_failures += 1

    def api_keys_reload_failed(self) -> None:
        with self._lock:
            self._api_keys_reload_failures += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP attractor_build_info Build information.",
                "# TYPE attractor_build_info gauge",
                f'attractor_build_info{{version="{_escape(__version__)}"}} 1',
                "# HELP attractor_process_start_time_seconds Process start, Unix time.",
                "# TYPE attractor_process_start_time_seconds gauge",
                f"attractor_process_start_time_seconds {_format(round(self._started, 3))}",
                "# HELP attractor_http_requests_total HTTP responses by route, method and status.",
                "# TYPE attractor_http_requests_total counter",
            ]
            for (route, method, status), count in sorted(self._requests.items()):
                lines.append(
                    f'attractor_http_requests_total{{route="{_escape(route)}",'
                    f'method="{_escape(method)}",status="{status}"}} {count}'
                )
            lines += [
                "# HELP attractor_http_request_duration_seconds HTTP latency by route.",
                "# TYPE attractor_http_request_duration_seconds histogram",
            ]
            for route in sorted(self._bucket_counts):
                label = _escape(route)
                for bound, count in zip(self._buckets, self._bucket_counts[route], strict=True):
                    lines.append(
                        f'attractor_http_request_duration_seconds_bucket{{route="{label}",'
                        f'le="{_format(bound)}"}} {count}'
                    )
                total = self._duration_count[route]
                lines.append(
                    f'attractor_http_request_duration_seconds_bucket{{route="{label}",le="+Inf"}} '
                    f"{total}"
                )
                lines.append(
                    f'attractor_http_request_duration_seconds_sum{{route="{label}"}} '
                    f"{_format(round(self._duration_sum[route], 6))}"
                )
                lines.append(
                    f'attractor_http_request_duration_seconds_count{{route="{label}"}} {total}'
                )
            lines += [
                "# HELP attractor_audit_record_failures_total Audit traces that failed to record.",
                "# TYPE attractor_audit_record_failures_total counter",
                f"attractor_audit_record_failures_total {self._audit_record_failures}",
                "# HELP attractor_api_keys_reload_failures_total Key-file reloads rejected as "
                "invalid; the last valid registry stays in use.",
                "# TYPE attractor_api_keys_reload_failures_total counter",
                f"attractor_api_keys_reload_failures_total {self._api_keys_reload_failures}",
            ]
        return "\n".join(lines) + "\n"


http_metrics = HttpMetrics()
