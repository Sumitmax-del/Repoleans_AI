"""Gemini LLM client — uses the modern google-genai SDK.

Implements the LLMClient protocol defined in backend/llm/provider.py.
Requires: pip install google-genai
"""

from __future__ import annotations

import os
from typing import AsyncIterator


class GeminiClient:
    """Async-native Gemini client using the google-genai SDK."""

    MODEL = "gemini-3.5-flash-lite"

    _SYSTEM_INSTRUCTION = (
        "You are RepoLens, an AI assistant that answers questions about "
        "software repositories.  You will receive code context extracted "
        "from the repository.  Use that context to answer the user's "
        "question accurately.  Cite file paths and line ranges where "
        "relevant using the format [file:start-end].  Be concise and "
        "helpful.  When showing code use markdown fenced code blocks."
    )

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file. "
                "Get a free key at https://aistudio.google.com"
            )
        from google import genai  # noqa: PLC0415

        self._client = genai.Client(api_key=api_key)

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """Yield response text tokens streamed from Gemini (async-native)."""
        from google.genai import types  # noqa: PLC0415

        response = self._client.models.generate_content_stream(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=self._SYSTEM_INSTRUCTION,
            ),
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
