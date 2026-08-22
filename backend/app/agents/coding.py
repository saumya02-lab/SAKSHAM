"""Coding Agent — generates, explains, and debugs code."""

import logging
from typing import AsyncGenerator, List, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)

CODING_SYSTEM_PROMPT = """You are SAKSHAM Coding Agent — an expert programmer and technical assistant.

Your core principles:
1. Generate clean, well-documented, and runnable code.
2. Always explain your code with comments and a brief explanation.
3. Label all assumptions clearly.
4. When debugging, identify the root cause before suggesting fixes.
5. Include error handling and edge cases where appropriate.
6. If asked to explain code, provide a structured breakdown.
7. Do NOT invent or hallucinate APIs — if unsure, say so.
8. When generating tests, use appropriate testing frameworks.
9. Use proper code formatting with syntax highlighting (markdown code blocks with language).

Capabilities:
- Code generation in any programming language
- Code explanation and documentation
- Bug identification and fixing
- Unit test generation
- Algorithm design and optimization
- Code refactoring suggestions
"""


async def run_coding_agent(
    message: str,
    conversation_history: List[Dict],
    memory_context: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """Run the coding agent and yield streaming events."""

    system_prompt = CODING_SYSTEM_PROMPT
    if memory_context:
        system_prompt = f"{system_prompt}\n\n{memory_context}"

    messages = [SystemMessage(content=system_prompt)]

    for msg in conversation_history[-10:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=message))

    llm = get_llm(streaming=True, agent_role="coding")

    full_response = ""
    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            full_response += token
            yield {"type": "token", "content": token}

    yield {"type": "done", "content": full_response}
