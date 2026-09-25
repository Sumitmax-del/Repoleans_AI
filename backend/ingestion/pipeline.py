"""
Ingestion pipeline orchestrator.

Runs the three pipeline stages in order:
  1. Clone  (cloner.py)
  2. Scan   (scanner.py)
  3. Fetch metadata  (metadata.py)

Each stage updates the shared IngestionRecord and persists it to disk.
The orchestrator is called from the FastAPI router and runs in a background
thread (via asyncio.to_thread) so it does not block the event loop during
the blocking git / filesystem operations.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.analysis.engine    import run_analysis
from backend.ingestion.cloner   import clone_repository, save_record, load_record
from backend.ingestion.metadata import fetch_repo_metadata
from backend.ingestion.models   import IngestionRecord, IngestionStatus
from backend.ingestion.scanner  import scan_repository
from backend.ingestion.validator import validate_github_url, canonical_url

logger = logging.getLogger(__name__)


async def run_ingestion(repo_url: str, repo_id: str) -> IngestionRecord:
    """
    Full ingestion pipeline for *repo_url*.

    Stages
    ------
    1. Validate URL and derive owner/repo
    2. Clone the repository (blocking → thread)
    3. Scan the file system (blocking → thread)
    4. Fetch GitHub API metadata (async)
    5. Persist the final record

    Returns the completed :class:`IngestionRecord`.
    Raises :class:`RuntimeError` with a human-readable message on failure.
    """
    # ── Stage 0: validate ─────────────────────────────────────────────────
    from backend.ingestion.validator import ValidationError  # local to avoid circular
    try:
        owner, repo = validate_github_url(repo_url)
    except ValidationError as exc:
        raise RuntimeError(str(exc)) from exc

    clone_url = canonical_url(owner, repo)

    # ── Stage 1: clone (blocking) ─────────────────────────────────────────
    try:
        record = await asyncio.to_thread(clone_repository, clone_url, repo_id)
    except RuntimeError:
        raise  # already has a friendly message from cloner.py

    # ── Stage 2: scan (blocking) ──────────────────────────────────────────
    record.status = IngestionStatus.scanning
    save_record(record)

    try:
        scan = await asyncio.to_thread(scan_repository, Path(record.work_dir))
    except Exception as exc:
        record.status = IngestionStatus.error
        record.error_message = f"File scan failed: {exc}"
        save_record(record)
        raise RuntimeError(record.error_message) from exc

    record.scan = scan

    # ── Stage 3: metadata (async, best-effort) ────────────────────────────
    try:
        metadata = await fetch_repo_metadata(owner, repo)
        record.metadata = metadata
    except Exception as exc:
        # Metadata failure is non-fatal; log and continue
        logger.warning("Metadata fetch failed for %s/%s: %s", owner, repo, exc)

    # ── Finalise ingestion ────────────────────────────────────────────────
    record.status = IngestionStatus.ready
    save_record(record)

    logger.info(
        "Ingestion complete: repo_id=%s  files=%d  lang=%s",
        repo_id,
        record.scan.file_count if record.scan else 0,
        record.scan.primary_language if record.scan else "?",
    )

    # ── Stage 4: static analysis (async, runs immediately after ingestion) ─
    try:
        await run_analysis(record)
    except Exception as exc:
        # Analysis failure is non-fatal; the ingestion record remains 'ready'
        logger.warning("Post-ingestion analysis failed for repo_id=%s: %s", repo_id, exc)

    return record
