"""Intent routing: clean the question, retrieve Polymarket data, answer.

Keyword routing (no extra classification call). Each path extracts clean search
keywords first, and follow-ups resolve against the previous topic (memory).
Returns (answer, topic) so the agent can remember the topic per user.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .llm import plan, synthesize
from .polymarket import Market, search_events, search_markets, trending_markets

SYSTEM_PROMPT = """You are Polyseer, a sharp prediction-market analyst. You read live Polymarket
markets and give a calibrated, conversational read — like a smart analyst, not a disclaimer bot.

You get a question and the live markets retrieved for it. Decide which market (if any) genuinely
informs the question, then answer in flowing prose:

- Lead with the headline probability in bold (e.g. **~72%**) and, in the same sentence, what it
  means in plain words.
- Then 1-3 fluid sentences interpreting it: what's driving the number, what the crowd is really
  saying, and what would move it — weaving the market's name and price in naturally.
- If you lean on a proxy or a slightly different timeframe/threshold, say so confidently in one
  clause (e.g. "no direct market on X, but the closest signal — Y at NN% — implies…") — and only
  use a proxy that genuinely informs the question.

If nothing retrieved is genuinely relevant, don't force a number: say there's no good market yet,
name the closest if any, and suggest a sharper query or "trending markets".

Style: confident, concise, calibrated — give a real take, not a pile of caveats. Flowing prose
(2-4 sentences), never bullet fragments. Plain text only — write "$100k" plainly, no LaTeX. Never
fabricate markets or prices, and never price something off a clearly unrelated market.
Informational only — not financial advice. Do not write a sources section; it is appended
automatically."""

_MENTION = re.compile(r"@[A-Za-z0-9_]+")


def _clean(text: str) -> str:
    return _MENTION.sub("", text).strip()


async def handle(question: str, prev_topic: str | None = None) -> tuple[str, str | None]:
    """Dynamically plan (intent + query) via the LLM, then dispatch — no keyword rules."""
    q = _clean(question)
    p = await plan(q, prev_topic)
    intent, query = p["intent"], p["query"]
    if intent == "trending":
        return await _trending(), prev_topic
    if intent == "ranked":
        return await _ranked(q, query)
    if intent == "discovery":
        return await _discovery(query)
    return await _answer(q, query)


async def _trending(limit: int = 8) -> str:
    markets = await trending_markets(limit)
    if not markets:
        return "I couldn't find any active markets right now."
    lines = ["**🔥 Trending Polymarket markets (by 24h volume):**"]
    for i, m in enumerate(markets, 1):
        top = m.top_outcome
        tag = f" — {top[0]} {top[1]:.0%}" if top else ""
        vol = f" (${m.volume24h:,.0f} 24h)" if m.volume24h else ""
        lines.append(f"{i}. [{m.title}]({m.url}){tag}{vol}")
    return "\n".join(lines)


async def _ranked(question: str, query: str) -> tuple[str, str | None]:
    """Multi-outcome events: 'who will win X' -> ranked candidate list."""
    events = await search_events(query, 6)
    chosen = next(((t, m) for t, m in events if len(m) >= 3), None)
    if not chosen:  # not a multi-outcome event — fall back to a normal estimate
        return await _answer(question, query)
    title, markets = chosen
    ranked = sorted(markets, key=lambda m: m.yes_prob, reverse=True)[:10]
    lines = [f"**{title} — current Polymarket odds:**"]
    for m in ranked:
        lines.append(f"- {m.label}: {m.yes_prob:.0%}")
    lines.append(f"\n[View on Polymarket]({ranked[0].url})")
    return "\n".join(lines), query


async def _discovery(query: str) -> tuple[str, str | None]:
    markets = await search_markets(query, 8)
    if not markets:
        return (f'I couldn\'t find live Polymarket markets matching "{query}". '
                'Try a more specific subject, or ask "trending markets".'), query
    lines = [f'**Polymarket markets matching "{query}":**']
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes[:4])
        lines.append(f"- [{m.label}]({m.url}): {outcomes}")
    return "\n".join(lines), query


async def _answer(question: str, query: str) -> tuple[str, str | None]:
    markets = await search_markets(query, 8)
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    if markets:
        context = "Live Polymarket markets retrieved for this question:\n" + _render(markets)
    else:
        context = "No live Polymarket markets were retrieved for this question."
    user = (
        f"Today is {today}.\n"
        f"User question: {question}\n"
        f'Search keywords used: "{query}"\n\n'
        f"{context}\n\n"
        "Answer per your rules."
    )
    answer = await synthesize(SYSTEM_PROMPT, user)
    _neg = ("no good market", "no matching market", "no direct market", "no relevant market",
            "no market", "couldn't find", "could not find")
    if markets and not any(p in answer.lower() for p in _neg):
        answer += _sources(markets)
    return answer, query


def _render(markets: list[Market]) -> str:
    out = []
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes[:4])
        meta = []
        if m.end_date:
            meta.append(f"ends {m.end_date[:10]}")
        if m.liquidity:
            meta.append(f"liquidity ${m.liquidity:,.0f}")
        suffix = f" ({'; '.join(meta)})" if meta else ""
        out.append(f"- {m.label}: {outcomes}{suffix}")
    return "\n".join(out)


def _sources(markets: list[Market]) -> str:
    seen, links = set(), []
    for m in markets:
        if m.url in seen:
            continue
        seen.add(m.url)
        links.append(f"- [{m.label}]({m.url})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


if __name__ == "__main__":  # local test: python -m polyseer.router "who will win the world cup?"
    import asyncio
    import sys

    q = " ".join(sys.argv[1:]) or "What are the odds the Fed cuts rates in July?"
    ans, _ = asyncio.run(handle(q))
    print(ans)
