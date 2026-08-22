"""Long-term memory — durable user facts and preferences (PRD F-MEM / FR-11).

Two halves:
  * `extract_memories`  — pulls durable facts/preferences out of a user message.
  * `get_memory_context` — renders stored memories for injection into prompts.

Extraction is deliberately rule-based rather than an extra LLM call: it is
free, deterministic, instant, and easy to unit test. PRD C-1 constrains our
LLM budget, so spending a second round-trip per message purely to notice
"call me Alex" is not worth it.
"""

import logging
import re
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Memory

logger = logging.getLogger(__name__)

MAX_MEMORIES_IN_PROMPT = 20
MAX_MEMORY_LENGTH = 300

# Each pattern captures the durable part of the statement in group 1.
# "preference" = how the user wants us to behave; "fact" = something about them.
_PREFERENCE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:always|from now on|going forward)\s+(.{4,200})", re.I),
    re.compile(r"\bkeep (?:your )?(?:answers|responses|replies)\s+(.{2,200})", re.I),
    re.compile(r"\b(?:i )?prefer(?:s|red)?\s+(.{4,200})", re.I),
    re.compile(r"\bi (?:like|want|need)\s+(?:you to\s+)?(.{4,200})", re.I),
    re.compile(r"\b(?:don't|do not|never)\s+(.{4,200})", re.I),
    re.compile(r"\brespond (?:in|with|using)\s+(.{2,200})", re.I),
]

_FACT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:my name is|i am called|call me)\s+(.{2,100})", re.I),
    re.compile(r"\bi(?:'m| am)\s+(?:a|an)\s+(.{3,150})", re.I),
    re.compile(r"\bi work (?:at|for|on)\s+(.{2,150})", re.I),
    re.compile(r"\bmy (?:team|company|role|job|project) is\s+(.{2,150})", re.I),
    re.compile(r"\bremember that\s+(.{4,200})", re.I),
]

# Guard against storing transient chatter as if it were a durable preference.
_TRANSIENT_MARKERS = (
    "this file",
    "this code",
    "the above",
    "that error",
    "right now",
    "this time",
    "just now",
)


def _clean(fragment: str) -> str:
    """Trim a captured fragment to a single tidy clause."""
    text = fragment.strip()
    # Cut at the first sentence/clause boundary so we don't store paragraphs.
    text = re.split(r"[.!?\n]|\bbut\b|\bhowever\b", text, maxsplit=1)[0]
    text = text.strip(" ,;:-\"'()")
    return re.sub(r"\s+", " ", text)[:MAX_MEMORY_LENGTH]


def extract_memories(message: str) -> List[Tuple[str, str]]:
    """Return a list of `(type, content)` memories found in `message`.

    `type` is either "preference" or "fact". Returns an empty list when the
    message contains nothing worth remembering, which is the common case.
    """
    if not message or len(message) < 6:
        return []

    found: List[Tuple[str, str]] = []
    seen: set[str] = set()

    for mem_type, patterns in (
        ("preference", _PREFERENCE_PATTERNS),
        ("fact", _FACT_PATTERNS),
    ):
        for pattern in patterns:
            match = pattern.search(message)
            if not match:
                continue

            content = _clean(match.group(1))
            if len(content) < 3:
                continue
            if any(marker in content.lower() for marker in _TRANSIENT_MARKERS):
                continue

            key = content.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append((mem_type, content))

    return found


async def save_memories(message: str, user_id: str, db: AsyncSession) -> int:
    """Extract memories from `message` and persist any that are new.

    Returns the number of memories stored. Never raises — memory is a
    best-effort enhancement and must not break the chat flow (NFR-05).
    """
    try:
        candidates = extract_memories(message)
        if not candidates:
            return 0

        result = await db.execute(
            select(Memory.content).where(Memory.user_id == user_id)
        )
        existing = {c.strip().lower() for c in result.scalars().all()}

        stored = 0
        for mem_type, content in candidates:
            if content.strip().lower() in existing:
                continue
            db.add(Memory(user_id=user_id, type=mem_type, content=content))
            existing.add(content.strip().lower())
            stored += 1

        if stored:
            await db.commit()
            logger.info(f"Stored {stored} memory item(s) for user {user_id}")
        return stored

    except Exception as e:
        logger.warning(f"Memory extraction failed (continuing without it): {e}")
        return 0


async def get_memory_context(user_id: str, db: Optional[AsyncSession] = None) -> str:
    """Render this user's stored memories as a prompt-ready block.

    Returns an empty string when the user has no memories, so callers can
    append it unconditionally.
    """

    async def _load(session: AsyncSession) -> List[Memory]:
        result = await session.execute(
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(MAX_MEMORIES_IN_PROMPT)
        )
        return list(result.scalars().all())

    try:
        if db is not None:
            memories = await _load(db)
        else:
            from app.core.database import async_session

            async with async_session() as session:
                memories = await _load(session)

        if not memories:
            return ""

        preferences = [m.content for m in memories if m.type == "preference"]
        facts = [m.content for m in memories if m.type != "preference"]

        lines = ["=== WHAT YOU KNOW ABOUT THIS USER ==="]
        if facts:
            lines.append("Facts:")
            lines.extend(f"- {f}" for f in facts)
        if preferences:
            lines.append("Standing preferences (honor these):")
            lines.extend(f"- {p}" for p in preferences)

        return "\n".join(lines)

    except Exception as e:
        logger.warning(f"Could not load memory context: {e}")
        return ""
