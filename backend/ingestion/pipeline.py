"""
Ingestion pipeline orchestrator.

Runs the pipeline stages in order:
  1. Clone  (cloner.py)
  2. Scan   (scanner.py)
  3. Fetch metadata  (metadata.py)
  4. Static analysis  (analysis/engine.py)
  5. RAG index build  (rag/index.py)

Each stage updates the shared IngestionRecord and persists it to disk.
The orchestrator is called from the FastAPI router and runs in a background
thread (via asyncio.to_thread) so it does not block the event loop during
the blocking git / filesystem operations.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from backend.analysis.engine    import run_analysis, _collect_file_paths
from backend.ingestion.cloner   import clone_repository, save_record, load_record
from backend.ingestion.metadata import fetch_repo_metadata
from backend.ingestion.models   import IngestionRecord, IngestionStatus
from backend.ingestion.scanner  import scan_repository
from backend.ingestion.validator import validate_github_url, canonical_url
from backend.rag.index          import build_index, index_exists

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
    5. Static analysis (blocking → thread, non-fatal)
    6. RAG index build (blocking → thread, non-fatal)

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

    # ── Stage 4: static analysis (non-fatal) ─────────────────────────────
    try:
        await run_analysis(record)
    except Exception as exc:
        logger.warning("Post-ingestion analysis failed for repo_id=%s: %s", repo_id, exc)

    # ── Stage 5: RAG index build (non-fatal) ──────────────────────────────
    if record.scan is not None and not index_exists(repo_id):
        try:
            scan        = record.scan
            file_paths  = _collect_file_paths(scan.file_tree)
            important   = set(scan.important_files)
            # Build language_map from the file tree
            lang_map    = _build_language_map(scan.file_tree)
            await build_index(
                repo_id        = repo_id,
                work_dir       = record.work_dir,
                file_paths     = file_paths,
                important_files = important,
                language_map   = lang_map,
            )
        except Exception as exc:
            logger.warning("Post-ingestion RAG index failed for repo_id=%s: %s", repo_id, exc)

    return record


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_language_map(file_tree) -> dict[str, str]:
    """Flatten the FileNode tree into {rel_path: language}."""
    result: dict[str, str] = {}
    _walk(file_tree, result)
    return result


def _walk(node, out: dict[str, str]) -> None:
    if node.type == "file" and node.language:
        out[node.path] = node.language
    for child in node.children or []:
        _walk(child, out)
