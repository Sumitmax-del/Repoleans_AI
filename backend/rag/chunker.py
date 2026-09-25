"""
Source-file chunker.

Splits repository source files into Chunk objects, preserving file path and
exact 1-based line numbers so citations shown to the user are accurate.

Chunking strategies (chosen per file type)
------------------------------------------
source_code   — split on top-level function/class definition boundaries,
                falling back to fixed-size overlapping windows.
markdown      — split on heading boundaries (## / ###), fallback to paragraphs.
config/data   — whole file as one chunk if ≤ MAX_WHOLE_FILE_LINES, else windows.
other         — fixed-size overlapping windows.

All strategies respect a minimum chunk size so tiny fragments are merged with
the next chunk rather than emitted alone.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

from backend.rag.models import Chunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tuneable constants (all in lines)
# ---------------------------------------------------------------------------

# Target size for a chunk (aim for this many lines)
CHUNK_TARGET_LINES = 40

# Maximum lines per chunk before forced split
CHUNK_MAX_LINES = 80

# Minimum lines a chunk must have before being merged into the previous one
CHUNK_MIN_LINES = 6

# Overlap between consecutive window chunks (helps context continuity)
CHUNK_OVERLAP_LINES = 8

# Files shorter than this are emitted as a single chunk
MAX_WHOLE_FILE_LINES = 100

# Files larger than this are skipped entirely (minified JS, generated files, …)
MAX_FILE_LINES = 4000

# ---------------------------------------------------------------------------
# Language → chunking strategy
# ---------------------------------------------------------------------------

# Languages that benefit from symbol-boundary splitting
_SYMBOL_LANGS = {
    "Python", "JavaScript", "TypeScript", "Go", "Rust",
    "Java", "Kotlin", "C#", "C", "C++", "Ruby", "PHP",
    "Swift", "Scala", "Elixir",
}

# Regex patterns that open a new top-level symbol boundary (per language family)
# Applied to lines individually; a match starts a new chunk boundary.
_BOUNDARY_PATTERNS: list[re.Pattern] = [
    # Python: def / async def / class at column 0
    re.compile(r"^(?:async\s+)?def\s+\w|^class\s+\w"),
    # JS/TS: function, class, export default function, arrow at col 0
    re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+\w|^(?:export\s+)?class\s+\w"),
    # Go: func at col 0
    re.compile(r"^func\s+"),
    # Rust: fn, impl, struct, enum, trait at col 0
    re.compile(r"^(?:pub\s+)?(?:async\s+)?fn\s+\w|^(?:pub\s+)?(?:impl|struct|enum|trait)\s+\w"),
    # Java/Kotlin/C#: public/private/protected method/class at col 0
    re.compile(r"^(?:public|private|protected|static|override|abstract)\s+"),
    # Ruby: def / class at col 0
    re.compile(r"^def\s+\w|^class\s+\w|^module\s+\w"),
]

# Markdown heading pattern
_MD_HEADING = re.compile(r"^#{1,4}\s+\S")

# Extensions classified as config/data (→ whole-file or window chunks, no symbol splitting)
_CONFIG_EXTS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".xml", ".env", ".sh", ".bash", ".ps1", ".dockerfile",
}

# Extensions to skip entirely
_SKIP_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".br",
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
    ".lock",   # package-lock.json is too large and noisy
    ".map",    # JS source maps
}

# Filenames to skip regardless of extension
_SKIP_FILENAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Cargo.lock", "composer.lock",
    "Pipfile.lock",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_repository(
    clone_dir: Path,
    file_paths: list[str],
    repo_id: str,
    important_files: set[str] | None = None,
    language_map: dict[str, str] | None = None,
) -> list[Chunk]:
    """
    Chunk every eligible file in *file_paths* and return the full Chunk list.

    Parameters
    ----------
    clone_dir:
        Absolute path to the cloned repository root.
    file_paths:
        Repo-relative POSIX paths to process.
    repo_id:
        Identifier written into every Chunk.
    important_files:
        Set of repo-relative paths flagged as important by the scanner.
        Chunks from these files get ``is_important=True``.
    language_map:
        Mapping of repo-relative path → detected language (from scanner).
    """
    important_files = important_files or set()
    language_map    = language_map or {}
    chunks: list[Chunk] = []

    for rel_path in file_paths:
        fname = Path(rel_path).name
        ext   = Path(rel_path).suffix.lower()

        # Skip binary / generated / lock files
        if ext in _SKIP_EXTS or fname in _SKIP_FILENAMES:
            continue

        abs_path = clone_dir / rel_path
        if not abs_path.exists() or not abs_path.is_file():
            continue

        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        lines = text.splitlines()
        if not lines or len(lines) > MAX_FILE_LINES:
            continue

        language   = language_map.get(rel_path, "")
        important  = rel_path in important_files

        file_chunks = _chunk_file(lines, rel_path, repo_id, language, important, ext)
        chunks.extend(file_chunks)

    logger.debug("Chunked %d files → %d chunks", len(file_paths), len(chunks))
    return chunks


# ---------------------------------------------------------------------------
# Per-file chunking dispatcher
# ---------------------------------------------------------------------------


def _chunk_file(
    lines: list[str],
    rel_path: str,
    repo_id: str,
    language: str,
    important: bool,
    ext: str,
) -> list[Chunk]:
    """Return chunks for a single file."""

    # Whole-file shortcut for tiny files
    if len(lines) <= MAX_WHOLE_FILE_LINES:
        return [_make_chunk(lines, 1, len(lines), rel_path, repo_id, language, important)]

    if ext == ".md" or ext == ".rst":
        spans = _split_markdown(lines)
    elif language in _SYMBOL_LANGS:
        spans = _split_by_symbols(lines)
    elif ext in _CONFIG_EXTS:
        spans = _split_windows(lines)
    else:
        spans = _split_windows(lines)

    # Merge spans that are too small into the next one
    spans = _merge_small_spans(spans)

    # Force-split spans that are too large
    spans = _force_split_large_spans(spans)

    return [
        _make_chunk(lines, start, end, rel_path, repo_id, language, important)
        for start, end in spans
    ]


# ---------------------------------------------------------------------------
# Splitting strategies
# ---------------------------------------------------------------------------


def _split_by_symbols(lines: list[str]) -> list[tuple[int, int]]:
    """
    Split on top-level symbol boundaries (def/class/func/…).
    Returns list of (1-based start, 1-based end) inclusive spans.
    """
    boundary_lines: list[int] = []  # 0-based indices of lines that start a new symbol

    for i, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped:
            continue
        for pat in _BOUNDARY_PATTERNS:
            if pat.match(stripped):
                boundary_lines.append(i)
                break

    if not boundary_lines:
        return _split_windows(lines)

    # Convert boundary line indices → (start, end) 1-based spans
    spans: list[tuple[int, int]] = []
    for idx, boundary in enumerate(boundary_lines):
        start = boundary          # 0-based
        end   = (boundary_lines[idx + 1] - 1) if idx + 1 < len(boundary_lines) else len(lines) - 1
        spans.append((start + 1, end + 1))  # convert to 1-based

    # Prepend any lines before the first symbol (e.g. module docstring, imports)
    if boundary_lines[0] > 0:
        spans.insert(0, (1, boundary_lines[0]))  # lines before first boundary

    return spans


def _split_markdown(lines: list[str]) -> list[tuple[int, int]]:
    """Split markdown/RST on heading lines."""
    heading_lines: list[int] = []

    for i, line in enumerate(lines):
        if _MD_HEADING.match(line):
            heading_lines.append(i)

    if not heading_lines:
        return _split_windows(lines)

    spans: list[tuple[int, int]] = []
    if heading_lines[0] > 0:
        spans.append((1, heading_lines[0]))

    for idx, h in enumerate(heading_lines):
        start = h
        end   = (heading_lines[idx + 1] - 1) if idx + 1 < len(heading_lines) else len(lines) - 1
        spans.append((start + 1, end + 1))

    return spans


def _split_windows(lines: list[str]) -> list[tuple[int, int]]:
    """Fixed-size overlapping windows."""
    spans: list[tuple[int, int]] = []
    total = len(lines)
    start = 0
    while start < total:
        end = min(start + CHUNK_TARGET_LINES - 1, total - 1)
        spans.append((start + 1, end + 1))
        if end == total - 1:
            break
        start = end + 1 - CHUNK_OVERLAP_LINES
        start = max(start, 0)
    return spans


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------


def _merge_small_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge any span shorter than CHUNK_MIN_LINES into the next one."""
    if not spans:
        return spans
    merged: list[tuple[int, int]] = []
    pending_start, pending_end = spans[0]

    for start, end in spans[1:]:
        if (pending_end - pending_start + 1) < CHUNK_MIN_LINES:
            # Extend pending into this span
            pending_end = end
        else:
            merged.append((pending_start, pending_end))
            pending_start, pending_end = start, end

    merged.append((pending_start, pending_end))
    return merged


def _force_split_large_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Force-split any span larger than CHUNK_MAX_LINES into windows."""
    result: list[tuple[int, int]] = []
    for start, end in spans:
        size = end - start + 1
        if size <= CHUNK_MAX_LINES:
            result.append((start, end))
        else:
            # Window-split this span
            cursor = start
            while cursor <= end:
                chunk_end = min(cursor + CHUNK_TARGET_LINES - 1, end)
                result.append((cursor, chunk_end))
                if chunk_end == end:
                    break
                cursor = chunk_end + 1 - CHUNK_OVERLAP_LINES
                cursor = max(cursor, start)
    return result


# ---------------------------------------------------------------------------
# Chunk factory
# ---------------------------------------------------------------------------


def _make_chunk(
    lines: list[str],
    start: int,      # 1-based inclusive
    end: int,        # 1-based inclusive
    rel_path: str,
    repo_id: str,
    language: str,
    important: bool,
) -> Chunk:
    # Clamp
    start = max(1, start)
    end   = min(len(lines), end)

    chunk_lines = lines[start - 1 : end]
    text        = "\n".join(chunk_lines)
    symbol      = _nearest_symbol(chunk_lines)

    return Chunk(
        chunk_id   = f"{rel_path}:{start}",
        repo_id    = repo_id,
        file_path  = rel_path,
        start_line = start,
        end_line   = end,
        language   = language,
        text       = text,
        symbol     = symbol,
        is_important = important,
    )


# ---------------------------------------------------------------------------
# Symbol name extraction (best-effort)
# ---------------------------------------------------------------------------

_SYMBOL_RE = re.compile(
    r"^(?:(?:async\s+)?def|class|func|fn|function|pub\s+fn|pub\s+struct|"
    r"impl|module|struct|enum|trait)\s+(\w+)"
)


def _nearest_symbol(chunk_lines: list[str]) -> str:
    """Return the name of the first symbol defined in these lines, or ''."""
    for line in chunk_lines:
        m = _SYMBOL_RE.match(line.strip())
        if m:
            return m.group(1)
    return ""
