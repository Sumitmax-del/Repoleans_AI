"""LLM provider factory.

Reads the LLM_PROVIDER environment variable and returns an appropriate client.
Currently only 'gemini' is implemented.  To add a new provider:
  1. Create backend/llm/<provider>_client.py with a class that implements
     the LLMClient protocol below.
  2. Add a branch in get_llm_client().
  3. Set LLM_PROVIDER=<provider> in .env.
"""

from __future__ import annotations

import os
from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM client must satisfy."""

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """Yield response text tokens as they arrive from the model."""
        ...


def get_llm_client() -> LLMClient:
    """Return the LLM client configured by the LLM_PROVIDER env var."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider == "gemini":
        # Import lazily so the package can be loaded without google-generativeai
        # installed (it's commented out in requirements.txt until Sub-Task 4).
        from backend.llm.gemini_client import GeminiClient  # noqa: PLC0415

        return GeminiClient()

    raise ValueError(
        f"Unsupported LLM_PROVIDER='{provider}'. "
        "Supported values: 'gemini'. "
        "See backend/llm/provider.py to add a new provider."
    )
