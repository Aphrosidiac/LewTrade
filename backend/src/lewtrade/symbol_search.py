"""Symbol autocomplete — no live API call. tradingview-mcp ships static
per-exchange symbol lists (~19k symbols total: NASDAQ, NYSE, Bursa, HKEX,
crypto venues, etc.) that it uses for its screener tools; we reuse the same
files as a search index. Forex/metals aren't in those lists (TradingView's
scanner doesn't cover that market — see _TA_ONLY_SCREENERS), so that handful
of pairs is hardcoded.
"""
from __future__ import annotations

import os

from tradingview_mcp.core.utils.validators import COINLIST_DIR

_STATIC_FOREX = [
    ("OANDA", "XAUUSD"), ("OANDA", "XAGUSD"), ("OANDA", "EURUSD"), ("OANDA", "GBPUSD"),
    ("OANDA", "USDJPY"), ("OANDA", "AUDUSD"), ("OANDA", "USDCAD"), ("OANDA", "NZDUSD"),
    ("OANDA", "USDCHF"), ("OANDA", "EURGBP"), ("OANDA", "EURJPY"), ("OANDA", "GBPJPY"),
]

_index: list[tuple[str, str]] | None = None  # (exchange, symbol)


def _build_index() -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = list(_STATIC_FOREX)
    seen = set(entries)
    for filename in sorted(os.listdir(COINLIST_DIR)):
        if not filename.endswith(".txt"):
            continue
        path = os.path.join(COINLIST_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" not in line:
                    continue
                exchange, symbol = line.split(":", 1)
                key = (exchange, symbol)
                if key not in seen:
                    seen.add(key)
                    entries.append(key)
    return entries


def _get_index() -> list[tuple[str, str]]:
    global _index
    if _index is None:
        _index = _build_index()
    return _index


def search(query: str, limit: int = 15) -> list[dict]:
    q = query.strip().upper()
    if not q:
        return []

    starts_with = []
    contains = []
    for exchange, symbol in _get_index():
        if symbol.startswith(q):
            starts_with.append((exchange, symbol))
        elif q in symbol:
            contains.append((exchange, symbol))
        if len(starts_with) >= limit:
            break

    starts_with.sort(key=lambda es: len(es[1]))
    contains.sort(key=lambda es: len(es[1]))

    results = (starts_with + contains)[:limit]
    return [{"symbol": s, "exchange": e} for e, s in results]
