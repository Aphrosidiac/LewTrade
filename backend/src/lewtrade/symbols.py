"""Symbol -> (exchange, news keyword, category) resolution.

Kept as a small lookup + heuristic fallback rather than a full instrument
database — this is the "basic" version, symbols not covered here still work,
they just default to a generic exchange guess and the raw symbol as the news
keyword.
"""
from __future__ import annotations

# symbol -> (default exchange, news search keyword, news category)
KNOWN_SYMBOLS: dict[str, tuple[str, str, str]] = {
    "XAUUSD": ("OANDA", "gold", "stocks"),
    "XAGUSD": ("OANDA", "silver", "stocks"),
    "EURUSD": ("OANDA", "euro", "stocks"),
    "GBPUSD": ("OANDA", "pound", "stocks"),
    "USDJPY": ("OANDA", "yen", "stocks"),
    "AUDUSD": ("OANDA", "aussie dollar", "stocks"),
    "USDCAD": ("OANDA", "canadian dollar", "stocks"),
    "NZDUSD": ("OANDA", "kiwi dollar", "stocks"),
    "USDCHF": ("OANDA", "swiss franc", "stocks"),
    "BTCUSDT": ("KUCOIN", "bitcoin", "crypto"),
    "ETHUSDT": ("KUCOIN", "ethereum", "crypto"),
    "SOLUSDT": ("KUCOIN", "solana", "crypto"),
    "AAPL": ("NASDAQ", "Apple", "stocks"),
    "TSLA": ("NASDAQ", "Tesla", "stocks"),
    "MSFT": ("NASDAQ", "Microsoft", "stocks"),
    "NVDA": ("NASDAQ", "Nvidia", "stocks"),
}

_FOREX_PAIR = {"EUR", "GBP", "USD", "JPY", "AUD", "CAD", "NZD", "CHF", "XAU", "XAG"}


def resolve(symbol: str, exchange_override: str | None = None) -> tuple[str, str, str, str]:
    """Returns (normalized_symbol, exchange, news_keyword, news_category)."""
    sym = symbol.upper().strip()

    if sym in KNOWN_SYMBOLS:
        exchange, keyword, category = KNOWN_SYMBOLS[sym]
        return sym, (exchange_override or exchange), keyword, category

    if exchange_override:
        return sym, exchange_override.upper(), sym, "all"

    if len(sym) == 6 and sym[:3] in _FOREX_PAIR and sym[3:] in _FOREX_PAIR:
        return sym, "OANDA", sym, "stocks"

    if sym.endswith(("USDT", "USDC", "BUSD")):
        return sym, "KUCOIN", sym.replace("USDT", "").replace("USDC", "").replace("BUSD", ""), "crypto"

    return sym, "NASDAQ", sym, "stocks"
