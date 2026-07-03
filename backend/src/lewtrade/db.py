"""SQLite storage — call history (track record), watchlist, response cache.

Plain sqlite3, no ORM: the schema is tiny and this is a single-instance
personal tool, so the extra dependency isn't worth it.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "lewtrade.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    created_at REAL NOT NULL,
    price_at_call REAL NOT NULL,
    call TEXT NOT NULL,
    confidence TEXT NOT NULL,
    gauge INTEGER NOT NULL,
    verdict_json TEXT NOT NULL,
    resolve_at REAL NOT NULL,
    resolved_at REAL,
    price_at_resolve REAL,
    outcome TEXT
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1h',
    added_at REAL NOT NULL,
    last_call TEXT,
    UNIQUE(symbol, exchange, timeframe)
);

CREATE TABLE IF NOT EXISTS analysis_cache (
    cache_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        # WAL lets the background scheduler (resolving calls, scanning the
        # watchlist) write concurrently with API request reads/writes instead
        # of blocking each other — persists in the db file, only needs setting once.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(SCHEMA)


# ── Horizon: how far ahead to check whether a call was right ───────────────
_RESOLVE_HORIZON_S = {
    "5m": 30 * 60,
    "15m": 2 * 60 * 60,
    "1h": 8 * 60 * 60,
    "4h": 24 * 60 * 60,
    "1D": 5 * 24 * 60 * 60,
}


def log_call(symbol: str, exchange: str, timeframe: str, price: float, verdict: dict) -> None:
    now = time.time()
    horizon = _RESOLVE_HORIZON_S.get(timeframe, 8 * 60 * 60)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO calls (symbol, exchange, timeframe, created_at, price_at_call, "
            "call, confidence, gauge, verdict_json, resolve_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, exchange, timeframe, now, price, verdict["call"], verdict["confidence"],
             verdict["gauge"], json.dumps(verdict), now + horizon),
        )


# A call is "correct" if the price moved the direction implied by the call by
# more than a small noise threshold. NEUTRAL calls aren't scored.
_DIRECTIONAL_THRESHOLD_PCT = 0.15


def _score_outcome(call: str, price_at_call: float, price_now: float) -> str | None:
    if price_at_call <= 0:
        return None
    change_pct = ((price_now - price_at_call) / price_at_call) * 100
    if call in ("STRONG_BUY", "BUY"):
        if change_pct > _DIRECTIONAL_THRESHOLD_PCT:
            return "win"
        if change_pct < -_DIRECTIONAL_THRESHOLD_PCT:
            return "loss"
        return "flat"
    if call in ("STRONG_SELL", "SELL"):
        if change_pct < -_DIRECTIONAL_THRESHOLD_PCT:
            return "win"
        if change_pct > _DIRECTIONAL_THRESHOLD_PCT:
            return "loss"
        return "flat"
    return None  # NEUTRAL — not scored


def resolve_due_calls(price_lookup) -> int:
    """Resolve any calls past their horizon. price_lookup(symbol, exchange) -> float | None.

    Returns count resolved.
    """
    now = time.time()
    with get_conn() as conn:
        due = conn.execute(
            "SELECT * FROM calls WHERE resolved_at IS NULL AND resolve_at <= ?", (now,)
        ).fetchall()

        resolved = 0
        for row in due:
            price_now = price_lookup(row["symbol"], row["exchange"])
            if price_now is None:
                continue
            outcome = _score_outcome(row["call"], row["price_at_call"], price_now)
            conn.execute(
                "UPDATE calls SET resolved_at = ?, price_at_resolve = ?, outcome = ? WHERE id = ?",
                (now, price_now, outcome, row["id"]),
            )
            resolved += 1
        return resolved


def track_record(limit: int = 50) -> dict:
    with get_conn() as conn:
        scored = conn.execute(
            "SELECT outcome FROM calls WHERE outcome IS NOT NULL"
        ).fetchall()
        wins = sum(1 for r in scored if r["outcome"] == "win")
        losses = sum(1 for r in scored if r["outcome"] == "loss")
        flats = sum(1 for r in scored if r["outcome"] == "flat")
        decided = wins + losses
        win_rate = round((wins / decided) * 100, 1) if decided else None

        recent = conn.execute(
            "SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()

        return {
            "total_calls": conn.execute("SELECT COUNT(*) c FROM calls").fetchone()["c"],
            "resolved": len(scored),
            "wins": wins,
            "losses": losses,
            "flats": flats,
            "win_rate": win_rate,
            "recent": [dict(r) for r in recent],
        }


# ── Watchlist ────────────────────────────────────────────────────────────────

def add_watchlist(symbol: str, exchange: str, timeframe: str = "1h") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (symbol, exchange, timeframe, added_at) VALUES (?, ?, ?, ?)",
            (symbol, exchange, timeframe, time.time()),
        )


def remove_watchlist(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))


def list_watchlist() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at ASC").fetchall()
        return [dict(r) for r in rows]


def set_watchlist_last_call(item_id: int, call: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE watchlist SET last_call = ? WHERE id = ?", (call, item_id))


# ── Response cache ───────────────────────────────────────────────────────────

def cache_get(key: str, max_age_s: float) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM analysis_cache WHERE cache_key = ?", (key,)).fetchone()
        if not row:
            return None
        if time.time() - row["created_at"] > max_age_s:
            return None
        return json.loads(row["payload_json"])


def cache_set(key: str, payload: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO analysis_cache (cache_key, payload_json, created_at) VALUES (?, ?, ?) "
            "ON CONFLICT(cache_key) DO UPDATE SET payload_json = excluded.payload_json, created_at = excluded.created_at",
            (key, json.dumps(payload), time.time()),
        )
