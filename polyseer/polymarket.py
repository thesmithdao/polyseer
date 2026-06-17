"""Public Polymarket Gamma API client (read-only, no auth).

Base URL: https://gamma-api.polymarket.com

Quirk: Gamma double-encodes `outcomes`, `outcomePrices` and `clobTokenIds` as
JSON *strings* inside the JSON response. We parse defensively.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx

GAMMA_BASE = "https://gamma-api.polymarket.com"
_TIMEOUT = httpx.Timeout(20.0)

# Tiny in-process TTL cache (speed + rate-limit protection under bursty load).
_CACHE: dict[str, tuple[float, object]] = {}


def _cache_get(key: str, ttl: float):
    hit = _CACHE.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    return None


def _cache_set(key: str, value) -> None:
    _CACHE[key] = (time.monotonic(), value)


@dataclass
class Market:
    question: str
    outcomes: list[tuple[str, float]]  # (label, implied_probability)
    slug: str = ""
    event_title: str = ""
    group_title: str = ""  # candidate name in a multi-outcome event (e.g. a team)
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
    def label(self) -> str:
        """The specific market identity (candidate name / question), not the event."""
        return self.group_title or self.question or self.event_title

    @property
    def top_outcome(self) -> tuple[str, float] | None:
        return max(self.outcomes, key=lambda o: o[1]) if self.outcomes else None

    @property
    def yes_prob(self) -> float:
        for label, p in self.outcomes:
            if label.strip().lower() == "yes":
                return p
        return self.outcomes[0][1] if self.outcomes else 0.0


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
        group_title=str(raw.get("groupItemTitle") or ""),
        volume=_to_float(raw.get("volumeNum") or raw.get("volume")),
        volume24h=_to_float(raw.get("volume24hr")),
        liquidity=_to_float(raw.get("liquidityNum") or raw.get("liquidity")),
        end_date=str(raw.get("endDate") or raw.get("endDateIso") or ""),
        active=bool(raw.get("active", True)),
        closed=bool(raw.get("closed", False)),
    )


async def _public_search(query: str) -> list[dict]:
    """Raw Gamma /public-search → list of event dicts (cached 30s)."""
    key = f"psearch:{query}"
    cached = _cache_get(key, 30)
    if cached is not None:
        return cached  # type: ignore[return-value]
    params = {"q": query, "limit_per_type": 12, "events_status": "active"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(f"{GAMMA_BASE}/public-search", params=params)
        resp.raise_for_status()
        data = resp.json()
    events = data.get("events", []) if isinstance(data, dict) else []
    _cache_set(key, events)
    return events


async def search_markets(query: str, limit: int = 8) -> list[Market]:
    """Keyword search → most relevant live markets (relevance order preserved)."""
    events = await _public_search(query)
    markets: list[Market] = []
    for event in events:
        title = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, event_title=title)
            if m and not m.closed:
                markets.append(m)
    return markets[:limit]


async def search_events(query: str, limit: int = 6) -> list[tuple[str, list[Market]]]:
    """Search → events with their (open) markets, relevance order preserved.

    Used for multi-outcome events (e.g. 'World Cup Winner' → one market per team).
    """
    events = await _public_search(query)
    out: list[tuple[str, list[Market]]] = []
    for event in events:
        title = str(event.get("title") or "")
        mkts = [m for raw in (event.get("markets") or [])
                if (m := _parse_market(raw, title)) and not m.closed]
        if mkts:
            out.append((title, mkts))
        if len(out) >= limit:
            break
    return out


async def trending_markets(limit: int = 8) -> list[Market]:
    """Top active markets by 24h volume via Gamma /events (cached 60s)."""
    key = f"trending:{limit}"
    cached = _cache_get(key, 60)
    if cached is not None:
        return cached  # type: ignore[return-value]
    params = {
        "closed": "false", "active": "true", "archived": "false",
        "order": "volume24hr", "ascending": "false", "limit": limit,
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
    _cache_set(key, out)
    return out
