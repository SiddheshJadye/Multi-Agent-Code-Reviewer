"""End-to-end graph tests using fake LLMs (no network).

These exercise the full cyclic collaboration and both stop conditions.
"""

from __future__ import annotations

from code_reviewer.nodes import coder, reviewer
from code_reviewer.runner import run_review
from code_reviewer.state import ReviewVerdict


def _wire_fakes(monkeypatch, coder_llm, reviewer_llm):
    monkeypatch.setattr(coder, "build_llm", lambda temperature: coder_llm)
    monkeypatch.setattr(reviewer, "build_llm", lambda temperature: reviewer_llm)


def test_loops_until_approved(monkeypatch, make_coder_llm, make_reviewer_llm):
    # Coder writes v1 (full), then revises via a SEARCH/REPLACE edit; Reviewer
    # rejects v1, approves v2. Exercises the real surgical-edit path end-to-end.
    coder_llm = make_coder_llm(
        ["# v1", "<<<<<<< SEARCH\n# v1\n=======\n# v2 improved\n>>>>>>> REPLACE"]
    )
    reviewer_llm = make_reviewer_llm(
        [
            ReviewVerdict(approved=False, feedback="Add a docstring."),
            ReviewVerdict(approved=True, feedback="All good now."),
        ]
    )
    _wire_fakes(monkeypatch, coder_llm, reviewer_llm)

    final = run_review("write something", max_iterations=3)

    assert final["approved"] is True
    assert final["iterations"] == 2
    assert final["code"] == "# v2 improved"
    # Audit trail: 2 coder turns + 2 reviewer turns.
    assert len(final["messages"]) == 4


def test_stops_at_max_iterations_without_approval(
    monkeypatch, make_coder_llm, make_reviewer_llm
):
    # Reviewer never approves; loop must stop at the cap. Revisions emit a
    # (no-op) edit block that applies cleanly, so the Coder runs once per cycle.
    coder_llm = make_coder_llm(
        ["# attempt", "<<<<<<< SEARCH\n# attempt\n=======\n# attempt\n>>>>>>> REPLACE"]
    )
    reviewer_llm = make_reviewer_llm(
        [ReviewVerdict(approved=False, feedback="Still not good enough.")]
    )
    _wire_fakes(monkeypatch, coder_llm, reviewer_llm)

    final = run_review("write something", max_iterations=3)

    assert final["approved"] is False
    assert final["iterations"] == 3  # exactly the cap, no more
    assert coder_llm.calls == 3  # Coder invoked exactly once per iteration


def test_approves_on_first_pass(monkeypatch, make_coder_llm, make_reviewer_llm):
    coder_llm = make_coder_llm(["print('perfect')"])
    reviewer_llm = make_reviewer_llm([ReviewVerdict(approved=True, feedback="Perfect.")])
    _wire_fakes(monkeypatch, coder_llm, reviewer_llm)

    final = run_review("write something", max_iterations=3)

    assert final["approved"] is True
    assert final["iterations"] == 1


def test_empty_task_rejected():
    import pytest

    with pytest.raises(ValueError):
        run_review("   ")
