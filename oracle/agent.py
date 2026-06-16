"""Oracle of Odds — an ASI:One-compatible uAgent.

Runs as a *mailbox* agent: it executes wherever you host it (e.g. Railway) but
registers in the Almanac and connects to Agentverse via the Mailroom, so ASI:One
can route natural-language questions to it through the Chat Protocol.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from .forecaster import forecast

AGENT_SEED = os.getenv("AGENT_SEED", "oracle-of-odds-dev-seed-change-me")
PORT = int(os.getenv("PORT", "8000"))

agent = Agent(
    name="oracle-of-odds",
    seed=AGENT_SEED,
    port=PORT,
    mailbox=True,
    publish_agent_details=True,
    readme_path="README.md",
)

chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
    # Every chat message must be acknowledged.
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )

    question = " ".join(item.text for item in msg.content if isinstance(item, TextContent)).strip()
    if not question:
        return

    ctx.logger.info(f"Question from {sender}: {question}")
    try:
        answer = await forecast(question)
    except Exception as exc:  # surface a useful message instead of going silent
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
async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement) -> None:
    ctx.logger.debug(f"Ack from {sender} for {msg.acknowledged_msg_id}")


agent.include(chat, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
