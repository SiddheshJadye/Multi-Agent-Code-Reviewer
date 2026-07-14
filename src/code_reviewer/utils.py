"""Small, dependency-light helpers shared across the package."""

from __future__ import annotations

import logging
import re
from typing import Any

_CODE_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*\n(?P<body>.*?)```",
    re.DOTALL | re.IGNORECASE,
)

_LOGGING_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once, idempotently."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _LOGGING_CONFIGURED = True


def message_text(content: Any) -> str:
    """Normalize a chat message's ``content`` to a plain string.

    Modern multimodal models (e.g. newer Gemini) may return ``content`` as a list
    of content blocks (dicts like ``{"type": "text", "text": ...}`` or plain
    strings) rather than a single string. This flattens either shape to text.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


def strip_code_fences(text: str) -> str:
    """Return runnable Python from an LLM response.

    Extracts the first fenced code block if present; otherwise returns the
    trimmed text unchanged. This keeps the Coder robust whether or not the model
    wraps its output in Markdown fences.
    """
    if not text:
        return ""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group("body").strip()
    return text.strip()
