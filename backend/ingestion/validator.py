"""
URL validation for the repository ingestion pipeline.

Accepts only public github.com HTTPS URLs that point to a repository root
(owner/repo).  Rejects everything else with a descriptive error message.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Only allow HTTPS github.com URLs
_GITHUB_HTTPS_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.\-]+)/(?P<repo>[A-Za-z0-9_.\-]+?)(?:\.git)?/?$"
)

# Names that are GitHub site navigation, not repositories
_RESERVED_NAMES = frozenset(
    {
        "about", "collections", "contact", "customer-stories", "enterprise",
        "events", "explore", "features", "issues", "login", "marketplace",
        "notifications", "orgs", "pricing", "pulls", "readme", "security",
        "settings", "solutions", "sponsors", "stars", "topics", "trending",
        "users", "watching",
    }
)


class ValidationError(ValueError):
    """Raised when the supplied URL is not a valid public GitHub repository URL."""


def validate_github_url(url: str) -> tuple[str, str]:
    """
    Validate *url* and return ``(owner, repo)`` if it is a valid public
    GitHub repository URL.

    Raises
    ------
    ValidationError
        With a human-readable message describing why the URL was rejected.
    """
    if not url or not url.strip():
        raise ValidationError("URL must not be empty.")

    url = url.strip()

    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http"):
        raise ValidationError(
            f"Only HTTPS GitHub URLs are supported (got scheme '{parsed.scheme}')."
        )

    if parsed.scheme == "http":
        # Rewrite to HTTPS; don't reject outright — caller will use canonical form
        url = "https://" + url[len("http://"):]

    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValidationError(
            f"Only public github.com repositories are supported "
            f"(got host '{parsed.netloc}')."
        )

    m = _GITHUB_HTTPS_RE.match(url)
    if not m:
        raise ValidationError(
            "URL must point to a repository root, e.g. "
            "https://github.com/owner/repository"
        )

    owner = m.group("owner")
    repo  = m.group("repo")

    if owner.lower() in _RESERVED_NAMES:
        raise ValidationError(
            f"'{owner}' is a reserved GitHub path, not a repository owner."
        )

    if repo.lower() in _RESERVED_NAMES:
        raise ValidationError(
            f"'{repo}' is a reserved GitHub path, not a repository name."
        )

    return owner, repo


def canonical_url(owner: str, repo: str) -> str:
    """Return the canonical clone URL for *owner*/*repo*."""
    return f"https://github.com/{owner}/{repo}.git"
