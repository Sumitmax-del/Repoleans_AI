"""
Analysis engine orchestrator.

Runs all analysis passes over an already-ingested repository and produces
a single AnalysisResult.  Persists the result as analysis.json in the
same job directory as record.json.

Usage
-----
    from backend.analysis.engine import run_analysis, load_analysis

    result = await run_analysis(record)   # runs in a thread
    saved  = load_analysis(repo_id)       # reads from disk
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from backend.analysis.architecture import build_arch_layers, build_summary_text
from backend.analysis.directories  import classify_directories
from backend.analysis.entrypoints  import classify_entry_points
from backend.analysis.routes       import detect_routes
from backend.ingestion.cloner      import get_work_root
from backend.ingestion.models      import (
    AnalysisResult, IngestionRecord, IngestionStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _analysis_path(repo_id: str) -> Path:
    return get_work_root() / repo_id / "analysis.json"


def save_analysis(result: AnalysisResult) -> None:
    """Persist *result* to <work_root>/<repo_id>/analysis.json."""
    path = _analysis_path(result.repo_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Analysis saved to %s", path)


def load_analysis(repo_id: str) -> AnalysisResult | None:
    """Return a persisted AnalysisResult, or None if it does not exist."""
    path = _analysis_path(repo_id)
    if not path.exists():
        return None
    try:
        return AnalysisResult.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse analysis.json for repo_id=%s: %s", repo_id, exc)
        return None


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def _run_analysis_sync(record: IngestionRecord) -> AnalysisResult:
    """
    Blocking analysis pass — designed to be called via asyncio.to_thread.

    Raises
    ------
    RuntimeError
        If the record has no completed scan (ingestion not finished).
    """
    if record.status != IngestionStatus.ready or record.scan is None:
        raise RuntimeError(
            f"Cannot analyse repo_id={record.repo_id!r}: "
            f"ingestion status is '{record.status.value}', expected 'ready'."
        )

    scan     = record.scan
    clone_dir = Path(record.work_dir)

    # ── Build file list (POSIX paths relative to clone root) ──────────────
    all_files = _collect_file_paths(scan.file_tree)

    # ── Pass 1: entry-point classification ────────────────────────────────
    logger.info("Analysis [%s]: classifying entry points", record.repo_id)
    entry_points = classify_entry_points(
        clone_dir,
        important_files=scan.important_files,
        all_files=all_files,
    )

    # ── Pass 2: source directory classification ───────────────────────────
    logger.info("Analysis [%s]: classifying directories", record.repo_id)
    source_dirs = classify_directories(clone_dir, scan.file_tree)

    # ── Pass 3: route / API detection ────────────────────────────────────
    logger.info("Analysis [%s]: detecting routes", record.repo_id)
    routes = detect_routes(clone_dir, all_files)

    # ── Pass 4: architecture flow layers ─────────────────────────────────
    logger.info("Analysis [%s]: building architecture layers", record.repo_id)
    arch_layers = build_arch_layers(scan, entry_points, routes)

    # ── Pass 5: summary text ─────────────────────────────────────────────
    summary = build_summary_text(scan, arch_layers, routes, entry_points)

    result = AnalysisResult(
        repo_id=record.repo_id,
        entry_points=entry_points,
        source_directories=source_dirs,
        routes=routes,
        arch_layers=arch_layers,
        summary_text=summary,
        route_count=len(routes),
    )

    save_analysis(result)

    logger.info(
        "Analysis complete: repo_id=%s  routes=%d  entry_points=%d  layers=%d",
        record.repo_id,
        len(routes),
        len(entry_points),
        len(arch_layers),
    )
    return result


async def run_analysis(record: IngestionRecord) -> AnalysisResult:
    """
    Async wrapper: runs the blocking analysis pass in a thread pool.

    Returns the completed :class:`AnalysisResult`.
    Raises :class:`RuntimeError` on failure.
    """
    return await asyncio.to_thread(_run_analysis_sync, record)


# ---------------------------------------------------------------------------
# Helper: flatten FileNode tree into a list of relative file paths
# ---------------------------------------------------------------------------


def _collect_file_paths(node, _acc: list[str] | None = None) -> list[str]:
    """Recursively collect all file paths from a FileNode tree."""
    if _acc is None:
        _acc = []
    if node.type == "file":
        _acc.append(node.path)
    for child in node.children or []:
        _collect_file_paths(child, _acc)
    return _acc
