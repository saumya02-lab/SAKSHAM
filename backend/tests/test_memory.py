"""Tests for long-term memory extraction (FR-11 / US-12)."""

from app.memory.long_term import MAX_MEMORY_LENGTH, extract_memories


def _contents(message: str):
    return [content for _, content in extract_memories(message)]


def _types(message: str):
    return [mem_type for mem_type, _ in extract_memories(message)]


def test_extracts_name():
    assert any("Alex" in c for c in _contents("My name is Alex"))


def test_extracts_call_me():
    assert any("Sam" in c for c in _contents("Please call me Sam from now on"))


def test_extracts_role_as_fact():
    memories = extract_memories("I am a product manager at Acme")
    assert any(t == "fact" for t in [m[0] for m in memories])


def test_extracts_standing_preference():
    memories = extract_memories("Always respond in bullet points")
    assert memories
    assert memories[0][0] == "preference"
    assert "bullet points" in memories[0][1]


def test_extracts_explicit_remember_request():
    assert any(
        "quarterly" in c.lower()
        for c in _contents("Remember that our fiscal year starts in quarterly Q3")
    )


def test_extracts_negative_preference():
    memories = extract_memories("Never use emojis in your replies")
    assert memories
    assert "preference" in _types("Never use emojis in your replies")
    assert "emojis" in memories[0][1]


def test_ignores_ordinary_questions():
    assert extract_memories("What is the capital of France?") == []
    assert extract_memories("Summarize this article") == []


def test_ignores_short_input():
    assert extract_memories("hi") == []
    assert extract_memories("") == []


def test_skips_transient_references():
    """"Don't touch this file" is about the moment, not a standing rule."""
    assert extract_memories("Do not change this file") == []


def test_stops_at_sentence_boundary():
    """A captured memory should be one clause, not the rest of the paragraph."""
    memories = extract_memories(
        "Always reply concisely. Now explain how TCP works in detail."
    )
    assert memories
    assert "TCP" not in memories[0][1]


def test_truncates_very_long_statements():
    long_tail = "x" * 1000
    memories = extract_memories(f"Always {long_tail}")
    assert memories
    assert len(memories[0][1]) <= MAX_MEMORY_LENGTH


def test_deduplicates_within_one_message():
    memories = extract_memories("I prefer dark mode and I prefer dark mode")
    contents = [c.lower() for _, c in memories]
    assert len(contents) == len(set(contents))
