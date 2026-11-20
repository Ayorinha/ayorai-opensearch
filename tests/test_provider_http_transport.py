"""The urllib provider transport must not follow redirects (credential leak)."""

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from typing import Any
from urllib import error, request

import pytest

from ayorai_attractor.providers import _http


class _Recorder(BaseHTTPRequestHandler):
    hits: list[dict[str, str]]
    location = ""

    def _handle(self) -> None:
        type(self).hits.append(dict(self.headers.items()))
        if type(self).location:
            self.send_response(302)
            self.send_header("Location", type(self).location)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            body = b'{"ok": true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    do_GET = _handle
    do_POST = _handle

    def log_message(self, *args: object) -> None:
        return None


def _serve(location: str) -> tuple[HTTPServer, type[_Recorder]]:
    handler = type("Handler", (_Recorder,), {"hits": [], "location": location})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, handler


@pytest.fixture
def servers() -> Iterator[tuple[str, type[_Recorder], type[_Recorder]]]:
    target, target_handler = _serve("")
    target_url = f"http://127.0.0.1:{target.server_port}/collect"
    origin, origin_handler = _serve(target_url)
    try:
        yield f"http://127.0.0.1:{origin.server_port}/api", origin_handler, target_handler
    finally:
        for server in (origin, target):
            server.shutdown()
            server.server_close()


@pytest.mark.parametrize("method", ["GET", "POST"])
def test_redirect_is_refused_and_credentials_never_reach_the_target(
    servers: tuple[str, type[_Recorder], type[_Recorder]], method: str
) -> None:
    origin_url, origin, target = servers
    req = request.Request(
        origin_url,
        data=b"{}" if method == "POST" else None,
        headers={"Authorization": "Bearer secret-key"},
        method=method,
    )
    with pytest.raises(error.HTTPError, match="redirect refused") as raised:
        _http.open_without_redirects(req, timeout=5)
    raised.value.close()

    assert len(origin.hits) == 1
    assert target.hits == []


def test_direct_answer_is_returned() -> None:
    server, handler = _serve("")
    try:
        req = request.Request(
            f"http://127.0.0.1:{server.server_port}/api",
            headers={"Authorization": "Bearer secret-key"},
        )
        with _http.open_without_redirects(req, timeout=5) as response:
            assert response.read() == b'{"ok": true}'
        assert handler.hits[0]["Authorization"] == "Bearer secret-key"
    finally:
        server.shutdown()
        server.server_close()


def test_plain_urlopen_would_have_leaked_the_key(
    servers: tuple[str, type[_Recorder], type[_Recorder]],
) -> None:
    """Documents the defect the transport closes (stdlib behaviour)."""
    origin_url, _, target = servers
    req = request.Request(origin_url, headers={"Authorization": "Bearer secret-key"})
    with request.urlopen(req, timeout=5) as response:
        response.read()
    assert target.hits and target.hits[0].get("Authorization") == "Bearer secret-key"


class _Body:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0
        self.requested: list[int] = []

    def read(self, size: int = -1) -> bytes:
        # Consumed like a real HTTP response: b"" once the payload is read.
        self.requested.append(size)
        start = self.offset
        self.offset = len(self.payload) if size < 0 else min(len(self.payload), start + size)
        return self.payload[start : self.offset]


def test_read_json_accepts_a_body_at_the_limit() -> None:
    body = _Body(b'{"a": 1}')
    assert _http.read_json(body, limit=len(body.payload)) == {"a": 1}
    assert body.requested == [len(body.payload) + 1]


def test_read_json_rejects_an_oversized_body_without_reading_it_all() -> None:
    body = _Body(b"[" + b"0," * 100 + b"0]")
    with pytest.raises(error.URLError, match="exceeds 16 bytes"):
        _http.read_json(body, limit=16)
    assert body.requested == [17]


def test_provider_reports_an_oversized_body_as_a_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ayorai_attractor.providers.http_search import HttpSearchProvider

    class _Response(_Body):
        def __enter__(self) -> "_Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(_http, "MAX_RESPONSE_BYTES", 8)
    monkeypatch.setattr(
        _http, "open_without_redirects", lambda *a, **k: _Response(b'{"results": []}')
    )
    with pytest.raises(RuntimeError, match="Search request failed"):
        HttpSearchProvider("https://example.test/search").execute("query")


class _Drip(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", "12")
        self.end_headers()
        try:
            for byte in b'{"hits":[]} ':
                self.wfile.write(bytes([byte]))
                self.wfile.flush()
                time.sleep(0.4)
        except OSError:
            pass

    def log_message(self, *args: Any) -> None:
        return None


def test_read_json_deadline_stops_a_slow_drip_from_a_real_server() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Drip)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        opener = request.build_opener(request.ProxyHandler({}))
        started = time.monotonic()
        with opener.open(f"http://127.0.0.1:{server.server_address[1]}/", timeout=1) as response:
            with pytest.raises(error.URLError, match="deadline"):
                _http.read_json(response, deadline=started + 1.0)
        # Each read is bounded by the 1 s socket timeout, so the call ends within
        # about deadline + one read; without a deadline it lasts ~4.8 s.
        assert time.monotonic() - started < 2.5
    finally:
        server.shutdown()
        server.server_close()


def test_read_json_with_deadline_keeps_the_size_limit() -> None:
    body = _Body(b"[" + b"0," * 100_000 + b"0]")
    with pytest.raises(error.URLError, match="exceeds 1000 bytes"):
        _http.read_json(body, limit=1000, deadline=time.monotonic() + 60)
    assert sum(body.requested) <= 1001


def test_read_json_with_deadline_accepts_a_body_at_the_limit() -> None:
    body = _Body(b'{"a": 1}')
    assert _http.read_json(body, limit=len(body.payload), deadline=time.monotonic() + 60) == {
        "a": 1
    }


@pytest.mark.parametrize(
    ("module", "factory"),
    [
        ("ayorai_attractor.providers.http_search", "HttpSearchProvider"),
        ("ayorai_attractor.providers.openai_compatible", "OpenAICompatibleProvider"),
    ],
)
def test_providers_read_with_a_deadline(
    monkeypatch: pytest.MonkeyPatch, module: str, factory: str
) -> None:
    import importlib

    deadlines: list[float | None] = []

    def fake_read_json(
        response: Any, limit: int | None = None, deadline: float | None = None
    ) -> Any:
        deadlines.append(deadline)
        raise error.URLError("stop")

    class _Open:
        def __enter__(self) -> "_Open":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

    monkeypatch.setattr(_http, "read_json", fake_read_json)
    monkeypatch.setattr(_http, "open_without_redirects", lambda *a, **k: _Open())
    cls = getattr(importlib.import_module(module), factory)
    provider = (
        cls("https://search.example.test")
        if factory == "HttpSearchProvider"
        else cls(api_key="test")
    )
    before = time.monotonic()
    with pytest.raises(RuntimeError):
        provider.execute("query")
    assert len(deadlines) == 1 and deadlines[0] is not None
    assert before < deadlines[0] <= time.monotonic() + 60
