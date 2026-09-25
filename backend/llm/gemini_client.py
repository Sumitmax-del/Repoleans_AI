"""Gemini 1.5 Flash LLM client.

Implements the LLMClient protocol defined in backend/llm/provider.py.
Requires google-generativeai (uncomment in requirements.txt for Sub-Task 4).
"""

from __future__ import annotations

import os
from typing import AsyncIterator


class GeminiClient:
    """Thin async wrapper around the Gemini GenerativeModel streaming API."""

    MODEL = "gemini-1.5-flash"

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file. "
                "Get a free key at https://aistudio.google.com"
            )
        # Import here so the module can be present without the package installed
        import google.generativeai as genai  # noqa: PLC0415

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(self.MODEL)

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """Yield response text tokens streamed from Gemini."""
        response = self._model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
