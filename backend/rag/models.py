"""
RAG layer data models.

These types flow through the full pipeline:
  chunker  →  Chunk list
  embedder →  EmbeddedChunk list
  index    →  IndexMeta (persisted)
  retriever→  RetrievalResult list  (consumed by Task 6B prompt builder)
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------


class Chunk(BaseModel):
    """
    A contiguous slice of a source file, ready for embedding.

    Attributes
    ----------
    chunk_id:
        Stable identifier within a repo: ``"<file_path>:<start_line>"``.
    repo_id:
        The repository this chunk belongs to.
    file_path:
        Repo-relative POSIX path, e.g. ``"fastapi/routing.py"``.
    start_line:
        1-based inclusive start line of this chunk in the source file.
    end_line:
        1-based inclusive end line of this chunk in the source file.
    language:
        Detected language (from scanner), e.g. ``"Python"`` — or ``""`` if unknown.
    text:
        The raw source text of the chunk (used for embedding and display).
    symbol:
        Nearest enclosing symbol name (function/class/section) if detectable, else ``""``.
    is_important:
        True when the file appears in ScanResult.important_files — boosts ranking.
    """

    chunk_id:    str
    repo_id:     str
    file_path:   str
    start_line:  int
    end_line:    int
    language:    str = ""
    text:        str
    symbol:      str = ""
    is_important: bool = False


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


class RetrievalResult(BaseModel):
    """
    A single retrieved chunk, ranked by relevance to a query.
    This is the unit the Task 6B prompt builder receives.
    """

    chunk_id:   str
    file_path:  str
    start_line: int
    end_line:   int
    language:   str = ""
    symbol:     str = ""
    text:       str
    score:      float   # cosine similarity in [0, 1]
    rank:       int     # 1-based position in the result list


# ---------------------------------------------------------------------------
# Index metadata (persisted alongside the vectors)
# ---------------------------------------------------------------------------


class IndexMeta(BaseModel):
    """
    Lightweight metadata stored in index_meta.json.
    The actual vectors live in index_vectors.npy.
    The chunk list lives in index_chunks.json.
    """

    repo_id:      str
    embed_provider: str          # e.g. "tfidf"
    chunk_count:  int
    vocab_size:   int = 0        # TF-IDF vocabulary size (0 for dense embedders)
    vector_dim:   int = 0        # embedding dimension
    built_at:     str = ""       # ISO-8601 timestamp
