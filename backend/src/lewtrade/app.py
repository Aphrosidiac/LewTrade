from __future__ import annotations

import asyncio

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from lewtrade import db, symbol_search
from lewtrade.engine import analyze
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
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return result


@app.get("/api/analyze")
def get_analysis(symbol: str, exchange: str | None = None, timeframe: str = "1h"):
    return _run_analysis(symbol, exchange, timeframe)


@app.get("/api/symbols/search")
def search_symbols(q: str = "", limit: int = 15):
    return symbol_search.search(q, limit)


@app.get("/api/track-record")
def get_track_record(limit: int = 50):
    return db.track_record(limit)


class WatchlistIn(BaseModel):
    symbol: str
    exchange: str | None = None
    timeframe: str = "1h"


@app.get("/api/watchlist")
def get_watchlist():
    return db.list_watchlist()


@app.post("/api/watchlist")
def post_watchlist(item: WatchlistIn):
    from lewtrade.symbols import resolve
    norm_symbol, exchange, _, _ = resolve(item.symbol, item.exchange)
    db.add_watchlist(norm_symbol, exchange, item.timeframe)
    return db.list_watchlist()


@app.delete("/api/watchlist/{item_id}")
def delete_watchlist(item_id: int):
    db.remove_watchlist(item_id)
    return db.list_watchlist()


@app.get("/api/watchlist/scan")
async def scan_watchlist():
    items = db.list_watchlist()

    async def run_one(item: dict):
        try:
            result = await asyncio.to_thread(analyze, item["symbol"], item["exchange"], item["timeframe"])
        except Exception as exc:
            return {"symbol": item["symbol"], "exchange": item["exchange"], "timeframe": item["timeframe"], "error": str(exc)}
        result["watchlist_id"] = item["id"]
        return result

    return await asyncio.gather(*(run_one(item) for item in items))


@app.get("/api/health")
def health():
    return {"status": "ok"}
