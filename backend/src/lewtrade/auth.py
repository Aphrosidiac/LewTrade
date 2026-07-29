"""API key gate for endpoints that cost money (Claude calls) or mutate state.
Optional by design — matches notifications.py's pattern of "nothing required
to run the app without it": if LEWTRADE_API_KEY isn't set, the gate is a
no-op so local dev needs no setup, but that means it MUST be set in prod.
"""
from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("LEWTRADE_API_KEY")
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
