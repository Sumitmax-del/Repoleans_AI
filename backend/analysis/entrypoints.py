"""
Entry-point file classifier.

Given the ScanResult (list of important files, detected frameworks, languages)
and optionally a small content scan of candidate files, classifies each
likely entry-point file with a kind and confidence level.

Entry-point kinds
-----------------
web_server   — boots an HTTP/ASGI/WSGI server
cli          — a command-line entry point
library      — a public library module (__init__.py at root, index.ts, etc.)
test         — a test runner or test suite entry point
config       — a build/packaging manifest (pyproject.toml, package.json, …)
script       — a utility script that does not fit other categories
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.ingestion.models import EntryPoint

# ---------------------------------------------------------------------------
# Rule tables
# ---------------------------------------------------------------------------

# (filename_lower → (kind, confidence, reason))
_EXACT: dict[str, tuple[str, str, str]] = {
    # Python servers
    "main.py":     ("web_server", "high",   "Conventional Python application entry point"),
    "app.py":      ("web_server", "high",   "Conventional Python app file; likely WSGI/ASGI root"),
    "server.py":   ("web_server", "high",   "Conventional Python server entry point"),
    "wsgi.py":     ("web_server", "high",   "WSGI application object"),
    "asgi.py":     ("web_server", "high",   "ASGI application object"),
    "manage.py":   ("cli",        "high",   "Django management CLI entry point"),
    "run.py":      ("web_server", "medium", "Likely starts the application server"),
    # Node servers
    "index.js":    ("web_server", "medium", "Node.js conventional entry point"),
    "index.ts":    ("web_server", "medium", "TypeScript/Node conventional entry point"),
    "index.tsx":   ("library",    "medium", "React app root component"),
    "server.js":   ("web_server", "high",   "Node.js server entry point"),
    "server.ts":   ("web_server", "high",   "TypeScript server entry point"),
    "app.js":      ("web_server", "medium", "Node.js app entry point"),
    "app.ts":      ("web_server", "medium", "TypeScript app entry point"),
    "main.ts":     ("web_server", "medium", "TypeScript main entry point"),
    "main.js":     ("web_server", "medium", "JavaScript main entry point"),
    # Go
    "main.go":     ("web_server", "high",   "Go program entry point (func main)"),
    # Rust
    "main.rs":     ("web_server", "high",   "Rust binary entry point"),
    "lib.rs":      ("library",    "high",   "Rust library crate root"),
    # Java
    "application.java": ("web_server", "medium", "Spring Boot application class"),
    # Ruby
    "config.ru":   ("web_server", "high",   "Rack/Rails server configuration"),
    # Packaging / config
    "pyproject.toml": ("config",  "high",   "Python packaging manifest"),
    "setup.py":    ("config",     "high",   "Python setup script"),
    "package.json":("config",     "high",   "Node.js package manifest"),
    "cargo.toml":  ("config",     "high",   "Rust package manifest"),
    "go.mod":      ("config",     "high",   "Go module definition"),
    "pom.xml":     ("config",     "high",   "Maven build manifest"),
    "build.gradle":("config",     "high",   "Gradle build script"),
    "gemfile":     ("config",     "high",   "Ruby Gemfile"),
    # Dockerfile / CI
    "dockerfile":  ("config",     "high",   "Docker container definition"),
    "makefile":    ("script",     "medium", "Build / task automation script"),
}

# Suffix-level heuristics (applied when no exact match)
_SUFFIX_RULES: list[tuple[str, str, str, str]] = [
    # (suffix, kind, confidence, reason)
    ("_test.go",    "test",    "high",   "Go test file (suffix _test.go)"),
    ("_spec.rb",    "test",    "high",   "Ruby RSpec spec file"),
    ("_spec.ts",    "test",    "medium", "TypeScript spec file"),
    ("_spec.js",    "test",    "medium", "JavaScript spec file"),
    (".test.ts",    "test",    "high",   "TypeScript test file"),
    (".test.js",    "test",    "high",   "JavaScript test file"),
    (".test.tsx",   "test",    "high",   "React test file"),
    (".spec.ts",    "test",    "high",   "TypeScript spec file"),
    (".spec.js",    "test",    "high",   "JavaScript spec file"),
]

# Content patterns that strongly indicate a particular kind
# Each entry: (compiled_re, kind, confidence, reason)
_CONTENT_HINTS: list[tuple[re.Pattern, str, str, str]] = [
    (re.compile(r"if\s+__name__\s*==\s*['\"]__main__['\"]", re.M),
     "web_server", "high", "Python __main__ guard (script entry point)"),
    (re.compile(r"uvicorn\.run\s*\(", re.M),
     "web_server", "high", "Calls uvicorn.run() — ASGI server startup"),
    (re.compile(r"app\.run\s*\(", re.M),
     "web_server", "high", "Calls app.run() — Flask/similar server startup"),
    (re.compile(r"createServer|http\.listen|app\.listen", re.M),
     "web_server", "high", "Node.js HTTP server listening"),
    (re.compile(r"^func\s+main\s*\(\s*\)", re.M),
     "web_server", "medium", "Go main function"),
    (re.compile(r"^fn\s+main\s*\(\s*\)", re.M),
     "web_server", "medium", "Rust main function"),
    (re.compile(r"@SpringBootApplication", re.M),
     "web_server", "high", "Spring Boot application annotation"),
    (re.compile(r"pytest\.main|unittest\.main", re.M),
     "cli",        "medium", "Test runner invocation"),
    (re.compile(r"argparse|click\.command|typer\.run|fire\.Fire", re.M),
     "cli",        "medium", "CLI argument parsing detected"),
]

_MAX_READ_BYTES = 32 * 1024   # only read first 32 KB for content hints


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_entry_points(
    clone_dir: Path,
    important_files: list[str],
    all_files: list[str] | None = None,
) -> list[EntryPoint]:
    """
    Classify *important_files* into :class:`EntryPoint` records.

    Parameters
    ----------
    clone_dir:
        Absolute path to the cloned repository root.
    important_files:
        Repo-relative paths flagged as important by the scanner.
    all_files:
        Optionally the full file list; if provided, any top-level source
        file matching the exact-name rules is also classified.
    """
    # Build a deduplicated candidate list: important_files + top-level
    # files that match exact-name rules.
    candidates: dict[str, None] = {f: None for f in important_files}

    if all_files:
        for f in all_files:
            fname = Path(f).name.lower()
            if fname in _EXACT and "/" not in f:
                candidates[f] = None

    results: list[EntryPoint] = []
    seen: set[str] = set()

    for rel in candidates:
        if rel in seen:
            continue
        seen.add(rel)

        fname = Path(rel).name.lower()

        # 1. Exact-name rule
        if fname in _EXACT:
            kind, conf, reason = _EXACT[fname]
            results.append(EntryPoint(file=rel, kind=kind, confidence=conf, reason=reason))
            continue

        # 2. Suffix rule
        matched_suffix = False
        for suffix, kind, conf, reason in _SUFFIX_RULES:
            if rel.endswith(suffix):
                results.append(EntryPoint(file=rel, kind=kind, confidence=conf, reason=reason))
                matched_suffix = True
                break
        if matched_suffix:
            continue

        # 3. Content scan (only for source files ≤ _MAX_READ_BYTES)
        abs_path = clone_dir / rel
        ext = Path(rel).suffix.lower()
        if ext not in {".py", ".js", ".ts", ".go", ".rs", ".java", ".rb", ".kt"}:
            continue

        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")[:_MAX_READ_BYTES]
        except OSError:
            continue

        for pattern, kind, conf, reason in _CONTENT_HINTS:
            if pattern.search(text):
                results.append(EntryPoint(file=rel, kind=kind, confidence=conf, reason=reason))
                break

    # Sort: high confidence first, then by file path
    _order = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda e: (_order.get(e.confidence, 9), e.file))
    return results
