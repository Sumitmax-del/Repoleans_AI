"""
GitHub metadata fetcher.

Fetches repository metadata from the GitHub REST API (unauthenticated).
Unauthenticated requests are rate-limited to 60 per hour; the fetcher
gracefully degrades when the API is unreachable or rate-limited.

No third-party libraries beyond httpx (already a project dependency) are used.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from backend.ingestion.models import RepoMetadata

logger = logging.getLogger(__name__)

# GitHub API base URL
_API_BASE = "https://api.github.com"

# Timeout for API requests (seconds)
_TIMEOUT = 10.0


async def fetch_repo_metadata(owner: str, repo: str) -> RepoMetadata:
    """
    Fetch repository metadata from the GitHub API.

    Returns a :class:`RepoMetadata` populated from the API response.
    On any failure (network error, 404, rate-limit) returns a minimal
    :class:`RepoMetadata` built from the owner/repo strings so the rest
    of the pipeline can continue.

    Parameters
    ----------
    owner:
        GitHub account / organisation name.
    repo:
        Repository name (without the ``.git`` suffix).
    """
    repo_url  = f"https://github.com/{owner}/{repo}"
    repo_name = f"{owner}/{repo}"
    fallback  = RepoMetadata(repo_name=repo_name, repo_url=repo_url)

    url = f"{_API_BASE}/repos/{owner}/{repo}"
    headers = {
        "Accept":     "application/vnd.github+json",
        "User-Agent": "RepoLens/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        logger.warning("GitHub API request timed out for %s/%s", owner, repo)
        return fallback
    except httpx.RequestError as exc:
        logger.warning("GitHub API request failed for %s/%s: %s", owner, repo, exc)
        return fallback

    if response.status_code == 404:
        logger.warning("GitHub API: repo not found %s/%s", owner, repo)
        return fallback

    if response.status_code == 403:
        # Likely rate-limited; degrade gracefully
        logger.warning(
            "GitHub API rate-limited (403) for %s/%s. "
            "Set a GITHUB_TOKEN env var to raise the limit.",
            owner, repo,
        )
        return fallback

    if not response.is_success:
        logger.warning(
            "GitHub API returned %d for %s/%s", response.status_code, owner, repo
        )
        return fallback

    try:
        data: dict[str, Any] = response.json()
    except Exception:
        return fallback

    return RepoMetadata(
        repo_name   = data.get("full_name", repo_name),
        repo_url    = data.get("html_url",  repo_url),
        description = data.get("description") or "",
        default_branch = data.get("default_branch", "main"),
        stargazers_count = data.get("stargazers_count", 0),
        forks_count      = data.get("forks_count", 0),
        topics           = data.get("topics", []),
    )
