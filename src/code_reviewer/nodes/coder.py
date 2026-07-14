"""Coder node: generates or refines the Python script."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..configuration import get_settings
from ..llm import build_llm
from ..prompts import CODER_SYSTEM_PROMPT, coder_user_prompt
from ..state import ReviewState
from ..utils import message_text, strip_code_fences

logger = logging.getLogger(__name__)


def coder_node(state: ReviewState) -> dict:
    """Produce the next version of the script.

    On the first pass it writes from the task alone; on later passes it revises
    the previous ``code`` using the Reviewer's ``review``. Increments the
    ``iterations`` counter, which drives the loop's stop condition.
    """
    settings = get_settings()
    iteration = state.get("iterations", 0) + 1

    logger.info("Coder: generating code (iteration %d)", iteration)

    llm = build_llm(settings.coder_temperature)
    messages = [
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(
            content=coder_user_prompt(
                task=state["task"],
                code=state.get("code", ""),
                review=state.get("review", ""),
            )
        ),
    ]

    response = llm.invoke(messages)
    code = strip_code_fences(message_text(response.content))

    logger.debug("Coder: produced %d chars of code", len(code))

    return {
        "code": code,
        "iterations": iteration,
        "messages": [AIMessage(content=code, name="coder")],
    }
