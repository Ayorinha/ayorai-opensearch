"""Outbound HTTP transport for urllib-based providers.

urllib follows redirects and forwards every request header, including
``Authorization``, to the new location, even when it is another host or plain
HTTP. A provider endpoint that redirects (misconfiguration or compromise) would
therefore leak its API key and silently break the HTTPS-only boundary the
providers check before dispatch. This transport refuses every redirect: the
configured endpoint must answer directly.

Response bodies are read with a fixed upper bound, so a misbehaving endpoint
cannot exhaust the process memory with an unbounded reply.
"""

from __future__ import annotations

import json
import time
from email.message import Message
from typing import IO, Any
from urllib import error, request


class _RefuseRedirects(request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: Message,
        newurl: str,
    ) -> request.Request | None:
        raise error.HTTPError(req.full_url, code, f"redirect refused ({code})", headers, fp)


_OPENER = request.build_opener(_RefuseRedirects)


def open_without_redirects(req: request.Request, timeout: float) -> Any:
    """Open ``req`` like ``urllib.request.urlopen`` but never follow a redirect."""
    return _OPENER.open(req, timeout=timeout)


MAX_RESPONSE_BYTES = 10 * 1024 * 1024


_READ_CHUNK = 64 * 1024


def read_json(response: Any, limit: int | None = None, deadline: float | None = None) -> Any:
    """Read and decode a JSON body of at most ``limit`` bytes.

    ``limit`` defaults to ``MAX_RESPONSE_BYTES``, read at call time.

    ``deadline`` is a ``time.monotonic()`` value. urllib timeouts apply to each
    socket operation, so a server that sends a byte before every timeout would
    keep a single ``read`` open indefinitely; with a deadline the body is read
    in chunks and the deadline is checked between them.

    Oversized or late bodies raise ``URLError`` so providers report them like
    any other transport failure.
    """
    if limit is None:
        limit = MAX_RESPONSE_BYTES
    if deadline is None:
        body = response.read(limit + 1)
    else:
        read = getattr(response, "read1", None) or response.read
        chunks = bytearray()
        while len(chunks) <= limit:
            if time.monotonic() > deadline:
                raise error.URLError("response body was not received before the deadline")
            chunk = read(min(_READ_CHUNK, limit + 1 - len(chunks)))
            if not chunk:
                break
            chunks += chunk
        body = bytes(chunks)
    if len(body) > limit:
        raise error.URLError(f"response body exceeds {limit} bytes")
    return json.loads(body)
