"""Reusable orchestration: run a task through the graph and return final state.

Kept separate from the CLI so the same entrypoint can be used from tests, a
notebook, or another service.
"""

from __future__ import annotations

import logging

from .configuration import get_settings
from .graph import build_graph
from .state import ReviewState

logger = logging.getLogger(__name__)


def initial_state(task: str, max_iterations: int) -> ReviewState:
    """Build the starting state for a run."""
    return {
        "task": task,
        "max_iterations": max_iterations,
        "code": "",
        "review": "",
        "approved": False,
        "iterations": 0,
        "messages": [],
    }


def run_review(
    task: str,
    *,
    max_iterations: int | None = None,
    compiled_graph=None,
) -> ReviewState:
    """Run the Coder/Reviewer loop for ``task`` and return the final state.

    Args:
        task: Natural-language description of the script to build.
        max_iterations: Override for the configured cap. Defaults to settings.
        compiled_graph: Injected graph (used by tests); defaults to the real one.

    Returns:
        The final :class:`ReviewState`, including ``code``, ``approved``,
        ``review``, and ``iterations``.
    """
    if not task or not task.strip():
        raise ValueError("task must be a non-empty string")

    settings = get_settings()
    cap = max_iterations if max_iterations is not None else settings.max_iterations
    graph = compiled_graph if compiled_graph is not None else build_graph()

    logger.info("Starting review loop (max_iterations=%d)", cap)
    final_state: ReviewState = graph.invoke(
        initial_state(task, cap),
        config={"recursion_limit": 2 * cap + 4},
    )
    logger.info(
        "Finished after %d iteration(s); approved=%s",
        final_state.get("iterations", 0),
        final_state.get("approved", False),
    )
    return final_state
