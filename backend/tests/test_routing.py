"""Routing accuracy tests.

PRD PO-1 / US-3 require >=90% correct agent selection over a 30-prompt set.

The rule layer deliberately abstains (returns None) on ambiguous prompts and
defers to the LLM. Mocking the LLM to return the expected answer would make an
accuracy number meaningless, so this suite measures the rule layer on the
prompts it actually commits to, and separately asserts that it commits to
enough of them to be useful.
"""

import pytest

from app.agents.supervisor import rule_based_route, route_request

# (prompt, expected agents) — 30 prompts, 10 coding / 10 research / 8 email / 2 multi.
LABELLED_PROMPTS = [
    # ── Coding ──
    ("Write a Python function to reverse a linked list", ["coding"]),
    ("Debug this JavaScript error: undefined is not a function", ["coding"]),
    ("Implement a binary search algorithm in Python", ["coding"]),
    ("Fix the syntax error in my SQL query", ["coding"]),
    ("Write unit tests for this React component", ["coding"]),
    ("Refactor this loop to be more optimized", ["coding"]),
    ("Explain what this regex does", ["coding"]),
    ("How do I create a REST API endpoint in FastAPI?", ["coding"]),
    ("My Python script throws an IndexError, help me fix it", ["coding"]),
    ("Generate a TypeScript class for a user model", ["coding"]),
    # ── Research ──
    ("What is the latest news on quantum computing?", ["research"]),
    ("Summarize the key trends in renewable energy", ["research"]),
    ("Who is the CEO of OpenAI?", ["research"]),
    ("Find recent articles about AI regulation", ["research"]),
    ("Compare the statistics for electric vehicle adoption", ["research"]),
    ("Tell me about the history of the internet", ["research"]),
    ("Look up information on the Mars rover mission", ["research"]),
    ("Give me an analysis report of the 2024 market data", ["research"]),
    ("Explain the facts behind climate change research", ["research"]),
    ("What are the sources and references for this claim?", ["research"]),
    # ── Email / writing ──
    ("Draft a formal email to my manager about a raise", ["email"]),
    ("Write a professional message to a client", ["email"]),
    ("Rewrite this paragraph in a friendly tone", ["email"]),
    ("Compose a follow-up email after the interview", ["email"]),
    ("Proofread and edit this announcement", ["email"]),
    ("Draft a reply to this customer complaint", ["email"]),
    ("Make this email more formal and professional", ["email"]),
    ("Respond to this message with a friendly subject line", ["email"]),
    # ── Multi-agent ──
    (
        "Research competitor pricing and draft an email to the sales team",
        ["research", "email"],
    ),
    ("Find the latest AI trends and write a summary email", ["research", "email"]),
]

MIN_ACCURACY = 0.90
MIN_COVERAGE = 0.70


def test_prompt_set_has_30_entries():
    """Guard the dataset size the PRD acceptance criterion is stated against."""
    assert len(LABELLED_PROMPTS) == 30


def test_rule_based_routing_accuracy():
    """>=90% of the prompts the rule layer commits to must be routed correctly."""
    decided = 0
    correct = 0
    failures = []

    for prompt, expected in LABELLED_PROMPTS:
        result = rule_based_route(prompt)
        if result is None:
            continue  # abstained; the LLM layer handles this prompt

        decided += 1
        if result["agents"] == expected:
            correct += 1
        else:
            failures.append((prompt, expected, result["agents"]))

    assert decided > 0, "rule layer decided nothing at all"

    accuracy = correct / decided
    coverage = decided / len(LABELLED_PROMPTS)

    print(
        f"\nrouting: {len(LABELLED_PROMPTS)} prompts, {decided} decided by rules "
        f"({coverage:.0%} coverage), accuracy {accuracy:.0%}"
    )
    for prompt, expected, got in failures:
        print(f"  misroute: {prompt!r} expected={expected} got={got}")

    assert accuracy >= MIN_ACCURACY, (
        f"routing accuracy {accuracy:.0%} < {MIN_ACCURACY:.0%}; misroutes: {failures}"
    )
    # A tiny sample could hit 100% by abstaining on everything hard, so the
    # rule layer also has to actually cover most of the set.
    assert coverage >= MIN_COVERAGE, (
        f"rule coverage {coverage:.0%} < {MIN_COVERAGE:.0%}"
    )


def test_abstains_rather_than_guessing():
    """Vague prompts must return None so the LLM layer can decide."""
    assert rule_based_route("hi") is None
    assert rule_based_route("ok thanks") is None


def test_multi_agent_order_is_research_then_email():
    """Chained requests must run research before drafting (US-6)."""
    result = rule_based_route(
        "Research competitor pricing and draft an email to the sales team"
    )
    assert result is not None
    assert result["agents"] == ["research", "email"]


def test_keywords_do_not_match_mid_word():
    """Regression: "latest" contains "test", which used to trigger coding.

    The visible symptom was a spurious third agent on multi-agent requests,
    so the coding agent ran (and emitted code) for a research+email task.
    """
    result = rule_based_route("Find the latest AI trends and write a summary email")
    assert result is not None
    assert "coding" not in result["agents"]
    assert result["agents"] == ["research", "email"]


def test_keywords_still_match_plurals():
    """Word-start anchoring must not break ordinary inflections."""
    assert rule_based_route("Write unit tests for this React component") == {
        "agents": ["coding"],
        "reasoning": "keyword match: coding",
    }


@pytest.mark.asyncio
async def test_manual_override_wins():
    """An explicit agent pick bypasses both the rules and the LLM (US-4)."""
    for agent in ("research", "coding", "email"):
        result = await route_request("anything at all", manual_agent=agent)
        assert result["agents"] == [agent]


@pytest.mark.asyncio
async def test_auto_does_not_count_as_override():
    """'auto' means 'decide for me', not 'use an agent literally named auto'."""
    result = await route_request(
        "Write a Python function to reverse a list", manual_agent="auto"
    )
    assert result["agents"] == ["coding"]
