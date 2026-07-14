"""Unit tests for the Coder and Reviewer nodes with fake LLMs."""

from __future__ import annotations

from code_reviewer.nodes import coder, reviewer
from code_reviewer.state import ReviewVerdict


def _state(**overrides):
    base = {
        "task": "Write a hello world function",
        "max_iterations": 3,
        "code": "",
        "review": "",
        "approved": False,
        "iterations": 0,
        "messages": [],
    }
    base.update(overrides)
    return base


def test_coder_strips_fences_and_increments_iteration(monkeypatch, make_coder_llm):
    fake = make_coder_llm(["def hello():\n    return 'hi'"])
    monkeypatch.setattr(coder, "build_llm", lambda temperature: fake)

    result = coder.coder_node(_state(iterations=0))

    assert result["code"] == "def hello():\n    return 'hi'"
    assert result["iterations"] == 1
    assert result["messages"][0].name == "coder"


def test_reviewer_returns_structured_verdict(monkeypatch, make_reviewer_llm):
    fake = make_reviewer_llm([ReviewVerdict(approved=True, feedback="Looks good.")])
    monkeypatch.setattr(reviewer, "build_llm", lambda temperature: fake)

    result = reviewer.reviewer_node(_state(code="def hello(): return 'hi'", iterations=1))

    assert result["approved"] is True
    assert result["review"] == "Looks good."
    assert "APPROVED" in result["messages"][0].content


def test_reviewer_rejection_carries_feedback(monkeypatch, make_reviewer_llm):
    fake = make_reviewer_llm([ReviewVerdict(approved=False, feedback="Add a docstring.")])
    monkeypatch.setattr(reviewer, "build_llm", lambda temperature: fake)

    result = reviewer.reviewer_node(_state(code="def hello(): return 'hi'", iterations=1))

    assert result["approved"] is False
    assert result["review"] == "Add a docstring."
