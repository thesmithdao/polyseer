"""Forecasting orchestration: question -> markets -> calibrated answer."""

from __future__ import annotations

from .llm import synthesize
from .polymarket import Market, search_markets

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


def _render_markets(markets: list[Market]) -> str:
    lines = []
    for m in markets:
        outcomes = ", ".join(f"{label} {prob:.0%}" for label, prob in m.outcomes)
        meta = []
        if m.end_date:
            meta.append(f"ends {m.end_date[:10]}")
        if m.liquidity:
            meta.append(f"liquidity ${m.liquidity:,.0f}")
        if m.volume:
            meta.append(f"volume ${m.volume:,.0f}")
        suffix = f" ({'; '.join(meta)})" if meta else ""
        lines.append(f"- {m.question}: {outcomes}{suffix}")
    return "\n".join(lines)


def _sources(markets: list[Market]) -> str:
    if not markets:
        return ""
    seen, links = set(), []
    for m in markets:
        if m.url in seen:
            continue
        seen.add(m.url)
        links.append(f"- [{m.question}]({m.url})")
        if len(links) >= 4:
            break
    return "\n\n**Markets referenced:**\n" + "\n".join(links)


async def forecast(question: str) -> str:
    markets = await search_markets(question, limit=6)
    if markets:
        context = "Relevant live Polymarket markets and their implied probabilities:\n" + _render_markets(markets)
    else:
        context = "No relevant live Polymarket markets were found for this question."

    user_prompt = (
        f"Question: {question}\n\n"
        f"{context}\n\n"
        "Give your calibrated estimate now."
    )
    answer = await synthesize(SYSTEM_PROMPT, user_prompt)
    return answer + _sources(markets)


if __name__ == "__main__":  # quick local test: python -m oracle.forecaster "Will the Fed cut rates in July?"
    import asyncio
    import sys

    q = " ".join(sys.argv[1:]) or "Will Bitcoin be above $100k by the end of the year?"
    print(asyncio.run(forecast(q)))
