"""
FastAPI router — Ask Repository chat endpoint.

Endpoint
--------
POST /api/chat
    Accept a repo_id + question, retrieve relevant context from the RAG
    index, build a grounded prompt, call the configured LLM, and stream
    the answer back as Server-Sent Events (SSE).

SSE event format
----------------
Every data line is a JSON object.  The client should handle three shapes:

    {"type": "token",  "text": "<partial text>"}
        One or more text tokens from the LLM, emitted as they arrive.

    {"type": "done",   "sources": [{"file_path": "...", "start_line": N, "end_line": N}, …]}
        Signals that the stream is complete.  Carries the deduplicated
        citation list so the frontend can render source chips.

    {"type": "error",  "detail": "<message>"}
        A recoverable error (e.g. LLM unavailable, index missing).
        The stream is closed after this event.

LLM provider
------------
Controlled by the LLM_PROVIDER environment variable (see backend/llm/provider.py).
Default: 'echo'  — no API key required; returns a structured context summary.
Set LLM_PROVIDER=gemini and GEMINI_API_KEY=<key> for AI-generated answers.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.ingestion.cloner   import load_record
from backend.ingestion.models   import IngestionStatus
from backend.llm.provider       import get_llm_client
from backend.rag.prompt_builder import build_prompt
from backend.rag.retriever      import retrieve

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Maximum number of chunks to retrieve for a single question.
_TOP_K = 8


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    repo_id:  str = Field(..., description="Repository ID returned by POST /api/analyze")
    question: str = Field(..., min_length=1, description="Natural-language question about the repository")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/chat")
async def ask_repository(body: ChatRequest) -> StreamingResponse:
    """
    Stream an AI answer grounded in the repository source files.

    Returns a ``text/event-stream`` response.  Each SSE ``data:`` line is
    a JSON object; see module docstring for the three event shapes.
    """
    # ── Validate repo ────────────────────────────────────────────────────────
    record = load_record(body.repo_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ingestion record found for repo_id='{body.repo_id}'. "
                   "Call POST /api/analyze first.",
        )
    if record.status == IngestionStatus.error:
        raise HTTPException(
            status_code=422,
            detail=record.error_message or "Ingestion failed.",
        )
    if record.status != IngestionStatus.ready:
        raise HTTPException(
            status_code=202,
            detail=f"Repository is still being ingested (status={record.status.value}).",
        )

    return StreamingResponse(
        _stream(body.repo_id, body.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable nginx buffering in production
        },
    )


# ---------------------------------------------------------------------------
# SSE generator
# ---------------------------------------------------------------------------


def _sse(obj: dict) -> str:
    """Format a dict as a single SSE data line."""
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def _stream(repo_id: str, question: str):
    """
    Async generator that drives the full RAG → LLM pipeline and yields
    SSE-formatted strings.
    """
    # ── Step 1: retrieve relevant chunks ────────────────────────────────────
    try:
        results = await asyncio.to_thread(retrieve, repo_id, question, _TOP_K)
    except Exception as exc:
        logger.error("Retrieval failed for repo_id=%s: %s", repo_id, exc)
        yield _sse({"type": "error", "detail": "Retrieval failed. Please try again."})
        return

    # ── Step 2: build grounded prompt ────────────────────────────────────────
    prompt, citations = build_prompt(question, results)

    logger.info(
        "chat: repo_id=%s  retrieved=%d  citations=%d  question=%r",
        repo_id, len(results), len(citations), question[:80],
    )

    # ── Step 3: stream LLM response ─────────────────────────────────────────
    try:
        client = get_llm_client()
        async for token in client.stream_response(prompt):
            yield _sse({"type": "token", "text": token})
    except EnvironmentError as exc:
        # Missing API key — surface a helpful message
        logger.warning("LLM not configured: %s", exc)
        yield _sse({
            "type":   "error",
            "detail": str(exc),
        })
        return
    except Exception as exc:
        err_str = str(exc).lower()
        if "429" in str(exc) or "resource" in err_str and "exhaust" in err_str or "quota" in err_str:
            logger.warning("Rate limit hit for repo_id=%s: %s", repo_id, exc)
            yield _sse({
                "type":   "error",
                "detail": "Rate limit exceeded. The free Gemini API allows 5 requests/minute. Please wait about 60 seconds and try again.",
            })
        else:
            logger.error("LLM stream error for repo_id=%s: %s", repo_id, exc)
            yield _sse({"type": "error", "detail": f"LLM request failed: {exc}"})
        return

    # ── Step 4: send done event with citations ───────────────────────────────
    yield _sse({"type": "done", "sources": citations})
