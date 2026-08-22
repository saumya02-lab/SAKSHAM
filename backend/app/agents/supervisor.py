"""Supervisor Agent — classifies intent and routes to the right agent(s)."""

import re
import logging
from typing import List, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.llm import get_routing_llm

logger = logging.getLogger(__name__)

RESEARCH_KEYWORDS = [
    "research", "search", "find", "look up", "summarize", "summary",
    "what is", "who is", "explain", "tell me about", "information",
    "article", "source", "reference", "news", "latest", "trend",
    "compare", "analysis", "report", "data", "statistics", "facts",
]

CODING_KEYWORDS = [
    "code", "program", "function", "class", "debug", "bug", "error",
    "fix", "implement", "algorithm", "python", "javascript", "java",
    "typescript", "sql", "html", "css", "react", "api", "test",
    "unit test", "script", "compile", "syntax", "variable", "loop",
    "regex", "refactor", "optimize",
]

EMAIL_KEYWORDS = [
    "email", "draft", "write", "compose", "letter", "message",
    "formal", "informal", "tone", "professional", "friendly",
    "reply", "respond", "subject", "dear", "sincerely",
    "memo", "announcement", "invitation", "follow up", "follow-up",
    "summarize this thread", "rewrite", "proofread", "edit",
]


def _compile(keywords: List[str]) -> List[re.Pattern]:
    """Anchor each keyword to a word start.

    Trailing inflections are allowed on purpose ("test" matches "tests",
    "trend" matches "trends"), but a keyword may not match mid-word, which is
    what previously made "latest" count as the coding keyword "test".
    """
    return [re.compile(r"\b" + re.escape(kw)) for kw in keywords]


_RESEARCH_PATTERNS = _compile(RESEARCH_KEYWORDS)
_CODING_PATTERNS = _compile(CODING_KEYWORDS)
_EMAIL_PATTERNS = _compile(EMAIL_KEYWORDS)


def _score(msg_lower: str, patterns: List[re.Pattern]) -> int:
    """Number of distinct keywords from one set present in the message."""
    return sum(1 for p in patterns if p.search(msg_lower))


MULTI_AGENT_PATTERNS = [
    r"research.*(?:and|then).*(?:draft|write|email|compose)",
    r"find.*(?:and|then).*(?:draft|write|email|compose)",
    r"(?:draft|write).*(?:based on|using).*research",
    r"look up.*(?:and|then).*(?:send|email|write)",
]

ROUTING_SYSTEM_PROMPT = """You are a routing supervisor for a multi-agent AI system.
Your job is to classify user requests and route them to the correct agent(s).

Available agents:
- research: For information lookup, web search, document-based Q&A, summarization, analysis
- coding: For code generation, explanation, debugging, and technical help
- email: For drafting emails, writing content, adjusting tone, summarizing threads

Rules:
1. If the request involves MULTIPLE agents (e.g., "research X then write an email about it"), return BOTH agents in order.
2. If unsure, default to "research".
3. Return ONLY a JSON object: {"agents": ["agent1"], "reasoning": "brief reason"}
4. For multi-agent tasks: {"agents": ["research", "email"], "reasoning": "research then draft"}
"""


def rule_based_route(message: str) -> Optional[Dict]:
    """Fast keyword/pattern-based routing."""
    msg_lower = message.lower()

    for pattern in MULTI_AGENT_PATTERNS:
        if re.search(pattern, msg_lower):
            agents = []
            if _score(msg_lower, _RESEARCH_PATTERNS):
                agents.append("research")
            if _score(msg_lower, _EMAIL_PATTERNS):
                agents.append("email")
            if _score(msg_lower, _CODING_PATTERNS):
                agents.append("coding")
            if len(agents) >= 2:
                return {"agents": agents, "reasoning": "multi-agent pattern detected"}

    research_score = _score(msg_lower, _RESEARCH_PATTERNS)
    coding_score = _score(msg_lower, _CODING_PATTERNS)
    email_score = _score(msg_lower, _EMAIL_PATTERNS)

    max_score = max(research_score, coding_score, email_score)

    if max_score >= 2:
        if research_score == max_score:
            return {"agents": ["research"], "reasoning": "keyword match: research"}
        elif coding_score == max_score:
            return {"agents": ["coding"], "reasoning": "keyword match: coding"}
        elif email_score == max_score:
            return {"agents": ["email"], "reasoning": "keyword match: email"}

    return None


async def llm_based_route(message: str) -> Dict:
    """Use LLM for ambiguous routing."""
    import json

    try:
        llm = get_routing_llm()
        response = await llm.ainvoke([
            SystemMessage(content=ROUTING_SYSTEM_PROMPT),
            HumanMessage(content=f"Route this request: {message}"),
        ])

        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        result = json.loads(content)
        if "agents" not in result:
            result = {"agents": ["research"], "reasoning": "default fallback"}
        return result

    except Exception as e:
        logger.error(f"LLM routing failed: {e}")
        return {"agents": ["research"], "reasoning": f"LLM routing error, defaulting to research: {e}"}


async def route_request(message: str, manual_agent: Optional[str] = None) -> Dict:
    """Route a user request to the appropriate agent(s). Hybrid: rules first, LLM fallback."""
    if manual_agent and manual_agent != "auto":
        return {"agents": [manual_agent], "reasoning": "manual selection"}

    rule_result = rule_based_route(message)
    if rule_result:
        logger.info(f"Rule-based routing: {rule_result}")
        return rule_result

    llm_result = await llm_based_route(message)
    logger.info(f"LLM-based routing: {llm_result}")
    return llm_result
