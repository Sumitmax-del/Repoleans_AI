"""
Shared Pydantic models for the ingestion pipeline and analysis layer.

These are the canonical internal types that cloner, scanner, metadata fetcher,
analysis engine, and future RAG/analysis modules all consume.  The shapes also
map directly to the JSON returned by the API endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class IngestionStatus(str, Enum):
    pending   = "pending"
    cloning   = "cloning"
    scanning  = "scanning"
    ready     = "ready"
    error     = "error"


# ---------------------------------------------------------------------------
# File / directory tree
# ---------------------------------------------------------------------------


class FileNode(BaseModel):
    """A single node in the repository file tree (file or directory)."""

    name: str
    path: str                        # POSIX-style path relative to repo root
    type: str                        # "file" | "directory"
    language: Optional[str] = None   # detected language, files only
    size_bytes: Optional[int] = None # files only
    children: Optional[list["FileNode"]] = None  # directories only

    model_config = {"populate_by_name": True}


FileNode.model_rebuild()  # resolve forward reference


# ---------------------------------------------------------------------------
# Repository metadata
# ---------------------------------------------------------------------------


class RepoMetadata(BaseModel):
    """Metadata fetched from the GitHub API (best-effort; may be partial)."""

    repo_name: str                          # "owner/repo"
    repo_url: str
    description: str = ""
    default_branch: str = "main"
    stargazers_count: int = 0
    forks_count: int = 0
    topics: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scan result
# ---------------------------------------------------------------------------


class ScanResult(BaseModel):
    """Output of the file-system scanner."""

    file_count: int
    directory_count: int
    total_size_bytes: int
    languages: list[str]             # ordered by file count, most common first
    primary_language: str            # top language
    frameworks: list[str]            # detected from filenames / dependency files
    config_files: list[str]          # notable config / CI files
    important_files: list[str]       # README, entry points, pyproject, …
    dependencies: dict[str, list[str]]  # manifest → [package names]
    file_tree: FileNode              # root node of the full tree


# ---------------------------------------------------------------------------
# Top-level ingestion record
# ---------------------------------------------------------------------------


class IngestionRecord(BaseModel):
    """
    Persisted state for a single ingestion job.
    Written to <work_dir>/record.json after each stage completes.
    """

    repo_id: str
    repo_url: str
    status: IngestionStatus = IngestionStatus.pending
    error_message: Optional[str] = None

    # Populated progressively as pipeline stages complete
    metadata: Optional[RepoMetadata] = None
    scan: Optional[ScanResult] = None

    # Filesystem paths (strings so they serialise cleanly to JSON)
    work_dir: str = ""     # absolute path to the cloned repo directory


# ---------------------------------------------------------------------------
# Analysis layer models  (Task 5)
# ---------------------------------------------------------------------------


class RouteDefinition(BaseModel):
    """A single detected API route / endpoint."""

    method: str          # HTTP verb: GET, POST, PUT, DELETE, PATCH, WS, "any"
    path: str            # route path pattern, e.g. "/users/{id}"
    file: str            # repo-relative path to the source file
    line: int            # 1-based line number where the route is defined
    handler: str = ""    # name of the handler function/method, if detectable
    framework: str = ""  # e.g. "FastAPI", "Express", "Django", "Flask"


class EntryPoint(BaseModel):
    """A classified entry-point file."""

    file: str            # repo-relative path
    kind: str            # "web_server" | "cli" | "library" | "test" | "config" | "script"
    confidence: str      # "high" | "medium" | "low"
    reason: str          # human-readable explanation


class SourceDirectory(BaseModel):
    """A classified source directory."""

    path: str            # repo-relative path (empty string = repo root)
    role: str            # "source" | "tests" | "docs" | "config" | "scripts" | "assets" | "infra"
    language: str = ""   # dominant language in this directory
    file_count: int = 0


class ArchLayer(BaseModel):
    """One layer in the architecture flow diagram."""

    id: str              # stable slug, e.g. "entry", "routing", "middleware"
    label: str           # display label, e.g. "Entry Point"
    color: str           # one of: blue sky purple orange green gray red cyan
    nodes: list["ArchNode"]


class ArchNode(BaseModel):
    """A node within an architecture layer."""

    name: str            # short display name, e.g. "FastAPI()"
    file: str            # repo-relative path to the most relevant file
    description: str     # one-line explanation


ArchLayer.model_rebuild()


class AnalysisResult(BaseModel):
    """
    Full static analysis result produced by the analysis engine.
    Stored as analysis.json alongside record.json in the job directory.
    Consumed by /api/analysis/{repo_id} and (later) the RAG pipeline.
    """

    repo_id: str

    # ── Core classification ───────────────────────────────────────────────
    entry_points:       list[EntryPoint]       = Field(default_factory=list)
    source_directories: list[SourceDirectory]  = Field(default_factory=list)
    routes:             list[RouteDefinition]  = Field(default_factory=list)

    # ── Architecture ──────────────────────────────────────────────────────
    arch_layers:        list[ArchLayer]        = Field(default_factory=list)

    # ── Narrative summary ─────────────────────────────────────────────────
    # A plain-English paragraph describing the repo architecture.
    # Generated deterministically from the detected structure (no LLM).
    summary_text: str = ""

    # ── Counts (convenience for display) ──────────────────────────────────
    route_count: int = 0
