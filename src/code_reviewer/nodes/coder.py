"""Coder node: writes the first script, then makes surgical edits on revisions."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..configuration import get_settings
from ..edits import apply_edits, parse_edit_blocks
from ..llm import build_llm
from ..prompts import (
    CODER_EDIT_SYSTEM_PROMPT,
    CODER_SYSTEM_PROMPT,
    coder_edit_prompt,
    coder_user_prompt,
)
from ..state import ReviewState
from ..utils import message_text, strip_code_fences

logger = logging.getLogger(__name__)


def coder_node(state: ReviewState) -> dict:
    """Produce the next version of the script.

    First iteration: write a complete script from the task. Later iterations:
    ask the model for surgical SEARCH/REPLACE edits against its previous code and
    apply them, so untouched code stays byte-for-byte identical. If the edits do
    not apply cleanly, fall back to a full rewrite (never a broken partial apply).
    """
    settings = get_settings()
    iteration = state.get("iterations", 0) + 1
    prev_code = state.get("code", "")
    review = state.get("review", "")
    task = state["task"]

    llm = build_llm(settings.coder_temperature)

    if not prev_code:
        logger.info("Coder: writing initial script (iteration %d)", iteration)
        code = _full_write(llm, task)
    else:
        logger.info("Coder: revising via surgical edits (iteration %d)", iteration)
        code = _revise(llm, task, prev_code, review)

    return {
        "code": code,
        "iterations": iteration,
        "messages": [AIMessage(content=code, name="coder")],
    }


def _full_write(llm, task: str, prev_code: str = "", review: str = "") -> str:
    """Generate a complete script (initial write, or full-rewrite fallback)."""
    messages = [
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(content=coder_user_prompt(task=task, code=prev_code, review=review)),
    ]
    response = llm.invoke(messages)
    return strip_code_fences(message_text(response.content))


def _revise(llm, task: str, prev_code: str, review: str) -> str:
    """Ask for SEARCH/REPLACE edits and apply them; fall back to a full rewrite."""
    messages = [
        SystemMessage(content=CODER_EDIT_SYSTEM_PROMPT),
        HumanMessage(content=coder_edit_prompt(task=task, code=prev_code, review=review)),
    ]
    response = llm.invoke(messages)
    blocks = parse_edit_blocks(message_text(response.content))
    new_code, ok = apply_edits(prev_code, blocks)

    if ok:
        logger.info("Coder: applied %d surgical edit(s)", len(blocks))
        return new_code

    logger.warning(
        "Coder: %d edit block(s) did not apply cleanly; falling back to full rewrite",
        len(blocks),
    )
    return _full_write(llm, task, prev_code=prev_code, review=review)
