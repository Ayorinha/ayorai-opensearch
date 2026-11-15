"""Outbound HTTP transport for urllib-based providers.

urllib follows redirects and forwards every request header, including
``Authorization``, to the new location, even when it is another host or plain
HTTP. A provider endpoint that redirects (misconfiguration or compromise) would
therefore leak its API key and silently break the HTTPS-only boundary the
providers check before dispatch. This transport refuses every redirect: the
configured endpoint must answer directly.
"""

from __future__ import annotations

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
