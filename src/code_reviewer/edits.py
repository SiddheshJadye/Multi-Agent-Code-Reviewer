"""Parse and apply SEARCH/REPLACE edit blocks (surgical, Aider-style edits).

The Coder emits one or more blocks in this exact form on a revision::

    <<<<<<< SEARCH
    <lines copied verbatim from the current script>
    =======
    <replacement lines>
    >>>>>>> REPLACE

A deterministic applier finds each SEARCH text in the current code and replaces
it. Matching is exact and must be unique — the same guarantee an editor's
find-and-replace gives. If a block does not match exactly once, application fails
and the caller falls back to a full rewrite, so we never apply an ambiguous edit.
"""

from __future__ import annotations

import re

_EDIT_RE = re.compile(
    r"<{5,}[ \t]*SEARCH[ \t]*\n"
    r"(?P<search>.*?)\n"
    r"[ \t]*={5,}[ \t]*\n"
    r"(?P<replace>.*?)"
    r"\n?[ \t]*>{5,}[ \t]*REPLACE",
    re.DOTALL,
)


def parse_edit_blocks(text: str) -> list[tuple[str, str]]:
    """Extract ``(search, replace)`` pairs from LLM output.

    Any surrounding prose or Markdown fences are ignored — only the blocks
    between the SEARCH/REPLACE markers are captured.
    """
    if not text:
        return []
    return [(m.group("search"), m.group("replace")) for m in _EDIT_RE.finditer(text)]


def apply_edits(code: str, blocks: list[tuple[str, str]]) -> tuple[str, bool]:
    """Apply edit blocks to ``code``.

    Returns ``(new_code, True)`` if every block matched exactly once and was
    applied. If there are no blocks, or any block's SEARCH text is missing or
    ambiguous (matches != 1), returns ``(code, False)`` unchanged — signalling
    the caller to fall back to a full rewrite.
    """
    if not blocks:
        return code, False

    new_code = code
    for search, replace in blocks:
        if not search:
            return code, False
        if new_code.count(search) != 1:  # 0 = not found, >1 = ambiguous
            return code, False
        new_code = new_code.replace(search, replace, 1)

    return new_code, True
