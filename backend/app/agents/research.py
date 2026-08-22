"""Research Agent — answers questions with grounded, cited information."""

import logging
from typing import AsyncGenerator, List, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import get_llm

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are SAKSHAM Research Agent — a skilled research assistant.

Your core principles:
1. ALWAYS cite your sources. Use [1], [2], etc. for inline citations.
2. If you have retrieved documents/context, base your answer PRIMARILY on them.
3. If you don't know something or can't find it in your sources, say so clearly — NEVER fabricate.
4. Structure your answers clearly with headings and bullet points when appropriate.
5. At the end, list all sources used in a "Sources:" section.

When document context is provided:
- Prioritize information from the provided documents
- Cite the document name and relevant sections
- If the documents don't contain the answer, say so

When web search results are provided:
- Synthesize information from multiple sources
- Include the URLs as citations
- Note when information might be outdated
"""


async def run_research_agent(
    message: str,
    conversation_history: List[Dict],
    rag_context: Optional[List[Dict]] = None,
    web_results: Optional[List[Dict]] = None,
    memory_context: Optional[str] = None,
) -> AsyncGenerator[Dict, None]:
    """Run the research agent and yield streaming events."""

    context_parts = []

    if rag_context:
        context_parts.append("=== RETRIEVED DOCUMENTS ===")
        for i, ctx in enumerate(rag_context, 1):
            source_name = ctx.get("source_name", "Document")
            content = ctx.get("chunk", ctx.get("content", ""))
            context_parts.append(f"[{i}] Source: {source_name}\n{content}\n")

    if web_results:
        offset = len(rag_context or [])
        context_parts.append("=== WEB SEARCH RESULTS ===")
        for i, result in enumerate(web_results, offset + 1):
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")
            context_parts.append(f"[{i}] {title}\nURL: {url}\n{snippet}\n")

    context_text = "\n".join(context_parts) if context_parts else ""

    system_prompt = RESEARCH_SYSTEM_PROMPT
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
    if context_text:
        user_prompt = f"""Context (use this to answer — cite sources):
{context_text}

Question: {message}"""

    messages.append(HumanMessage(content=user_prompt))

    llm = get_llm(streaming=True, agent_role="research")

    citations = []
    if rag_context:
        for ctx in rag_context:
            citations.append({
                "source_title": ctx.get("source_name", "Document"),
                "source_url": "",
                "snippet": ctx.get("chunk", "")[:200],
            })
    if web_results:
        for result in web_results:
            citations.append({
                "source_title": result.get("title", ""),
                "source_url": result.get("url", ""),
                "snippet": result.get("snippet", "")[:200],
            })

    full_response = ""
    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            full_response += token
            yield {"type": "token", "content": token}

    for citation in citations:
        yield {"type": "citation", "data": citation}

    yield {"type": "done", "content": full_response}
