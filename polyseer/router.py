"""Intent routing: classify the question, fetch Polymarket data, answer.

Lean by design — keyword routing (no extra LLM classification call), three paths:
trending, discovery, and the default "answer" (forecast / market lookup).
"""

from __future__ import annotations

from .llm import synthesize
from .polymarket import Market, search_markets, trending_markets

SYSTEM_PROMPT = """You are Polyseer, a calibrated forecasting agent for Polymarket.

You answer probabilistic questions with a single well-calibrated probability and
short, transparent reasoning, anchored on live prediction-market prices.

Rules:
- Treat market prices as your strongest prior — they are crowd-sourced, money-
  weighted estimates. Anchor on them.
- If the markets don't exactly match the question, say so and reason about the gap.
- Give ONE headline probability as a percentage, then 2-4 concise bullets.
- Never invent markets, prices, or facts. If you have no relevant market, say the
  estimate is low-confidence and explain why.
- Informational only — not financial advice.

Format exactly:
**Estimate: ~NN%**
- bullet
- bullet
(Do not add a sources section — it is appended automatically.)"""

_TRENDING_KEYS = ("trending", "hottest", "hot market", "biggest market", "top market",
                  "most popular", "most active", "highest volume", "what's popular")
_DISCOVERY_KEYS = ("find market", "search market", "list market", "markets about",
                   "show me market", "which markets", "what markets")


async def handle(question: str) -> str:
    q = question.lower()
    if any(k in q for k in _TRENDING_KEYS):
        return await _trending()
    if any(k in q for k in _DISCOVERY_KEYS):
        return await _discovery(question)
    return await _answer(question)


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


async def _discovery(question: str, limit: int = 8) -> str:
    markets = await search_markets(question, limit)
    if not markets:
        return "I couldn't find live markets matching that."
    lines = ["**Matching Polymarket markets:**"]
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes)
        lines.append(f"- [{m.title}]({m.url}): {outcomes}")
    return "\n".join(lines)


async def _answer(question: str) -> str:
    markets = await search_markets(question, 6)
    if markets:
        context = "Relevant live Polymarket markets and implied probabilities:\n" + _render(markets)
    else:
        context = "No relevant live Polymarket markets were found."
    user = f"Question: {question}\n\n{context}\n\nGive your calibrated estimate now."
    return await synthesize(SYSTEM_PROMPT, user) + _sources(markets)


def _render(markets: list[Market]) -> str:
    out = []
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes)
        meta = []
        if m.end_date:
            meta.append(f"ends {m.end_date[:10]}")
        if m.liquidity:
            meta.append(f"liquidity ${m.liquidity:,.0f}")
        suffix = f" ({'; '.join(meta)})" if meta else ""
        out.append(f"- {m.title}: {outcomes}{suffix}")
    return "\n".join(out)


def _sources(markets: list[Market]) -> str:
    if not markets:
        return ""
    seen, links = set(), []
    for m in markets:
        if m.url in seen:
            continue
        seen.add(m.url)
        links.append(f"- [{m.title}]({m.url})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


if __name__ == "__main__":  # local test: python -m polyseer.router "trending markets?"
    import asyncio
    import sys

    q = " ".join(sys.argv[1:]) or "What are the odds the Fed cuts rates in July?"
    print(asyncio.run(handle(q)))
