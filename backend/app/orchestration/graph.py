"""Agent Orchestration — coordinates the supervisor and worker agents."""

import logging
from typing import AsyncGenerator, Dict, List, Optional

from app.agents.supervisor import route_request
from app.agents.research import run_research_agent
from app.agents.coding import run_coding_agent
from app.agents.email_writer import run_email_agent
from app.rag.retrieve import search_documents
from app.tools.web_search import web_search
from app.tools.calculator import calculate
from app.memory.long_term import get_memory_context

logger = logging.getLogger(__name__)


def detect_math_query(message: str) -> Optional[str]:
    """Check if the message contains a math expression to evaluate."""
    import re

    patterns = [
        r"(?:calculate|compute|evaluate|what is|solve)\s+([\d\s\+\-\*\/\(\)\.\^%]+)",
        r"^([\d\s\+\-\*\/\(\)\.%]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, message.lower().strip())
        if match:
            expr = match.group(1).strip()
            if any(op in expr for op in ["+", "-", "*", "/", "**", "%"]):
                return expr
    return None


async def run_orchestration(
    message: str,
    conversation_history: List[Dict],
    user_id: str,
    agent_override: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """
    Main orchestration pipeline:
    1. Route the request via supervisor
    2. Gather tools/context as needed
    3. Run agent(s) and stream results
    4. For multi-agent tasks, chain agents
    """

    # Check for calculator tool
    math_expr = detect_math_query(message)
    if math_expr:
        yield {"type": "tool", "content": f"Using calculator: {math_expr}"}
        result = calculate(math_expr)
        yield {"type": "token", "content": f"**Calculation Result:**\n\n`{math_expr}` = **{result}**\n"}
        yield {"type": "done", "content": f"`{math_expr}` = **{result}**", "agent": "calculator"}
        return

    # Step 1: Route
    routing = await route_request(message, agent_override)
    agents = routing["agents"]
    logger.info(f"Routing decision: {routing}")

    # Let the user see *why* the supervisor chose this agent.
    from app.agents.llm import _resolve_model_temp
    agent_models = {}
    for a in agents:
        m, t = _resolve_model_temp(a, None, None)
        agent_models[a] = {"model": m, "temperature": t}

    yield {
        "type": "routing",
        "content": {
            "agents": agents,
            "reasoning": routing.get("reasoning", ""),
            "models": agent_models,
        },
    }

    # Long-term memory: loaded once, shared by every agent in this request.
    memory_context = await get_memory_context(user_id)

    # Step 2: Execute agent(s)
    if len(agents) == 1:
        agent = agents[0]
        yield {"type": "agent", "content": agent}

        async for event in _run_single_agent(
            agent, message, conversation_history, user_id,
            memory_context=memory_context,
        ):
            yield event

    else:
        # Multi-agent: chain agents sequentially
        accumulated_context = ""

        for i, agent in enumerate(agents):
            yield {"type": "agent", "content": agent}

            if i == 0:
                # First agent runs normally
                async for event in _run_single_agent(
                    agent, message, conversation_history, user_id,
                    memory_context=memory_context,
                ):
                    if event["type"] == "done":
                        accumulated_context = event.get("content", "")
                    else:
                        yield event
            else:
                # Subsequent agents receive prior context
                async for event in _run_single_agent(
                    agent, message, conversation_history, user_id,
                    prior_context=accumulated_context,
                    memory_context=memory_context,
                ):
                    if event["type"] == "done":
                        accumulated_context += "\n\n" + event.get("content", "")
                    else:
                        yield event

        yield {"type": "done", "content": accumulated_context, "agent": ",".join(agents)}


async def _run_single_agent(
    agent: str,
    message: str,
    conversation_history: List[Dict],
    user_id: str,
    prior_context: Optional[str] = None,
    memory_context: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """Run a single agent with appropriate tools and context."""

    if agent == "research":
        # Gather RAG context (search_documents resolves the real filename per chunk)
        rag_context = await search_documents(message, user_id, top_k=5)

        # Web search
        web_results = None
        if not rag_context:
            yield {"type": "tool", "content": "Searching the web..."}
            try:
                web_results = await web_search(message, num_results=5)
            except Exception as e:
                logger.warning(f"Web search failed: {e}")
                web_results = []

        if rag_context:
            yield {"type": "tool", "content": f"Found {len(rag_context)} relevant document chunks"}

        async for event in run_research_agent(
            message, conversation_history, rag_context, web_results,
            memory_context=memory_context,
        ):
            yield event

    elif agent == "coding":
        async for event in run_coding_agent(
            message, conversation_history, memory_context=memory_context
        ):
            yield event

    elif agent == "email":
        async for event in run_email_agent(
            message, conversation_history, research_context=prior_context,
            memory_context=memory_context,
        ):
            yield event

    else:
        # Default to research
        async for event in run_research_agent(
            message, conversation_history, memory_context=memory_context
        ):
            yield event
