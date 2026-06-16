"""Public Polymarket Gamma API client (read-only, no auth).

Base URL: https://gamma-api.polymarket.com

Quirk: Gamma double-encodes `outcomes`, `outcomePrices` and `clobTokenIds` as
JSON *strings* inside the JSON response. We parse defensively so the client keeps
working if Polymarket ever returns real arrays.
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
    outcomes: list[tuple[str, float]]  # (label, implied_probability)
    slug: str = ""
    event_title: str = ""
    volume: float = 0.0
    volume24h: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    active: bool = True
    closed: bool = False
    tags: list[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://polymarket.com/event/{self.slug}" if self.slug else "https://polymarket.com"

    @property
    def title(self) -> str:
        return self.event_title or self.question

    @property
    def top_outcome(self) -> tuple[str, float] | None:
        return max(self.outcomes, key=lambda o: o[1]) if self.outcomes else None


def _maybe_json(value):
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
    return Market(
        question=str(raw.get("question") or raw.get("title") or event_title or "Untitled market"),
        outcomes=[(str(lbl), _to_float(p)) for lbl, p in zip(labels, prices)],
        slug=str(raw.get("slug") or raw.get("eventSlug") or ""),
        event_title=event_title,
        volume=_to_float(raw.get("volumeNum") or raw.get("volume")),
        volume24h=_to_float(raw.get("volume24hr")),
        liquidity=_to_float(raw.get("liquidityNum") or raw.get("liquidity")),
        end_date=str(raw.get("endDate") or raw.get("endDateIso") or ""),
        active=bool(raw.get("active", True)),
        closed=bool(raw.get("closed", False)),
    )


async def search_markets(query: str, limit: int = 6) -> list[Market]:
    """Keyword search via Gamma /public-search; returns the most liquid markets."""
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


async def trending_markets(limit: int = 8) -> list[Market]:
    """Top active markets by 24h volume via Gamma /events."""
    params = {
        "closed": "false",
        "active": "true",
        "archived": "false",
        "order": "volume24hr",
        "ascending": "false",
        "limit": limit,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{GAMMA_BASE}/events", params=params)
        resp.raise_for_status()
        data = resp.json()

    events = data if isinstance(data, list) else data.get("data", []) or []
    out: list[Market] = []
    for event in events:
        title = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, event_title=title)
            if m and not m.closed:
                m.slug = str(event.get("slug") or m.slug)
                m.volume24h = _to_float(event.get("volume24hr")) or m.volume24h
                out.append(m)
                break  # one representative market per event
        if len(out) >= limit:
            break
    return out
