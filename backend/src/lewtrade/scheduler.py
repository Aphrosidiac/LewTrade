"""Background loop: resolves due calls for the track record, and scans the
watchlist periodically to alert on verdict flips.
"""
from __future__ import annotations

import asyncio
import logging

from lewtrade import db
from lewtrade.engine import analyze, get_current_price
from lewtrade.notifications import notify

log = logging.getLogger("lewtrade.scheduler")

RESOLVE_INTERVAL_S = 15 * 60
WATCHLIST_SCAN_INTERVAL_S = 15 * 60

_ALERT_WORTHY = {"STRONG_BUY", "STRONG_SELL"}


async def _resolve_loop():
    while True:
        try:
            count = await asyncio.to_thread(db.resolve_due_calls, get_current_price)
            if count:
                log.info("resolved %d due call(s)", count)
        except Exception:
            log.exception("resolve loop failed")
        await asyncio.sleep(RESOLVE_INTERVAL_S)


async def _watchlist_loop():
    while True:
        try:
            await asyncio.to_thread(_scan_watchlist_for_alerts)
        except Exception:
            log.exception("watchlist alert loop failed")
        await asyncio.sleep(WATCHLIST_SCAN_INTERVAL_S)


def _scan_watchlist_for_alerts():
    for item in db.list_watchlist():
        result = analyze(item["symbol"], item["exchange"], item["timeframe"], use_cache=True)
        if "error" in result:
            continue
        call = result["verdict"]["call"]
        previous = item["last_call"]
        db.set_watchlist_last_call(item["id"], call)

        if call != previous and call in _ALERT_WORTHY:
            notify(
                f"LewTrade: {item['symbol']} ({item['exchange']}, {item['timeframe']}) "
                f"flipped to {call} — {result['verdict']['trend_label']}"
            )


def start_background_tasks():
    asyncio.create_task(_resolve_loop())
    asyncio.create_task(_watchlist_loop())
