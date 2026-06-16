"""Polyseer — an ASI:One-compatible uAgent (Chat Protocol over the uAgents framework).

Runs on your own infra (e.g. Railway). Set AGENT_ENDPOINT to register as a public
ENDPOINT agent; leave it unset to run as a MAILBOX agent.
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

from .router import handle

AGENT_SEED = os.getenv("AGENT_SEED", "polyseer-dev-seed-change-me")
PORT = int(os.getenv("PORT", "8000"))
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")  # e.g. https://polyseer.up.railway.app/submit

_common = dict(name="polyseer", seed=AGENT_SEED, port=PORT,
               publish_agent_details=True, readme_path="README.md")
agent = Agent(endpoint=[AGENT_ENDPOINT], **_common) if AGENT_ENDPOINT else Agent(mailbox=True, **_common)

chat = Protocol(spec=chat_protocol_spec)


@chat.on_message(ChatMessage)
async def handle_chat(ctx: Context, sender: str, msg: ChatMessage) -> None:
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )
    question = " ".join(item.text for item in msg.content if isinstance(item, TextContent)).strip()
    if not question:
        return
    ctx.logger.info(f"Question from {sender}: {question}")
    try:
        answer = await handle(question)
    except Exception as exc:
        ctx.logger.exception("handler failed")
        answer = f"Sorry — I couldn't answer that right now ({exc})."
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
