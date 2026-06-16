"""Polyseer — Agentverse HOSTED agent (single file).

Copy-paste into a Blank Agent in the Agentverse editor (https://agentverse.ai).
Uses only hosted-runtime imports: uagents, uagents_core, requests, stdlib.
Set your key as an Agent Secret (e.g. ASI_ONE_API_KEY). Informational only.
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import requests

# uagents (<=0.25) calls asyncio.get_event_loop() while constructing the Agent,
# which raises on Python 3.14+ when no loop is running. Ensure one exists.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

GAMMA_BASE = "https://gamma-api.polymarket.com"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "asi1").strip().lower()  # asi1 | anthropic | openai
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY", "")
ASI_ONE_MODEL = os.getenv("ASI_ONE_MODEL", "asi1-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are Polyseer, a calibrated forecasting agent for Polymarket.

Answer probabilistic questions with a single well-calibrated probability and short,
transparent reasoning, anchored on live prediction-market prices.

Rules:
- Treat market prices as your strongest prior — money-weighted crowd estimates.
- If markets don't exactly match the question, say so and reason about the gap.
- Give ONE headline probability as a percentage, then 2-4 concise bullets.
- Never invent markets or prices. Informational only — not financial advice.

Format exactly:
**Estimate: ~NN%**
- bullet
- bullet
(Do not add a sources section — it is appended automatically.)"""

_TRENDING_KEYS = ("trending", "hottest", "hot market", "biggest market", "top market",
                  "most popular", "most active", "highest volume", "what's popular")
_DISCOVERY_KEYS = ("find market", "search market", "list market", "markets about",
                   "show me market", "which markets", "what markets")


# ── Polymarket (public Gamma API) ──────────────────────────────────────
def _maybe_json(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (ValueError, TypeError):
            return []
    return v or []


def _to_float(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _parse_market(raw, event_title=""):
    labels = _maybe_json(raw.get("outcomes"))
    prices = _maybe_json(raw.get("outcomePrices"))
    if not labels or not prices or len(labels) != len(prices):
        return None
    slug = str(raw.get("slug") or raw.get("eventSlug") or "")
    title = str(raw.get("question") or raw.get("title") or event_title or "Untitled market")
    return {
        "title": event_title or title,
        "outcomes": [(str(lbl), _to_float(p)) for lbl, p in zip(labels, prices)],
        "url": f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com",
        "slug": slug,
        "liquidity": _to_float(raw.get("liquidityNum") or raw.get("liquidity")),
        "volume24h": _to_float(raw.get("volume24hr")),
        "end_date": str(raw.get("endDate") or raw.get("endDateIso") or ""),
        "closed": bool(raw.get("closed", False)),
    }


def search_markets(query, limit=6):
    resp = requests.get(
        f"{GAMMA_BASE}/public-search",
        params={"q": query, "limit_per_type": 12, "events_status": "active"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    events = data.get("events", []) if isinstance(data, dict) else []
    markets = []
    for event in events:
        et = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, et)
            if m and not m["closed"]:
                markets.append(m)
    markets.sort(key=lambda m: m["liquidity"], reverse=True)
    return markets[:limit]


def trending_markets(limit=8):
    resp = requests.get(
        f"{GAMMA_BASE}/events",
        params={"closed": "false", "active": "true", "archived": "false",
                "order": "volume24hr", "ascending": "false", "limit": limit},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    events = data if isinstance(data, list) else data.get("data", []) or []
    out = []
    for event in events:
        et = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, et)
            if m and not m["closed"]:
                m["slug"] = str(event.get("slug") or m["slug"])
                m["url"] = f"https://polymarket.com/event/{m['slug']}" if m["slug"] else m["url"]
                m["volume24h"] = _to_float(event.get("volume24hr")) or m["volume24h"]
                out.append(m)
                break
        if len(out) >= limit:
            break
    return out


# ── LLM (raw HTTP — hosted runtime has no SDKs) ────────────────────────
def call_llm(system, user):
    if LLM_PROVIDER == "anthropic":
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": ANTHROPIC_MODEL, "max_tokens": 3000, "thinking": {"type": "adaptive"},
                  "system": system, "messages": [{"role": "user", "content": user}]},
            timeout=90,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()

    if LLM_PROVIDER == "openai":
        base, key, model = "https://api.openai.com/v1", OPENAI_API_KEY, OPENAI_MODEL
    else:
        base, key, model = "https://api.asi1.ai/v1", ASI_ONE_API_KEY, ASI_ONE_MODEL
    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": 0.2, "max_tokens": 1200,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── Routing ────────────────────────────────────────────────────────────
def _sources(markets):
    if not markets:
        return ""
    seen, links = set(), []
    for m in markets:
        if m["url"] in seen:
            continue
        seen.add(m["url"])
        links.append(f"- [{m['title']}]({m['url']})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


def answer(question):
    q = question.lower()
    if any(k in q for k in _TRENDING_KEYS):
        markets = trending_markets(8)
        if not markets:
            return "I couldn't find any active markets right now."
        lines = ["**🔥 Trending Polymarket markets (by 24h volume):**"]
        for i, m in enumerate(markets, 1):
            top = max(m["outcomes"], key=lambda o: o[1]) if m["outcomes"] else None
            tag = f" — {top[0]} {top[1]:.0%}" if top else ""
            vol = f" (${m['volume24h']:,.0f} 24h)" if m["volume24h"] else ""
            lines.append(f"{i}. [{m['title']}]({m['url']}){tag}{vol}")
        return "\n".join(lines)

    if any(k in q for k in _DISCOVERY_KEYS):
        markets = search_markets(question, 8)
        if not markets:
            return "I couldn't find live markets matching that."
        lines = ["**Matching Polymarket markets:**"]
        for m in markets:
            outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m["outcomes"])
            lines.append(f"- [{m['title']}]({m['url']}): {outcomes}")
        return "\n".join(lines)

    markets = search_markets(question, 6)
    if markets:
        rendered = "\n".join(
            f"- {m['title']}: " + ", ".join(f"{l} {p:.0%}" for l, p in m["outcomes"]) for m in markets
        )
        context = "Relevant live Polymarket markets and implied probabilities:\n" + rendered
    else:
        context = "No relevant live Polymarket markets were found."
    user = f"Question: {question}\n\n{context}\n\nGive your calibrated estimate now."
    return call_llm(SYSTEM_PROMPT, user) + _sources(markets)


# ── Agent ──────────────────────────────────────────────────────────────
agent = Agent()
chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )
    question = " ".join(item.text for item in msg.content if isinstance(item, TextContent)).strip()
    if not question:
        return
    ctx.logger.info(f"Question from {sender}: {question}")
    try:
        reply = answer(question)
    except Exception as exc:
        ctx.logger.exception("handler failed")
        reply = f"Sorry — I couldn't answer that right now ({exc})."
    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=reply), EndSessionContent(type="end-session")],
        ),
    )


@chat.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"Ack from {sender} for {msg.acknowledged_msg_id}")


agent.include(chat, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
