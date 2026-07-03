"""Push a message when a watchlist symbol's call changes. Two optional
channels, both configured via env vars — nothing required to run the app
without alerts.
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("lewtrade.notifications")


def notify(text: str) -> None:
    _send_webhook(text)
    _send_telegram(text)


def _send_webhook(text: str) -> None:
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"content": text, "text": text}, timeout=5)
    except Exception:
        log.exception("webhook alert failed")


def _send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=5,
        )
    except Exception:
        log.exception("telegram alert failed")
