"""Configurable LLM backend.

Pick the reasoning model with the LLM_PROVIDER env var:
  • asi1      (default) — ASI:One (Web3-native LLM), OpenAI-compatible API.
  • anthropic           — Claude via the official Anthropic SDK.
  • openai              — OpenAI / any OpenAI-compatible endpoint.
"""

from __future__ import annotations

import json
import os
import re

_PLAN_SYSTEM = (
    "You are the planner for a Polymarket prediction-market assistant. Read the user's message, "
    "decide what they want, extract a clean market search query, and flag any crypto asset.\n"
    'Return ONLY a compact JSON object: '
    '{"intent": <forecast|ranked|trending|discovery>, "query": <keywords>, "asset": <crypto ticker or empty>}.\n'
    "Intents:\n"
    "- forecast: a probability question about a specific outcome ('odds of X', 'will Y happen', 'chance of Z').\n"
    "- ranked: who/which wins among many candidates ('who will win the world cup', 'next president', 'favorite to win').\n"
    "- trending: the hottest / biggest / most active markets right now, with no specific subject.\n"
    "- discovery: browse or list what markets exist about a topic ('what markets on sports', 'find markets about AI').\n"
    "For query: 2-6 keywords using the terms prediction markets actually use (e.g. 'AGI' for human-level/general AI, "
    "ticker symbols for stocks, full names for people/teams, 'Fed rate', 'Bitcoin', 'recession'); drop filler, fix typos. "
    "For trending, query may be empty.\n"
    "For asset: set it to the crypto ticker (BTC, ETH, SOL, FET, ...) ONLY if the message is about a specific "
    "cryptocurrency's price or a crypto price target; otherwise empty string.\n"
    "If a previous topic is given and the message is a follow-up ('any others?', 'what about Brazil?', 'more'), "
    "resolve the query against that topic."
)


async def plan(question: str, context: str | None = None) -> dict:
    """Dynamically classify intent, extract a search query, and detect a crypto asset.

    Returns {"intent": ..., "query": str, "asset": str}.
    """
    user = question if not context else f"Previous topic: {context}\nNew message: {question}"
    try:
        raw = await synthesize(_PLAN_SYSTEM, user)
    except Exception:
        return {"intent": "forecast", "query": question, "asset": ""}
    match = re.search(r"\{.*\}", raw or "", re.S)
    try:
        data = json.loads(match.group(0)) if match else {}
    except (ValueError, TypeError):
        data = {}
    intent = str(data.get("intent", "forecast")).strip().lower()
    if intent not in ("forecast", "ranked", "trending", "discovery"):
        intent = "forecast"
    query = (str(data.get("query") or question)).strip().strip('"')[:80] or question
    asset = re.sub(r"[^A-Za-z0-9]", "", str(data.get("asset") or "")).upper()[:10]
    return {"intent": intent, "query": query, "asset": asset}


async def synthesize(system: str, user: str) -> str:
    provider = os.getenv("LLM_PROVIDER", "asi1").strip().lower()
    if provider == "anthropic":
        return await _anthropic(system, user)
    if provider == "openai":
        return await _openai_compatible(
            system, user,
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key_env="OPENAI_API_KEY",
            model_env="OPENAI_MODEL",
            default_model="gpt-4o-mini",
        )
    return await _openai_compatible(
        system, user,
        base_url=os.getenv("ASI_ONE_BASE_URL", "https://api.asi1.ai/v1"),
        api_key_env="ASI_ONE_API_KEY",
        model_env="ASI_ONE_MODEL",
        default_model="asi1-mini",
    )


async def _anthropic(system: str, user: str) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic()
    model = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
    resp = await client.messages.create(
        model=model,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


async def _openai_compatible(
    system: str,
    user: str,
    *,
    base_url: str | None,
    api_key_env: str,
    model_env: str,
    default_model: str,
) -> str:
    from openai import AsyncOpenAI

    kwargs = {"api_key": os.environ[api_key_env]}
    if base_url:
        kwargs["base_url"] = base_url
    client = AsyncOpenAI(**kwargs)
    model = os.getenv(model_env, default_model)
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1200,
    )
    return (resp.choices[0].message.content or "").strip()
