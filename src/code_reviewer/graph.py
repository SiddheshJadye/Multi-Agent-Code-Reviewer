"""The two-agent cyclic graph: Coder <-> Reviewer.

Shape::

    START -> coder -> reviewer -> approved OR max iterations -> END
                          ^                                      |
                          +----------- needs changes ------------+

The exported module-level ``graph`` is what ``langgraph.json`` registers. Building
the graph does not instantiate any LLM (nodes construct models lazily on
invocation), so importing this module is cheap and side-effect free.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from .nodes import coder_node, reviewer_node
from .state import ReviewState

logger = logging.getLogger(__name__)

CODER = "coder"
REVIEWER = "reviewer"


def route_after_review(state: ReviewState) -> str:
    """Decide whether to stop or loop back to the Coder.

    Stop conditions (either ends the run):
      1. The Reviewer approved the code.
      2. We have reached ``max_iterations`` (cost/safety guard).
    Otherwise, cycle back to the Coder for another revision.
    """
    if state.get("approved"):
        logger.info("Stop: reviewer approved.")
        return END

    if state.get("iterations", 0) >= state.get("max_iterations", 3):
        logger.info(
            "Stop: reached max_iterations (%d) without approval.",
            state.get("max_iterations", 3),
        )
        return END

    logger.info("Loop: sending feedback back to coder.")
    return CODER


def build_graph():
    """Construct and compile the Coder/Reviewer state graph."""
    builder = StateGraph(ReviewState)

    builder.add_node(CODER, coder_node)
    builder.add_node(REVIEWER, reviewer_node)

    builder.add_edge(START, CODER)
    builder.add_edge(CODER, REVIEWER)
    builder.add_conditional_edges(
        REVIEWER,
        route_after_review,
        {CODER: CODER, END: END},
    )

    return builder.compile()


# Registered in langgraph.json as `code_reviewer`.
graph = build_graph()
