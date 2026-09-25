"""
FastAPI router — repository ingestion endpoints.

Endpoints
---------
POST /api/analyze
    Accept a GitHub URL, run the full ingestion pipeline, return repo_id.

GET  /api/summary/{repo_id}
    Return the RepoSummary for an already-ingested repository.

GET  /api/structure/{repo_id}
    Return the full FileNode tree for an already-ingested repository.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.analysis.engine    import load_analysis, run_analysis
from backend.ingestion.cloner   import load_record, repo_id_for
from backend.ingestion.models   import AnalysisResult, FileNode, IngestionStatus
from backend.ingestion.pipeline import run_ingestion
from backend.ingestion.validator import ValidationError, validate_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingestion"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# (These are the shapes the frontend api/client.ts already expects.)
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="Public GitHub repository URL")


class AnalyzeResponse(BaseModel):
    repo_id: str
    status: str


class RepoSummary(BaseModel):
    """Shape returned by GET /api/summary/:repo_id — matches frontend types.ts."""

    repo_name:        str
    repo_url:         str
    description:      str
    primary_language: str
    languages:        list[str]
    frameworks:       list[str]
    file_count:       int
    dependencies:     dict[str, list[str]]
    config_files:     list[str]
    important_files:  list[str]


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------


@router.post("/analyze", response_model=AnalyzeResponse, status_code=202)
async def analyze_repository(body: AnalyzeRequest) -> AnalyzeResponse:
    """
    Trigger repository ingestion.

    Validates the URL, clones the repo, scans the file system, and fetches
    GitHub metadata.  Returns immediately with ``repo_id`` and ``status``.

    The call is **synchronous** from the client's perspective — it waits for
    the full pipeline to finish before responding.  For a hackathon this is
    fine; in production you would move the heavy work into a background task
    and poll a status endpoint.
    """
    # ── Validate URL ──────────────────────────────────────────────────────
    try:
        validate_github_url(body.repo_url)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    repo_id = repo_id_for(body.repo_url)

    # ── Run pipeline ──────────────────────────────────────────────────────
    try:
        record = await run_ingestion(body.repo_url, repo_id)
    except RuntimeError as exc:
        logger.error("Ingestion failed for %s: %s", body.repo_url, exc)
        # Surface the friendly error from the pipeline
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return AnalyzeResponse(repo_id=record.repo_id, status=record.status.value)


# ---------------------------------------------------------------------------
# GET /api/summary/{repo_id}
# ---------------------------------------------------------------------------


@router.get("/summary/{repo_id}", response_model=RepoSummary)
async def get_summary(repo_id: str) -> RepoSummary:
    """Return the repository summary for an already-ingested repo."""
    record = load_record(repo_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ingestion record found for repo_id='{repo_id}'. "
                   "Call POST /api/analyze first.",
        )

    if record.status == IngestionStatus.error:
        raise HTTPException(
            status_code=422,
            detail=record.error_message or "Ingestion failed.",
        )

    if record.status != IngestionStatus.ready or record.scan is None:
        raise HTTPException(
            status_code=202,
            detail=f"Ingestion is still in progress (status={record.status.value}).",
        )

    scan = record.scan
    meta = record.metadata

    return RepoSummary(
        repo_name        = meta.repo_name  if meta else record.repo_url.split("github.com/")[-1].rstrip(".git"),
        repo_url         = meta.repo_url   if meta else record.repo_url,
        description      = meta.description if meta else "",
        primary_language = scan.primary_language,
        languages        = scan.languages,
        frameworks       = scan.frameworks,
        file_count       = scan.file_count,
        dependencies     = scan.dependencies,
        config_files     = scan.config_files,
        important_files  = scan.important_files,
    )


# ---------------------------------------------------------------------------
# GET /api/structure/{repo_id}
# ---------------------------------------------------------------------------


@router.get("/structure/{repo_id}", response_model=FileNode)
async def get_structure(repo_id: str) -> FileNode:
    """Return the file tree for an already-ingested repo."""
    record = load_record(repo_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ingestion record found for repo_id='{repo_id}'.",
        )

    if record.status == IngestionStatus.error:
        raise HTTPException(
            status_code=422,
            detail=record.error_message or "Ingestion failed.",
        )

    if record.status != IngestionStatus.ready or record.scan is None:
        raise HTTPException(
            status_code=202,
            detail=f"Ingestion is still in progress (status={record.status.value}).",
        )

    return record.scan.file_tree


# ---------------------------------------------------------------------------
# GET /api/analysis/{repo_id}
# ---------------------------------------------------------------------------


@router.get("/analysis/{repo_id}", response_model=AnalysisResult)
async def get_analysis(repo_id: str) -> AnalysisResult:
    """
    Return the full static analysis result for an ingested repository.

    If the analysis has already been computed it is returned from the cached
    analysis.json file.  If the repo is ready but not yet analysed the
    analysis is run on-demand and cached before returning.
    """
    record = load_record(repo_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No ingestion record found for repo_id='{repo_id}'. "
                   "Call POST /api/analyze first.",
        )

    if record.status == IngestionStatus.error:
        raise HTTPException(
            status_code=422,
            detail=record.error_message or "Ingestion failed.",
        )

    if record.status != IngestionStatus.ready or record.scan is None:
        raise HTTPException(
            status_code=202,
            detail=f"Ingestion is still in progress (status={record.status.value}).",
        )

    # Return cached result if available
    cached = load_analysis(repo_id)
    if cached is not None:
        return cached

    # Run analysis on-demand
    try:
        result = await run_analysis(record)
    except RuntimeError as exc:
        logger.error("Analysis failed for repo_id=%s: %s", repo_id, exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result
