"""Graph state and structured schemas.

The state is the single source of truth threaded through every node. The
``ReviewVerdict`` Pydantic model is what the Reviewer emits via structured
output, giving us a clean boolean stop condition instead of parsing prose.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class ReviewVerdict(BaseModel):
    """Structured output returned by the Reviewer agent."""

    approved: bool = Field(
        description="True only if the code fully satisfies the task and is "
        "production-ready with no remaining required changes."
    )
    feedback: str = Field(
        description="If not approved: specific, actionable changes the Coder "
        "must make. If approved: a brief note on why it passes."
    )


class ReviewState(TypedDict):
    """State passed between the Coder and Reviewer nodes."""

    # Inputs
    task: str
    max_iterations: int

    # Working values
    code: str
    review: str
    approved: bool
    iterations: int

    # Full audit trail of agent turns (append-only via the add_messages reducer)
    messages: Annotated[list[AnyMessage], add_messages]
