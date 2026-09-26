"""
RAG prompt builder.

Assembles a grounded system prompt from a list of RetrievalResult objects
so that the LLM is constrained to answer only from the provided repository
context.

Prompt structure
----------------
<system instructions>
<retrieved context blocks, each labelled file:start-end>
<question>

The builder also returns the deduplicated citation list so the router can
attach it to the final SSE event without re-parsing the LLM response.
"""

from __future__ import annotations

from backend.rag.models import RetrievalResult

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------

# Maximum total characters of context to include in the prompt.
# Keeps the prompt within reasonable token limits for all LLM providers.
_MAX_CONTEXT_CHARS = 12_000

# Number of characters reserved for the system instructions + question wrapper.
_PROMPT_OVERHEAD_CHARS = 800

_SYSTEM_INSTRUCTIONS = """\
You are RepoLens, an AI assistant that answers questions about software repositories.

Rules you MUST follow:
1. Answer ONLY using the code context provided below.  Do not speculate or invent information.
2. For every factual claim, cite the file and line range in the format [file:start-end].
3. If the provided context does not contain enough information to answer the question,
   respond with exactly: "The repository does not contain enough information to answer this question."
4. Be concise.  Prefer short, direct answers over long explanations.
5. When showing code snippets use markdown fenced code blocks with the language identifier.
"""

_CONTEXT_HEADER = "## Repository Context\n\n"
_CONTEXT_BLOCK_TEMPLATE = "### [{citation}]\n```{language}\n{text}\n```\n"
_QUESTION_HEADER = "\n## Question\n\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_prompt(
    question: str,
    results: list[RetrievalResult],
) -> tuple[str, list[dict]]:
    """
    Build the full prompt string and the deduplicated citation list.

    Parameters
    ----------
    question:
        The user's natural-language question.
    results:
        Ranked retrieval results from ``backend.rag.retriever.retrieve``.

    Returns
    -------
    (prompt, citations)
        ``prompt``    — the full string to send to the LLM.
        ``citations`` — list of ``{"file_path", "start_line", "end_line"}`` dicts,
                        in rank order, deduplicated by chunk_id.
    """
    context_budget = _MAX_CONTEXT_CHARS - _PROMPT_OVERHEAD_CHARS

    context_blocks: list[str] = []
    citations: list[dict] = []
    seen_chunk_ids: set[str] = set()
    used_chars = 0

    for r in results:
        if r.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(r.chunk_id)

        citation_label = f"{r.file_path}:{r.start_line}-{r.end_line}"
        language = r.language.lower() if r.language else ""

        block = _CONTEXT_BLOCK_TEMPLATE.format(
            citation=citation_label,
            language=language,
            text=r.text,
        )

        block_chars = len(block)
        if used_chars + block_chars > context_budget:
            # Truncate the text so we can still include a partial block
            remaining = context_budget - used_chars
            if remaining < 120:
                break  # not worth including a near-empty snippet
            truncated_text = r.text[: remaining - 80] + "\n… (truncated)"
            block = _CONTEXT_BLOCK_TEMPLATE.format(
                citation=citation_label,
                language=language,
                text=truncated_text,
            )
            context_blocks.append(block)
            citations.append({
                "file_path":  r.file_path,
                "start_line": r.start_line,
                "end_line":   r.end_line,
            })
            break

        context_blocks.append(block)
        citations.append({
            "file_path":  r.file_path,
            "start_line": r.start_line,
            "end_line":   r.end_line,
        })
        used_chars += block_chars

    # Build the full prompt
    prompt = (
        _SYSTEM_INSTRUCTIONS
        + "\n"
        + _CONTEXT_HEADER
        + "".join(context_blocks)
        + _QUESTION_HEADER
        + question.strip()
        + "\n"
    )

    return prompt, citations
