"""Core analysis: pulls technicals, multi-timeframe confluence, candle
strength, news, and Reddit sentiment from the tradingview-mcp engine, then
asks Claude to synthesize all of it into one verdict. Results are cached and
every call is logged for track-record scoring.
"""
from __future__ import annotations

import json
import logging
import os
import time

from anthropic import Anthropic
from tradingview_mcp.core.services.news_service import fetch_news
from tradingview_mcp.core.services.screener_service import (
    analyze_coin,
    calculate_candle_pattern_score,
    run_multi_timeframe_analysis,
)
from tradingview_mcp.core.services.sentiment_service import analyze_sentiment
from tradingview_mcp.core.utils.validators import normalize_tradingview_symbol

from lewtrade import db
from lewtrade.symbols import resolve

log = logging.getLogger("lewtrade.engine")

_client: Anthropic | None = None
CACHE_TTL_S = 180  # repeated requests for the same symbol/timeframe within 3 min reuse the result


def _anthropic() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


VERDICT_TOOL = {
    "name": "emit_verdict",
    "description": "Emit the synthesized trading call.",
    "input_schema": {
        "type": "object",
        "properties": {
            "call": {"type": "string", "enum": ["STRONG_SELL", "SELL", "NEUTRAL", "BUY", "STRONG_BUY"]},
            "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
            "gauge": {"type": "integer", "minimum": 0, "maximum": 100, "description": "0=strong sell, 50=neutral, 100=strong buy"},
            "trend_label": {"type": "string", "description": "Short human trend read, e.g. 'Uptrend, pulling back to support'"},
            "bullets": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4},
            "what_flips_it": {"type": "string", "description": "The catalyst/level that would invalidate this call"},
        },
        "required": ["call", "confidence", "gauge", "trend_label", "bullets", "what_flips_it"],
    },
}


def get_current_price(symbol: str, exchange: str, timeframe: str = "1h") -> float | None:
    """Lightweight price-only fetch, used by the track-record resolver — no
    news/sentiment/Claude call needed just to check where price ended up."""
    technical = analyze_coin(symbol, exchange, timeframe)
    if "error" in technical:
        return None
    return technical["price_data"]["current_price"]


def _candle_score(technical: dict) -> dict:
    """Momentum/strength score for the current candle, derived from data
    analyze_coin already fetched — no extra network call. Not classic
    pattern recognition (pin bar / inside bar need multi-candle OHLC history
    the snapshot API doesn't expose) — this scores body size, momentum,
    volume, and RSI/trend alignment on the current bar.
    """
    price = technical["price_data"]
    synthetic_indicators = {
        "open": price.get("open"),
        "close": price.get("close"),
        "high": price.get("high"),
        "low": price.get("low"),
        "volume": price.get("volume"),
        "RSI": (technical.get("rsi") or {}).get("value"),
        "EMA50": (technical.get("ema") or {}).get("ema50"),
    }
    if not all([synthetic_indicators["open"], synthetic_indicators["close"],
                synthetic_indicators["high"], synthetic_indicators["low"]]):
        return {"detected": False, "score": 0}
    return calculate_candle_pattern_score(synthetic_indicators, pattern_length=1, min_increase=1.0)


def _multi_timeframe(norm_symbol: str, exchange: str) -> dict | None:
    try:
        full_symbol = normalize_tradingview_symbol(norm_symbol, exchange)
        result = run_multi_timeframe_analysis(full_symbol, exchange)
        if "error" in result:
            return None
        return {
            "alignment": result["alignment"]["status"],
            "net_score": result["alignment"]["net_score"],
            "divergent_timeframes": result["alignment"]["divergent_timeframes"],
            "recommendation": result["recommendation"]["action"],
            "per_timeframe": {
                tf: {"bias": d.get("bias"), "trend_strength": d.get("trend_strength")}
                for tf, d in result["timeframes"].items() if "error" not in d
            },
        }
    except Exception:
        log.exception("multi-timeframe analysis failed for %s", norm_symbol)
        return None


def _sentiment(keyword: str, category: str) -> dict | None:
    try:
        sentiment_category = "crypto" if category == "crypto" else "stocks"
        result = analyze_sentiment(keyword, sentiment_category, 8)
        if "error" in result:
            return None
        return result
    except Exception:
        log.exception("sentiment fetch failed for %s", keyword)
        return None


def analyze(symbol: str, exchange_override: str | None = None, timeframe: str = "1h", use_cache: bool = True) -> dict:
    norm_symbol, exchange, keyword, category = resolve(symbol, exchange_override)
    cache_key = f"{norm_symbol}:{exchange}:{timeframe}"

    if use_cache:
        cached = db.cache_get(cache_key, CACHE_TTL_S)
        if cached:
            return {**cached, "cached": True}

    technical = analyze_coin(norm_symbol, exchange, timeframe)
    if "error" in technical:
        return {"error": technical["error"], "symbol": norm_symbol, "exchange": exchange}

    news_items = fetch_news(symbol=keyword, category=category, limit=6)
    if len(news_items) < 3:
        seen_titles = {n["title"] for n in news_items}
        general = fetch_news(symbol=None, category=category, limit=6)
        news_items += [n for n in general if n["title"] not in seen_titles]

    candle = _candle_score(technical)
    mtf = _multi_timeframe(norm_symbol, exchange)
    sentiment = _sentiment(keyword, category)

    verdict = _synthesize(norm_symbol, timeframe, technical, news_items, candle, mtf, sentiment)

    result = {
        "symbol": norm_symbol,
        "exchange": exchange,
        "timeframe": timeframe,
        "price": technical["price_data"],
        "market_structure": technical["market_structure"],
        "support_resistance": technical["support_resistance"],
        "market_sentiment": technical["market_sentiment"],
        "volume_analysis": technical.get("volume_analysis"),
        "candle_score": candle,
        "multi_timeframe": mtf,
        "social_sentiment": sentiment,
        "news": news_items,
        "verdict": verdict,
        "cached": False,
    }

    db.cache_set(cache_key, result)
    db.log_call(norm_symbol, exchange, timeframe, technical["price_data"]["current_price"], verdict)

    return result


def _synthesize(symbol: str, timeframe: str, technical: dict, news_items: list[dict],
                 candle: dict, mtf: dict | None, sentiment: dict | None) -> dict:
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": technical["price_data"],
        "market_structure": technical["market_structure"],
        "support_resistance": technical["support_resistance"],
        "market_sentiment": technical["market_sentiment"],
        "volume_analysis": technical.get("volume_analysis"),
        "obv": technical.get("obv"),
        "rsi": technical.get("rsi"),
        "macd": technical.get("macd"),
        "adx": technical.get("adx"),
        "candle_strength_score": candle,
        "multi_timeframe_confluence": mtf,
        "reddit_sentiment": sentiment,
        "headlines": [{"title": n["title"], "summary": n["summary"]} for n in news_items[:6]],
    }

    message = _anthropic().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        tools=[VERDICT_TOOL],
        tool_choice={"type": "tool", "name": "emit_verdict"},
        messages=[{
            "role": "user",
            "content": (
                "You're a technical analyst combining chart data, multi-timeframe confluence, volume, "
                "candle strength, Reddit sentiment, and news for a trading signal tool. "
                "Trend and support/resistance are derived directly from indicators (treat as ground truth). "
                "multi_timeframe_confluence tells you whether higher timeframes agree with this timeframe's read — "
                "weight divergence heavily (a 1h buy against a bearish daily/weekly is a much weaker call). "
                "Weigh the news headlines and reddit_sentiment for how much they'd move price and whether they "
                "confirm or contradict the technical picture; ignore anything irrelevant to the symbol. "
                "Be decisive and concrete, not hedgy — this is a quick-read signal card, not a report. "
                "Only cite numeric figures that appear in the Data JSON below — never invent or estimate a "
                "statistic that isn't given to you.\n\n"
                f"Data:\n{json.dumps(payload, default=str)}"
            ),
        }],
    )

    for block in message.content:
        if block.type == "tool_use" and block.name == "emit_verdict":
            return block.input

    return {
        "call": "NEUTRAL",
        "confidence": "Low",
        "gauge": 50,
        "trend_label": "Unable to synthesize",
        "bullets": ["Model did not return a structured verdict."],
        "what_flips_it": "N/A",
    }
