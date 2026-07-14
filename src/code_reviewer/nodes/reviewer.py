"""Reviewer node: critiques the script and emits a structured verdict."""

from __future__ import annotations

import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..configuration import get_settings
from ..llm import build_llm
from ..prompts import REVIEWER_SYSTEM_PROMPT, reviewer_user_prompt
from ..state import ReviewState, ReviewVerdict

logger = logging.getLogger(__name__)


def reviewer_node(state: ReviewState) -> dict:
    """Review the current ``code`` and return an approval verdict + feedback.

    Uses structured output so the graph gets a clean ``approved`` boolean rather
    than having to parse free-form prose for a stop signal.
    """
    settings = get_settings()
    logger.info("Reviewer: reviewing code (iteration %d)", state.get("iterations", 0))

    llm = build_llm(settings.reviewer_temperature).with_structured_output(ReviewVerdict)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(
            content=reviewer_user_prompt(
                task=state["task"],
                code=state.get("code", ""),
                # Full memory of the task so far: earlier attempts + prior reviews.
                history=state.get("messages", []),
            )
        ),
    ]

    verdict: ReviewVerdict = llm.invoke(messages)

    logger.info(
        "Reviewer: verdict = %s", "APPROVED" if verdict.approved else "CHANGES REQUESTED"
    )

    prefix = "APPROVED" if verdict.approved else "CHANGES REQUESTED"
    return {
        "approved": verdict.approved,
        "review": verdict.feedback,
        "messages": [
            AIMessage(content=f"[{prefix}] {verdict.feedback}", name="reviewer")
        ],
    }
