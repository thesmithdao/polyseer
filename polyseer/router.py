"""Intent routing: clean the question, retrieve Polymarket data, answer.

Keyword routing (no extra classification call). Each path extracts clean search
keywords first, and follow-ups resolve against the previous topic (memory).
Returns (answer, topic) so the agent can remember the topic per user.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .llm import extract_query, synthesize
from .polymarket import Market, search_events, search_markets, trending_markets

SYSTEM_PROMPT = """You are Polyseer, a calibrated forecasting agent for Polymarket prediction markets.

You receive a user question and a list of live markets retrieved for it. First judge relevance:

1. If a retrieved market DIRECTLY answers the question (same subject, timeframe and threshold),
   anchor on its live implied probability and respond:
   **Estimate: ~NN%**
   - 1-3 short bullets, citing the market's price.

2. If a market is RELATED but not exact (different date, threshold, or a broader event), you may
   give a careful estimate, but you MUST state the mismatch and that confidence is lower
   (e.g. "$150k is a higher bar than $100k, so $100k is at least this likely").

3. If NO retrieved market is about the question's subject, DO NOT invent a probability. Respond:
   **No matching market** — one short line on what was/wasn't found, and suggest the user try a
   more specific subject or ask for "trending markets".

Hard rules:
- NEVER derive a probability from markets on an unrelated subject (never price a football match,
  election, or war off interest-rate or other unrelated markets). If the list is off-topic, use case 3.
- NEVER fabricate markets, prices, or numbers not present in the provided list.
- Pick the single most relevant market; ignore the rest.
- Use PLAIN TEXT only — no LaTeX or math markup. Write amounts like "$100k" as plain text.
- Be concise. Informational only — not financial advice.
- Do not write a sources section; it is appended automatically."""

_MENTION = re.compile(r"@[A-Za-z0-9_]+")

_TRENDING_KEYS = ("trending", "hottest", "hot market", "biggest market", "biggest markets",
                  "top market", "most popular", "most active", "highest volume", "what's popular")
_RANKED_KEYS = ("who will win", "who wins", "who'll win", "who is winning", "winner", "which team",
                "most likely to win", "favorite to win", "favourite to win", "who will be the next",
                "next president", "next prime minister")
_DISCOVERY_KEYS = ("find market", "search market", "list market", "markets about", "markets on",
                   "markets there", "show me market", "which markets", "what markets", "any market",
                   "other markets", "prediction markets", "markets for", "scan ")


def _clean(text: str) -> str:
    return _MENTION.sub("", text).strip()


async def handle(question: str, prev_topic: str | None = None) -> tuple[str, str | None]:
    q = _clean(question)
    low = q.lower()
    if any(k in low for k in _TRENDING_KEYS):
        return await _trending(), prev_topic
    if any(k in low for k in _RANKED_KEYS):
        return await _ranked(q, prev_topic)
    if any(k in low for k in _DISCOVERY_KEYS):
        return await _discovery(q, prev_topic)
    return await _answer(q, prev_topic)


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


async def _ranked(question: str, prev_topic: str | None) -> tuple[str, str | None]:
    """Multi-outcome events: 'who will win X' -> ranked candidate list."""
    query = await extract_query(question, prev_topic)
    events = await search_events(query, 6)
    chosen = next(((t, m) for t, m in events if len(m) >= 3), None)
    if not chosen:  # not a multi-outcome event — fall back to a normal estimate
        return await _answer(question, prev_topic)
    title, markets = chosen
    ranked = sorted(markets, key=lambda m: m.yes_prob, reverse=True)[:10]
    lines = [f"**{title} — current Polymarket odds:**"]
    for m in ranked:
        label = m.group_title or m.question
        lines.append(f"- {label}: {m.yes_prob:.0%}")
    lines.append(f"\n[View on Polymarket]({ranked[0].url})")
    return "\n".join(lines), query


async def _discovery(question: str, prev_topic: str | None) -> tuple[str, str | None]:
    query = await extract_query(question, prev_topic)
    markets = await search_markets(query, 8)
    if not markets:
        return (f'I couldn\'t find live Polymarket markets matching "{query}". '
                'Try a more specific subject, or ask "trending markets".'), query
    lines = [f'**Polymarket markets matching "{query}":**']
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes[:4])
        lines.append(f"- [{m.title}]({m.url}): {outcomes}")
    return "\n".join(lines), query


async def _answer(question: str, prev_topic: str | None) -> tuple[str, str | None]:
    query = await extract_query(question, prev_topic)
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
    if markets and "no matching market" not in answer.lower():
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
        out.append(f"- {m.title}: {outcomes}{suffix}")
    return "\n".join(out)


def _sources(markets: list[Market]) -> str:
    seen, links = set(), []
    for m in markets:
        if m.url in seen:
            continue
        seen.add(m.url)
        links.append(f"- [{m.title}]({m.url})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


if __name__ == "__main__":  # local test: python -m polyseer.router "who will win the world cup?"
    import asyncio
    import sys

    q = " ".join(sys.argv[1:]) or "What are the odds the Fed cuts rates in July?"
    ans, _ = asyncio.run(handle(q))
    print(ans)
