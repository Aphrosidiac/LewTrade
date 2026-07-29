"""Minimal in-memory per-IP rate limiter for the endpoints that trigger a
Claude call. PM2 runs a single worker (see ecosystem.config.js), so an
in-memory counter is enough — no Redis needed for a personal tool.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_hits: dict[str, deque[float]] = defaultdict(deque)

# A distinct IP per request (scanners, IP rotation) would otherwise grow this
# dict forever — crude but sufficient bound for a personal tool, not an
# attempt at a fully attack-hardened limiter.
_MAX_TRACKED_IPS = 5000


def _client_ip(request: Request) -> str:
    # The site is proxied through Cloudflare, which always sets this to the
    # real visitor IP and strips any client-supplied copy at its edge — more
    # reliable than X-Forwarded-For, which past Cloudflare resolves to one of
    # its own edge node IPs rather than the actual visitor (confirmed live:
    # request.client.host was landing on addresses in Cloudflare's own
    # ranges). Falls back to request.client for local dev, where there's no
    # Cloudflare hop and this header won't be present.
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip
    return request.client.host if request.client else "unknown"


def limit(max_requests: int, window_s: float):
    def dependency(request: Request) -> None:
        ip = _client_ip(request)
        if ip not in _hits and len(_hits) >= _MAX_TRACKED_IPS:
            _hits.clear()

        now = time.time()
        hits = _hits[ip]
        while hits and hits[0] < now - window_s:
            hits.popleft()
        if len(hits) >= max_requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded — try again shortly")
        hits.append(now)
    return dependency
