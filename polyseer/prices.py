"""Live crypto spot prices from Binance public market data (no auth).

Uses the `data-api.binance.vision` host, which serves public market data and is
NOT geo-blocked like `api.binance.com` (which returns 451 from US IPs / Railway).
Gives last price + 24h change% + high/low — used to ground crypto forecasts in
where the price actually is right now.
"""

from __future__ import annotations

import time

import httpx

_BINANCE = "https://data-api.binance.vision/api/v3/ticker/24hr"
_TIMEOUT = httpx.Timeout(10.0)
_CACHE: dict[str, tuple[float, dict | None]] = {}


async def crypto_spot(ticker: str) -> dict | None:
    """Live 24h ticker for a crypto symbol (e.g. 'BTC'). Returns None if unavailable.

    Cached 20s. Quotes against USDT.
    """
    sym = (ticker or "").strip().upper().replace("USDT", "")
    if not sym:
        return None
    pair = f"{sym}USDT"

    hit = _CACHE.get(pair)
    if hit and time.monotonic() - hit[0] < 20:
        return hit[1]

    result: dict | None = None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_BINANCE, params={"symbol": pair})
        if resp.status_code == 200:
            d = resp.json()
            result = {
                "symbol": sym,
                "price": float(d["lastPrice"]),
                "change24h": float(d["priceChangePercent"]),
                "high24h": float(d["highPrice"]),
                "low24h": float(d["lowPrice"]),
            }
    except Exception:
        result = None

    _CACHE[pair] = (time.monotonic(), result)
    return result
