"""Unit tests for helper functions."""

from __future__ import annotations

from code_reviewer.utils import message_text, strip_code_fences


def test_extracts_python_fence():
    text = "Here you go:\n```python\nprint('hi')\n```\nDone."
    assert strip_code_fences(text) == "print('hi')"


def test_extracts_bare_fence():
    assert strip_code_fences("```\nx = 1\n```") == "x = 1"


def test_returns_trimmed_text_without_fence():
    assert strip_code_fences("  x = 1  ") == "x = 1"


def test_empty_input():
    assert strip_code_fences("") == ""


def test_message_text_plain_string():
    assert message_text("hello") == "hello"


def test_message_text_list_of_blocks():
    content = [
        {"type": "text", "text": "print("},
        {"type": "text", "text": "'hi')"},
    ]
    assert message_text(content) == "print('hi')"


def test_message_text_mixed_list_and_none():
    assert message_text(["a", {"text": "b"}]) == "ab"
    assert message_text(None) == ""
