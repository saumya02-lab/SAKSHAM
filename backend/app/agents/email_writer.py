"""Email/Writing Agent — drafts, summarizes, and adjusts tone of text."""

import logging
from typing import AsyncGenerator, List, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)

EMAIL_SYSTEM_PROMPT = """You are SAKSHAM Email/Writing Agent — a skilled communicator and writing assistant.

Your core principles:
1. Match the requested tone exactly (formal, friendly, concise, persuasive, etc.).
2. Structure emails properly with Subject, Greeting, Body, Closing.
3. When summarizing threads, capture ALL key points and action items.
4. Never fabricate facts — if context/research is provided, use ONLY that information.
5. Keep writing clear, professional, and ready-to-send.
6. When adjusting tone, preserve the original meaning and key information.
7. For replies, maintain appropriate context from the original message.

Capabilities:
- Draft emails from a brief description
- Summarize email threads (key points + action items)
- Adjust tone (formal ↔ friendly ↔ concise)
- Write professional content (memos, announcements, invitations)
- Suggest reply options
- Proofread and improve existing text
"""


async def run_email_agent(
    message: str,
    conversation_history: List[Dict],
    research_context: Optional[str] = None,
    memory_context: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """Run the email/writing agent and yield streaming events."""

    system_prompt = EMAIL_SYSTEM_PROMPT
    if memory_context:
        system_prompt = f"{system_prompt}\n\n{memory_context}"

    messages = [SystemMessage(content=system_prompt)]

    for msg in conversation_history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=msg["content"]))

    user_prompt = message
    if research_context:
        user_prompt = f"""Use the following research context to inform your writing:

=== RESEARCH CONTEXT ===
{research_context}
========================

Task: {message}"""

    messages.append(HumanMessage(content=user_prompt))

    llm = get_llm(streaming=True, agent_role="email")

    full_response = ""
    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            full_response += token
            yield {"type": "token", "content": token}

    yield {"type": "done", "content": full_response}
