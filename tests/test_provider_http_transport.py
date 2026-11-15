"""The urllib provider transport must not follow redirects (credential leak)."""

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
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
