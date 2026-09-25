"""
RAG index builder and persistence.

Builds a vector index from a list of Chunks, persists it to disk, and
provides a fast load-from-disk path so retrieval is instant on subsequent
requests without re-embedding.

Disk layout (all under <work_root>/<repo_id>/)
-----------------------------------------------
rag_meta.json      — IndexMeta (provider, counts, vocab size, dimension)
rag_vectors.npy    — float32 array, shape (n_chunks, dim)
rag_chunks.json    — serialised list of Chunk objects
rag_embedder.json  — embedder state (TF-IDF vocab+IDF; empty for dense models)
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
from pathlib import Path

import numpy as np

from backend.ingestion.cloner import get_work_root
from backend.rag.chunker      import chunk_repository
from backend.rag.embedder     import get_embedder
from backend.rag.models       import Chunk, IndexMeta

logger = logging.getLogger(__name__)

# Batch size for embedding (keeps memory usage bounded)
_EMBED_BATCH = 512


# ---------------------------------------------------------------------------
# Filesystem paths
# ---------------------------------------------------------------------------

def _index_dir(repo_id: str) -> Path:
    return get_work_root() / repo_id


def _meta_path(repo_id: str)     -> Path: return _index_dir(repo_id) / "rag_meta.json"
def _vectors_path(repo_id: str)  -> Path: return _index_dir(repo_id) / "rag_vectors.npy"
def _chunks_path(repo_id: str)   -> Path: return _index_dir(repo_id) / "rag_chunks.json"
def _embedder_path(repo_id: str) -> Path: return _index_dir(repo_id) / "rag_embedder.json"


# ---------------------------------------------------------------------------
# Public load helpers
# ---------------------------------------------------------------------------


def index_exists(repo_id: str) -> bool:
    """Return True if a fully built index exists on disk for *repo_id*."""
    return (
        _meta_path(repo_id).exists()
        and _vectors_path(repo_id).exists()
        and _chunks_path(repo_id).exists()
    )


def load_index(repo_id: str) -> tuple[np.ndarray, list[Chunk], IndexMeta] | None:
    """
    Load a previously built index from disk.

    Returns
    -------
    (vectors, chunks, meta)  or  None if the index does not exist.
    """
    if not index_exists(repo_id):
        return None

    try:
        meta = IndexMeta.model_validate_json(
            _meta_path(repo_id).read_text(encoding="utf-8")
        )
        vectors = np.load(str(_vectors_path(repo_id)))
        raw_chunks = json.loads(_chunks_path(repo_id).read_text(encoding="utf-8"))
        chunks = [Chunk.model_validate(c) for c in raw_chunks]
    except Exception as exc:
        logger.warning("Failed to load RAG index for repo_id=%s: %s", repo_id, exc)
        return None

    return vectors, chunks, meta


def load_embedder_state(repo_id: str) -> dict:
    """Load the persisted embedder state (TF-IDF vocab/IDF)."""
    path = _embedder_path(repo_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Index builder (blocking)
# ---------------------------------------------------------------------------


def build_index_sync(
    repo_id: str,
    work_dir: str,
    file_paths: list[str],
    important_files: set[str] | None = None,
    language_map: dict[str, str] | None = None,
) -> IndexMeta:
    """
    Build and persist the full RAG index for a repository.

    Steps
    -----
    1. Chunk all source files (preserving line numbers).
    2. Fit the embedder on the chunk corpus.
    3. Embed all chunks in batches.
    4. Persist vectors + chunks + embedder state + metadata.

    Returns
    -------
    IndexMeta describing the built index.
    """
    clone_dir = Path(work_dir)

    # ── Step 1: chunk ──────────────────────────────────────────────────────
    logger.info("RAG index [%s]: chunking %d files", repo_id, len(file_paths))
    chunks = chunk_repository(
        clone_dir=clone_dir,
        file_paths=file_paths,
        repo_id=repo_id,
        important_files=important_files,
        language_map=language_map,
    )

    if not chunks:
        logger.warning("RAG index [%s]: no chunks produced", repo_id)
        # Write a minimal valid index so subsequent calls don't re-build
        meta = IndexMeta(
            repo_id=repo_id,
            embed_provider="tfidf",
            chunk_count=0,
            vocab_size=0,
            vector_dim=0,
            built_at=_now(),
        )
        _persist(repo_id, np.zeros((0, 1), dtype=np.float32), [], meta, {})
        return meta

    logger.info("RAG index [%s]: %d chunks produced", repo_id, len(chunks))

    # ── Step 2: fit embedder ───────────────────────────────────────────────
    embedder = get_embedder()
    texts    = [c.text for c in chunks]

    logger.info("RAG index [%s]: fitting embedder (%s)", repo_id, embedder.provider_name)
    embedder.fit(texts)

    # ── Step 3: embed in batches ───────────────────────────────────────────
    logger.info("RAG index [%s]: embedding %d chunks", repo_id, len(chunks))
    all_vecs: list[np.ndarray] = []
    for i in range(0, len(texts), _EMBED_BATCH):
        batch = texts[i : i + _EMBED_BATCH]
        vecs  = embedder.transform(batch)
        all_vecs.append(vecs)

    vectors = np.vstack(all_vecs).astype(np.float32)  # (n, dim)

    # ── Step 4: persist ────────────────────────────────────────────────────
    vocab_size = getattr(embedder, "vocab_size", lambda: 0)()
    meta = IndexMeta(
        repo_id        = repo_id,
        embed_provider = embedder.provider_name,
        chunk_count    = len(chunks),
        vocab_size     = vocab_size,
        vector_dim     = vectors.shape[1] if vectors.ndim == 2 else 0,
        built_at       = _now(),
    )

    embedder_state = embedder.get_state() if hasattr(embedder, "get_state") else {}
    _persist(repo_id, vectors, chunks, meta, embedder_state)

    logger.info(
        "RAG index [%s]: built — chunks=%d dim=%d provider=%s",
        repo_id, len(chunks), meta.vector_dim, embedder.provider_name,
    )
    return meta


async def build_index(
    repo_id: str,
    work_dir: str,
    file_paths: list[str],
    important_files: set[str] | None = None,
    language_map: dict[str, str] | None = None,
) -> IndexMeta:
    """Async wrapper: runs the blocking build in a thread pool."""
    return await asyncio.to_thread(
        build_index_sync,
        repo_id, work_dir, file_paths, important_files, language_map,
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _persist(
    repo_id: str,
    vectors: np.ndarray,
    chunks: list[Chunk],
    meta: IndexMeta,
    embedder_state: dict,
) -> None:
    d = _index_dir(repo_id)
    d.mkdir(parents=True, exist_ok=True)

    _meta_path(repo_id).write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    np.save(str(_vectors_path(repo_id)), vectors)
    _chunks_path(repo_id).write_text(
        json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _embedder_path(repo_id).write_text(
        json.dumps(embedder_state, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.debug("RAG index persisted to %s", d)


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"
