"""Unit tests for the stop-condition routing logic (no LLM involved)."""

from __future__ import annotations

from langgraph.graph import END

from code_reviewer.graph import CODER, route_after_review


def _state(**overrides):
    base = {
        "task": "t",
        "max_iterations": 3,
        "code": "print(1)",
        "review": "",
        "approved": False,
        "iterations": 1,
        "messages": [],
    }
    base.update(overrides)
    return base


def test_approved_stops():
    assert route_after_review(_state(approved=True, iterations=1)) == END


def test_max_iterations_stops_even_if_not_approved():
    assert route_after_review(_state(approved=False, iterations=3, max_iterations=3)) == END


def test_below_max_and_not_approved_loops_back():
    assert route_after_review(_state(approved=False, iterations=1, max_iterations=3)) == CODER


def test_approval_wins_over_iteration_cap():
    # Approved on the final allowed iteration -> still stop (approved path).
    assert route_after_review(_state(approved=True, iterations=3, max_iterations=3)) == END
