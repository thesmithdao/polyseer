"""Oracle of Odds — Agentverse HOSTED agent (single file).

Copy-paste this whole file into a Blank Agent in the Agentverse editor
(https://agentverse.ai → New Agent → Blank Agent). It runs in ASI cloud,
auto-registers in the Almanac/marketplace, and is discoverable from ASI:One.

It uses ONLY imports available in the Agentverse hosted runtime:
    uagents, uagents_core, requests, and the Python standard library.
(That's why the LLM and Polymarket calls use `requests` directly rather than the
openai/anthropic/httpx SDKs — those aren't in the hosted allowlist.)

Set your key(s) as Agent Secrets in the Agentverse UI:
    ASI_ONE_API_KEY   (default backend)
  optionally: LLM_PROVIDER, ANTHROPIC_API_KEY, OPENAI_API_KEY, model overrides.

Informational analysis only — not financial advice.
"""

import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import requests
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

GAMMA_BASE = "https://gamma-api.polymarket.com"

# ── LLM config (set these as Agent Secrets in Agentverse) ──────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "asi1").strip().lower()  # asi1 | anthropic | openai
ASI_ONE_API_KEY = os.getenv("ASI_ONE_API_KEY", "")
ASI_ONE_MODEL = os.getenv("ASI_ONE_MODEL", "asi1-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM_PROMPT = """You are Oracle of Odds, a calibrated forecasting agent.

You answer probabilistic questions ("what are the odds X happens?") with a single
well-calibrated probability and short, transparent reasoning.

Rules:
- Treat live prediction-market prices as your strongest prior — they are crowd-
  sourced, money-weighted estimates. Anchor on them.
- If the markets don't exactly match the user's question, say so and reason about
  the gap rather than pretending they do.
- Give ONE headline probability as a percentage, then 2-4 concise bullets of
  reasoning. Be explicit about uncertainty and what would move the number.
- Never invent markets, prices, or facts. If you have no relevant market data,
  say the estimate is low-confidence and explain why.
- Do not give financial advice. This is informational analysis only.

Format exactly:
**Estimate: ~NN%**
- bullet
- bullet
(Do not add a sources section — it is appended automatically.)"""


# ── Polymarket (public Gamma API, no auth) ─────────────────────────────
def _maybe_json(value):
    """Gamma double-encodes outcomes/outcomePrices as JSON strings — decode if needed."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return []
    return value or []


def _to_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_market(raw, event_title=""):
    labels = _maybe_json(raw.get("outcomes"))
    prices = _maybe_json(raw.get("outcomePrices"))
    if not labels or not prices or len(labels) != len(prices):
        return None
    slug = str(raw.get("slug") or raw.get("eventSlug") or "")
    return {
        "question": str(raw.get("question") or raw.get("title") or event_title or "Untitled market"),
        "outcomes": [(str(lbl), _to_float(p)) for lbl, p in zip(labels, prices)],
        "slug": slug,
        "url": f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com",
        "volume": _to_float(raw.get("volumeNum") or raw.get("volume")),
        "liquidity": _to_float(raw.get("liquidityNum") or raw.get("liquidity")),
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
        title = str(event.get("title") or "")
        for raw in event.get("markets", []) or []:
            m = _parse_market(raw, title)
            if m and not m["closed"]:
                markets.append(m)
    markets.sort(key=lambda m: m["liquidity"], reverse=True)
    return markets[:limit]


def _render_markets(markets):
    lines = []
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m["outcomes"])
        meta = []
        if m["end_date"]:
            meta.append(f"ends {m['end_date'][:10]}")
        if m["liquidity"]:
            meta.append(f"liquidity ${m['liquidity']:,.0f}")
        if m["volume"]:
            meta.append(f"volume ${m['volume']:,.0f}")
        suffix = f" ({'; '.join(meta)})" if meta else ""
        lines.append(f"- {m['question']}: {outcomes}{suffix}")
    return "\n".join(lines)


def _sources(markets):
    if not markets:
        return ""
    seen, links = set(), []
    for m in markets:
        if m["url"] in seen:
            continue
        seen.add(m["url"])
        links.append(f"- [{m['question']}]({m['url']})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


# ── LLM (raw HTTP — hosted runtime has no SDKs) ────────────────────────
def call_llm(system, user):
    if LLM_PROVIDER == "anthropic":
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 3000,
                "thinking": {"type": "adaptive"},
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            timeout=90,
        )
        resp.raise_for_status()
        blocks = resp.json().get("content", [])
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()

    if LLM_PROVIDER == "openai":
        base, key, model = "https://api.openai.com/v1", OPENAI_API_KEY, OPENAI_MODEL
    else:  # default: ASI:One (OpenAI-compatible)
        base, key, model = "https://api.asi1.ai/v1", ASI_ONE_API_KEY, ASI_ONE_MODEL

    resp = requests.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def forecast(question):
    markets = search_markets(question, limit=6)
    if markets:
        context = "Relevant live Polymarket markets and their implied probabilities:\n" + _render_markets(markets)
    else:
        context = "No relevant live Polymarket markets were found for this question."
    user_prompt = f"Question: {question}\n\n{context}\n\nGive your calibrated estimate now."
    return call_llm(SYSTEM_PROMPT, user_prompt) + _sources(markets)


# ── Agent ──────────────────────────────────────────────────────────────
# On hosted Agentverse, identity (name/seed/address) is managed by the platform.
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
        answer = forecast(question)
    except Exception as exc:
        ctx.logger.exception("forecast failed")
        answer = f"Sorry — I couldn't compute the odds right now ({exc})."
    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=answer), EndSessionContent(type="end-session")],
        ),
    )


@chat.on_message(ChatAcknowledgement)
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.debug(f"Ack from {sender} for {msg.acknowledged_msg_id}")


agent.include(chat, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
