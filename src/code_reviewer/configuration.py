"""Runtime configuration, loaded from environment / ``.env``.

All tunables live here so nodes and the graph stay free of magic values and the
whole system is configurable without code changes (12-factor style).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Field names map to UPPER_SNAKE_CASE environment variables case-insensitively
    (e.g. ``model_name`` <- ``MODEL_NAME``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    google_api_key: str = Field(
        default="",
        description="Gemini API key. If empty, the Google client falls back to "
        "GOOGLE_API_KEY in the process environment.",
    )
    model_name: str = Field(default="gemini-3.1-flash-lite")
    coder_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    reviewer_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

    # --- Control flow ---
    max_iterations: int = Field(
        default=3,
        ge=1,
        description="Maximum Coder<->Reviewer cycles before forcing a stop.",
    )

    # --- Observability ---
    log_level: str = Field(default="INFO")

    @property
    def recursion_limit(self) -> int:
        """LangGraph recursion backstop.

        Each cycle executes two nodes (coder + reviewer); add headroom for the
        entry edge so a legitimate ``max_iterations`` run never trips this.
        """
        return 2 * self.max_iterations + 4


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
