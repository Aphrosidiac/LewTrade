from __future__ import annotations

import asyncio

from dotenv import load_dotenv
load_dotenv()

from anthropic import APIError
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lewtrade import db, symbol_search
from lewtrade.auth import require_api_key
from lewtrade.engine import analyze
from lewtrade.ratelimit import limit
from lewtrade.scheduler import start_background_tasks

app = FastAPI(title="LewTrade")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    db.init_db()
    symbol_search._get_index()  # warm the index so the first search isn't slow
    start_background_tasks()


def _run_analysis(symbol: str, exchange: str | None, timeframe: str):
    try:
        result = analyze(symbol, exchange, timeframe)
    except KeyError as exc:
        if "ANTHROPIC_API_KEY" in str(exc):
            raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set in backend/.env")
        raise
    except APIError as exc:
        # Not 502/504: Cloudflare (this site is proxied through it) replaces
        # those specific codes with its own generic error page regardless of
        # what the origin actually returned, discarding this detail message.
        raise HTTPException(status_code=500, detail=f"Claude API error: {exc}")
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.get("/api/analyze", dependencies=[Depends(require_api_key), Depends(limit(20, 60))])
def get_analysis(symbol: str, exchange: str | None = None, timeframe: str = "1h"):
    return _run_analysis(symbol, exchange, timeframe)


@app.get("/api/symbols/search")
def search_symbols(q: str = "", limit: int = 15):
    return symbol_search.search(q, limit)


@app.get("/api/track-record")
def get_track_record(limit: int = 50):
    return db.track_record(limit)


@app.get("/api/history")
def get_history(symbol: str, exchange: str, timeframe: str = "1h", limit: int = 30):
    return db.symbol_history(symbol, exchange, timeframe, limit)


class WatchlistIn(BaseModel):
    symbol: str
    exchange: str | None = None
    timeframe: str = "1h"


@app.get("/api/watchlist")
def get_watchlist():
    return db.list_watchlist()


@app.post("/api/watchlist", dependencies=[Depends(require_api_key)])
def post_watchlist(item: WatchlistIn):
    from lewtrade.symbols import resolve
    norm_symbol, exchange, _, _ = resolve(item.symbol, item.exchange)
    db.add_watchlist(norm_symbol, exchange, item.timeframe)
    return db.list_watchlist()


@app.delete("/api/watchlist/{item_id}", dependencies=[Depends(require_api_key)])
def delete_watchlist(item_id: int):
    db.remove_watchlist(item_id)
    return db.list_watchlist()


@app.get("/api/watchlist/scan", dependencies=[Depends(require_api_key), Depends(limit(5, 60))])
async def scan_watchlist():
    items = db.list_watchlist()

    async def run_one(item: dict):
        try:
            result = await asyncio.to_thread(analyze, item["symbol"], item["exchange"], item["timeframe"])
        except Exception as exc:
            # watchlist_id matters on this path too — the frontend keys results
            # by it, so omitting it made a failed scan vanish silently instead
            # of marking the row as errored.
            return {"watchlist_id": item["id"], "symbol": item["symbol"],
                    "exchange": item["exchange"], "timeframe": item["timeframe"], "error": str(exc)}
        result["watchlist_id"] = item["id"]
        return result

    return await asyncio.gather(*(run_one(item) for item in items))


@app.get("/api/health")
def health():
    return {"status": "ok"}
