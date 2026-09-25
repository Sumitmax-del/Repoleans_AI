"""
Repository cloner.

Clones a public GitHub repository (shallow, depth=1) into a dedicated
subdirectory under the configured work root.  The work root defaults to
``<system-temp>/repolens`` but can be overridden with the ``REPOLENS_WORK_DIR``
environment variable.

Directory layout
----------------
<work_root>/
    <repo_id>/           ← one directory per ingestion job
        repo/            ← the actual git clone lands here
        record.json      ← IngestionRecord persisted between pipeline stages
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from backend.ingestion.models import IngestionRecord, IngestionStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_DEFAULT_WORK_ROOT = Path(tempfile.gettempdir()) / "repolens"


def get_work_root() -> Path:
    """Return the root directory used for all ingestion jobs."""
    env = os.getenv("REPOLENS_WORK_DIR")
    root = Path(env) if env else _DEFAULT_WORK_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def repo_id_for(url: str) -> str:
    """Deterministic, filesystem-safe ID derived from the canonical URL."""
    return hashlib.sha256(url.lower().strip().encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Record helpers
# ---------------------------------------------------------------------------

def _record_path(job_dir: Path) -> Path:
    return job_dir / "record.json"


def save_record(record: IngestionRecord) -> None:
    job_dir = Path(record.work_dir).parent  # work_dir is .../job/repo
    _record_path(job_dir).write_text(
        record.model_dump_json(indent=2), encoding="utf-8"
    )


def load_record(repo_id: str) -> IngestionRecord | None:
    """Return a persisted IngestionRecord, or None if it does not exist."""
    record_file = get_work_root() / repo_id / "record.json"
    if not record_file.exists():
        return None
    try:
        return IngestionRecord.model_validate_json(record_file.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Could not parse record.json for repo_id=%s", repo_id)
        return None


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------

# Directories that are never useful for code analysis
_IGNORE_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox",
    "build", "dist", "out", "target",        # build outputs
    ".idea", ".vscode", ".vs",               # IDE metadata
    "vendor", "third_party", "Pods",         # vendored deps
    ".next", ".nuxt", ".turbo",              # JS framework caches
    "coverage", ".nyc_output",              # test coverage artefacts
}

# Maximum total size we're willing to clone (bytes) – 500 MB
_MAX_CLONE_SIZE_BYTES = 500 * 1024 * 1024

# git clone timeout (seconds) — generous for large repos on slow links
_CLONE_TIMEOUT = 120


def _run_git(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a git subcommand and return the result.  Raises on non-zero exit."""
    cmd = ["git"] + args
    logger.debug("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=_CLONE_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {args[0]} failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def clone_repository(repo_url: str, repo_id: str) -> IngestionRecord:
    """
    Shallow-clone *repo_url* into ``<work_root>/<repo_id>/repo/``.

    Returns
    -------
    IngestionRecord
        With ``status=ready`` (clone stage) and ``work_dir`` set.

    Raises
    ------
    RuntimeError
        If git is unavailable, the URL is inaccessible, or cloning fails.
    """
    work_root = get_work_root()
    job_dir   = work_root / repo_id
    clone_dir = job_dir / "repo"

    # ── Already cloned? ────────────────────────────────────────────────────
    existing = load_record(repo_id)
    if (
        existing is not None
        and existing.status not in (IngestionStatus.pending, IngestionStatus.error)
        and clone_dir.exists()
        and any(clone_dir.iterdir())
    ):
        logger.info("repo_id=%s already cloned, reusing.", repo_id)
        return existing

    # ── Fresh job directory ────────────────────────────────────────────────
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
    job_dir.mkdir(parents=True, exist_ok=True)

    record = IngestionRecord(
        repo_id=repo_id,
        repo_url=repo_url,
        status=IngestionStatus.cloning,
        work_dir=str(clone_dir),
    )
    _record_path(job_dir).write_text(record.model_dump_json(indent=2), encoding="utf-8")

    # ── Check git availability ─────────────────────────────────────────────
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True, check=True, timeout=5
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        record.status = IngestionStatus.error
        record.error_message = "git is not available on this system."
        save_record(record)
        raise RuntimeError(record.error_message)

    # ── Clone ──────────────────────────────────────────────────────────────
    logger.info("Cloning %s → %s", repo_url, clone_dir)
    try:
        _run_git([
            "clone",
            "--depth", "1",          # shallow: only latest commit
            "--single-branch",       # don't fetch all branches
            "--no-tags",             # skip tag objects
            "--filter=blob:none",    # don't download blobs yet (treeless clone)
            "--quiet",
            repo_url,
            str(clone_dir),
        ])
    except subprocess.TimeoutExpired:
        _cleanup_on_error(job_dir)
        record.status = IngestionStatus.error
        record.error_message = f"Clone timed out after {_CLONE_TIMEOUT}s."
        save_record(record)
        raise RuntimeError(record.error_message)
    except RuntimeError as exc:
        _cleanup_on_error(job_dir)
        msg = str(exc)
        # Friendly messages for common failure modes
        if "Repository not found" in msg or "not found" in msg.lower():
            msg = f"Repository not found or is private: {repo_url}"
        elif "fatal: unable to access" in msg:
            msg = f"Could not reach GitHub. Check your internet connection. ({repo_url})"
        record.status = IngestionStatus.error
        record.error_message = msg
        save_record(record)
        raise RuntimeError(record.error_message) from exc

    # ── Now materialise the blobs (needed for file content analysis) ───────
    try:
        _run_git(["fetch", "--filter=blob:none", "--quiet"], cwd=clone_dir)
    except RuntimeError:
        # Non-fatal: treeless clone still gives us the tree for scanning
        logger.warning("Blob fetch failed; file content analysis may be limited.")

    # ── Size guard ────────────────────────────────────────────────────────
    total = _dir_size(clone_dir)
    if total > _MAX_CLONE_SIZE_BYTES:
        shutil.rmtree(job_dir, ignore_errors=True)
        record.status = IngestionStatus.error
        record.error_message = (
            f"Repository is too large ({total // (1024*1024)} MB > "
            f"{_MAX_CLONE_SIZE_BYTES // (1024*1024)} MB limit)."
        )
        save_record(record)
        raise RuntimeError(record.error_message)

    # ── Remove .git to save space (we don't need history) ─────────────────
    git_dir = clone_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir, ignore_errors=True)

    record.status = IngestionStatus.scanning
    record.work_dir = str(clone_dir)
    save_record(record)

    logger.info("Clone complete: repo_id=%s  size=%d bytes", repo_id, total)
    return record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dir_size(path: Path) -> int:
    """Return the total byte size of all files under *path*."""
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def _cleanup_on_error(job_dir: Path) -> None:
    try:
        shutil.rmtree(job_dir, ignore_errors=True)
    except Exception:
        pass
