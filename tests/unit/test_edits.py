"""Unit tests for the SEARCH/REPLACE parser and applier."""

from __future__ import annotations

from code_reviewer.edits import apply_edits, parse_edit_blocks

BLOCK = (
    "<<<<<<< SEARCH\n"
    "def add(a, b):\n"
    "    return a - b\n"
    "=======\n"
    "def add(a, b):\n"
    "    return a + b\n"
    ">>>>>>> REPLACE"
)


def test_parse_single_block():
    blocks = parse_edit_blocks(BLOCK)
    assert len(blocks) == 1
    search, replace = blocks[0]
    assert "return a - b" in search
    assert "return a + b" in replace


def test_parse_ignores_surrounding_text_and_fences():
    text = "Here is my edit:\n```\n" + BLOCK + "\n```\nDone."
    assert len(parse_edit_blocks(text)) == 1


def test_parse_multiple_blocks():
    text = BLOCK + "\n\n<<<<<<< SEARCH\nx = 1\n=======\nx = 2\n>>>>>>> REPLACE"
    assert len(parse_edit_blocks(text)) == 2


def test_parse_empty_or_no_blocks():
    assert parse_edit_blocks("") == []
    assert parse_edit_blocks("just some prose, no blocks") == []


def test_apply_clean_edit():
    code = "def add(a, b):\n    return a - b\n"
    new, ok = apply_edits(code, parse_edit_blocks(BLOCK))
    assert ok
    assert "return a + b" in new
    assert "return a - b" not in new


def test_apply_multiple_sequential_edits():
    code = "x = 1\ny = 1\n"
    new, ok = apply_edits(code, [("x = 1", "x = 2"), ("y = 1", "y = 2")])
    assert ok
    assert new == "x = 2\ny = 2\n"


def test_apply_fails_when_search_not_found():
    new, ok = apply_edits("a = 1", [("b = 2", "b = 3")])
    assert not ok
    assert new == "a = 1"  # unchanged -> caller falls back


def test_apply_fails_when_match_is_ambiguous():
    code = "x = 1\nx = 1\n"  # two identical matches
    new, ok = apply_edits(code, [("x = 1", "x = 2")])
    assert not ok
    assert new == code


def test_apply_empty_blocks_is_failure():
    new, ok = apply_edits("a = 1", [])
    assert not ok
    assert new == "a = 1"
