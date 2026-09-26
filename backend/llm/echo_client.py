"""
Echo LLM client — zero-dependency provider for local testing and CI.

Returns a structured plain-text response that echoes the retrieved context
back to the caller without calling any external API.  Useful for:

- Testing the full POST /api/chat → SSE pipeline without an API key
- CI/CD validation runs
- Offline development

Activate with:  LLM_PROVIDER=echo  (in .env or environment)
"""

from __future__ import annotations

import re
from typing import AsyncIterator


class EchoClient:
    """
    Simulates an LLM response by producing a deterministic summary of the
    prompt's context blocks.  No network calls, no dependencies.
    """

    # Regex to extract citation labels from the context header lines
    _CITATION_RE = re.compile(r"### \[([^\]]+)\]")

    async def stream_response(self, prompt: str) -> AsyncIterator[str]:
        """
        Yield a synthesised answer, token by token (word by word).

        The response lists every cited file/line range found in the prompt
        and confirms that the context was received, making it easy to verify
        the SSE streaming pipeline end-to-end.
        """
        citations = self._CITATION_RE.findall(prompt)

        if citations:
            lines = [
                "**Echo provider** — no LLM API key required for this response.\n\n",
                "The following context blocks were retrieved from the repository:\n\n",
            ]
            for i, cit in enumerate(citations, 1):
                lines.append(f"{i}. `{cit}`\n")
            lines.append(
                "\nTo receive AI-generated answers, set `LLM_PROVIDER=gemini` "
                "and add your `GEMINI_API_KEY` to `.env`.\n"
            )
        else:
            lines = [
                "**Echo provider** — no context was retrieved for this query.\n\n",
                "The repository does not contain enough information to answer this question.\n",
            ]

        response_text = "".join(lines)

        # Stream word-by-word so the SSE consumer is exercised properly
        for word in response_text.split(" "):
            yield word + " "

    # Make it easy to detect in tests
    provider_name = "echo"
