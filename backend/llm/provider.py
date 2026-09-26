"""LLM provider factory.

Reads the LLM_PROVIDER environment variable and returns an appropriate client.
To add a new provider:
  1. Create backend/llm/<provider>_client.py with a class that implements
     the LLMClient protocol below.
  2. Add a branch in get_llm_client().
  3. Set LLM_PROVIDER=<provider> in .env.

Supported providers
-------------------
echo    (default when LLM_PROVIDER is unset or set to 'echo')
    Zero-dependency echo client.  No API key required.  Returns a structured
    summary of retrieved context — useful for testing and offline development.

gemini  (set LLM_PROVIDER=gemini + GEMINI_API_KEY)
    Google Gemini 1.5 Flash via google-generativeai.  Free tier available at
    https://aistudio.google.com.  Requires: pip install google-generativeai
"""

from __future__ import annotations

import os
from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Minimal interface every LLM client must satisfy."""

    def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Return an async iterable of text tokens.

        Implementations are typically async generator functions (``async def``
        with ``yield``), so callers should iterate directly:

            async for token in client.stream_response(prompt):
                ...
        """
        ...


def get_llm_client() -> LLMClient:
    """Return the LLM client configured by the LLM_PROVIDER env var."""
    provider = os.getenv("LLM_PROVIDER", "echo").lower().strip()

    if provider == "echo":
        from backend.llm.echo_client import EchoClient  # noqa: PLC0415

        return EchoClient()

    if provider == "gemini":
        # Requires: pip install google-generativeai  (see requirements.txt)
        from backend.llm.gemini_client import GeminiClient  # noqa: PLC0415

        return GeminiClient()

    raise ValueError(
        f"Unsupported LLM_PROVIDER='{provider}'. "
        "Supported values: 'echo' (default, no key needed), 'gemini' (GEMINI_API_KEY required). "
        "See backend/llm/provider.py to add a new provider."
    )
