"""Public Polymarket Gamma API client.

Gamma is read-only and requires no authentication.
Base URL: https://gamma-api.polymarket.com

Important quirk: the Gamma API double-encodes `outcomes`, `outcomePrices` and
`clobTokenIds` as JSON *strings* inside the JSON response (e.g. the value of
`outcomePrices` is the literal string '["0.62", "0.38"]', not an array). We parse
defensively so the client keeps working if Polymarket ever returns real arrays.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx

GAMMA_BASE = "https://gamma-api.polymarket.com"
_TIMEOUT = httpx.Timeout(20.0)


@dataclass
class Market:
    question: str
    outcomes: list[tuple[str, float]]  # (label, implied_probability) pairs
    slug: str = ""
    event_title: str = ""
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    active: bool = True
    closed: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://polymarket.com/event/{self.slug}" if self.slug else "https://polymarket.com"


def _maybe_json(value):
    """Gamma returns outcomes / outcomePrices as JSON-encoded strings. Decode if needed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return []
    return value or []


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_market(raw: dict, event_title: str = "") -> Market | None:
    labels = _maybe_json(raw.get("outcomes"))
    prices = _maybe_json(raw.get("outcomePrices"))
    if not labels or not prices or len(labels) != len(prices):
        return None
    outcomes = [(str(lbl), _to_float(p)) for lbl, p in zip(labels, prices)]
    return Market(
        question=str(raw.get("question") or raw.get("title") or event_title or "Untitled market"),
        outcomes=outcomes,
        slug=str(raw.get("slug") or raw.get("eventSlug") or ""),
        event_title=event_title,
        volume=_to_float(raw.get("volumeNum") or raw.get("volume")),
        liquidity=_to_float(raw.get("liquidityNum") or raw.get("liquidity")),
        end_date=str(raw.get("endDate") or raw.get("endDateIso") or ""),
        active=bool(raw.get("active", True)),
        closed=bool(raw.get("closed", False)),
    )


async def search_markets(query: str, limit: int = 6) -> list[Market]:
    """Search Polymarket for markets relevant to a natural-language question.

    Uses the Gamma `/public-search` endpoint, which returns events (each carrying
    one or more markets). We flatten to markets, drop closed ones, and keep the
    most liquid `limit` results.
    """
    params = {"q": query, "limit_per_type": 12, "events_status": "active"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{GAMMA_BASE}/public-search", params=params)
        resp.raise_for_status()
        data = resp.json()

    events = data.get("events", []) if isinstance(data, dict) else []
    markets: list[Market] = []
    for event in events:
        title = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, event_title=title)
            if m and not m.closed:
                markets.append(m)

    markets.sort(key=lambda m: m.liquidity, reverse=True)
    return markets[:limit]
