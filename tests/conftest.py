"""Shared test doubles.

These fakes let the whole graph run offline with zero API calls, so tests are
deterministic and CI needs no GOOGLE_API_KEY.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from code_reviewer.state import ReviewVerdict


class FakeCoderLLM:
    """Stands in for the Coder's chat model.

    Returns the next canned code string each time ``invoke`` is called.
    """

    def __init__(self, code_outputs: list[str]):
        self._outputs = list(code_outputs)
        self.calls = 0

    def invoke(self, messages):
        code = self._outputs[min(self.calls, len(self._outputs) - 1)]
        self.calls += 1
        return AIMessage(content=f"```python\n{code}\n```")


class _StructuredReviewer:
    def __init__(self, parent: "FakeReviewerLLM"):
        self._parent = parent

    def invoke(self, messages) -> ReviewVerdict:
        verdict = self._parent._verdicts[
            min(self._parent.calls, len(self._parent._verdicts) - 1)
        ]
        self._parent.calls += 1
        return verdict


class FakeReviewerLLM:
    """Stands in for the Reviewer's chat model, including structured output."""

    def __init__(self, verdicts: list[ReviewVerdict]):
        self._verdicts = list(verdicts)
        self.calls = 0

    def with_structured_output(self, schema):
        return _StructuredReviewer(self)


@pytest.fixture
def make_coder_llm():
    return FakeCoderLLM


@pytest.fixture
def make_reviewer_llm():
    return FakeReviewerLLM
