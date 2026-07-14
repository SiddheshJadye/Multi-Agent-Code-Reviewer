"""Unit tests for the history-aware reviewer prompt."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from code_reviewer.prompts import reviewer_user_prompt


def test_first_review_is_full_from_scratch():
    # History holds only the current Coder attempt -> no prior review yet.
    history = [AIMessage(content="# v1", name="coder")]
    prompt = reviewer_user_prompt("do X", "# v1", history)

    assert "Submitted script" in prompt
    assert "History of this task" not in prompt


def test_first_review_with_empty_history():
    prompt = reviewer_user_prompt("do X", "# v1", [])
    assert "Submitted script" in prompt


def test_followup_review_includes_history_and_focuses_on_changes():
    history = [
        AIMessage(content="# v1", name="coder"),
        AIMessage(content="[CHANGES REQUESTED] Add input validation.", name="reviewer"),
        AIMessage(content="# v2 with validation", name="coder"),
    ]
    prompt = reviewer_user_prompt("do X", "# v2 with validation", history)

    # It remembers the earlier attempt and its own prior feedback...
    assert "History of this task" in prompt
    assert "Add input validation." in prompt
    assert "Coder attempt #1" in prompt
    # ...shows the latest code to review...
    assert "# v2 with validation" in prompt
    # ...and instructs an incremental, change-focused review.
    assert "changes you requested" in prompt


def test_followup_does_not_duplicate_latest_attempt_in_history():
    history = [
        AIMessage(content="# v1", name="coder"),
        AIMessage(content="[CHANGES REQUESTED] Fix bug.", name="reviewer"),
        AIMessage(content="# v2", name="coder"),
    ]
    prompt = reviewer_user_prompt("do X", "# v2", history)

    # The latest attempt (#2) is shown once, as "Latest script", not as a
    # numbered history entry.
    assert "Coder attempt #2" not in prompt
    assert "Coder attempt #1" in prompt
