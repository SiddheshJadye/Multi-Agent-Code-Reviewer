"""Unit tests for the CLI's iteration transcript (terminal-only history)."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from code_reviewer.cli import _print_transcript


def _messages():
    # Two full cycles: reject attempt 1, approve attempt 2.
    return [
        AIMessage(content="# attempt 1 code", name="coder"),
        AIMessage(content="[CHANGES REQUESTED] Add a self-test block.", name="reviewer"),
        AIMessage(content="# attempt 2 code", name="coder"),
        AIMessage(content="[APPROVED] Looks complete now.", name="reviewer"),
    ]


def test_transcript_shows_every_attempt_in_order(capsys):
    _print_transcript({"messages": _messages()})
    out = capsys.readouterr().out

    # Both attempts and both reviews appear...
    assert "# attempt 1 code" in out
    assert "# attempt 2 code" in out
    assert "Add a self-test block." in out
    assert "[APPROVED] Looks complete now." in out

    # ...labelled with the right iteration numbers, in chronological order.
    assert "Iteration 1 - Coder wrote" in out
    assert "Iteration 2 - Coder wrote" in out
    assert out.index("# attempt 1 code") < out.index("# attempt 2 code")


def test_transcript_empty_history_prints_nothing(capsys):
    _print_transcript({"messages": []})
    assert capsys.readouterr().out == ""
