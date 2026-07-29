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


def limit(max_requests: int, window_s: float):
    def dependency(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
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
