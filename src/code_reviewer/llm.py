"""Gemini chat-model factory.

Kept deliberately thin so nodes depend on ``build_llm`` (easy to monkeypatch in
tests) rather than constructing provider clients themselves.
"""

from __future__ import annotations

from langchain_google_genai import ChatGoogleGenerativeAI

from .configuration import get_settings


def build_llm(temperature: float) -> ChatGoogleGenerativeAI:
    """Create a Gemini chat model at the given temperature.

    The API key is taken from settings when provided, otherwise the underlying
    client falls back to ``GOOGLE_API_KEY`` in the environment.
    """
    settings = get_settings()
    kwargs: dict = {
        "model": settings.model_name,
        "temperature": temperature,
    }
    if settings.google_api_key:
        kwargs["google_api_key"] = settings.google_api_key
    return ChatGoogleGenerativeAI(**kwargs)
