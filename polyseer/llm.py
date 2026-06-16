"""Configurable LLM backend.

Pick the reasoning model with the LLM_PROVIDER env var:
  • asi1      (default) — ASI:One (Web3-native LLM), OpenAI-compatible API.
  • anthropic           — Claude via the official Anthropic SDK.
  • openai              — OpenAI / any OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os


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
