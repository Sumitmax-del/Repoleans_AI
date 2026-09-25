"""
Semantic retriever.

Given a natural-language query and a built RAG index, returns the most
relevant Chunks as RetrievalResult objects.

Scoring
-------
Base score   = cosine similarity between query vector and chunk vector.
               (Both are L2-normalised so dot product == cosine similarity.)

Keyword boost = small additive bonus when the query contains tokens that
                appear verbatim in the chunk text.  Helps surface exact
                symbol/function names even when the TF-IDF similarity is
                slightly lower due to vocabulary mismatch.

Importance boost = small additive bonus for chunks from files flagged as
                   important by the scanner (README, main entry points, etc.).

Final score is clamped to [0, 1].

Usage
-----
    from backend.rag.retriever import retrieve

    results = retrieve(repo_id, "how is routing structured", top_k=8)
    for r in results:
        print(r.file_path, r.start_line, r.score)
"""

from __future__ import annotations

import logging
import re

import numpy as np

from backend.rag.embedder import get_embedder
from backend.rag.index    import index_exists, load_embedder_state, load_index
from backend.rag.models   import Chunk, RetrievalResult

logger = logging.getLogger(__name__)

# Additive bonus for exact keyword match (per token, capped)
_KEYWORD_BONUS_PER_TOKEN = 0.04
_KEYWORD_BONUS_MAX       = 0.20

# Additive bonus for chunks from important files
_IMPORTANCE_BONUS = 0.05

# Minimum score threshold — chunks below this are excluded from results
_MIN_SCORE = 0.01

# Simple word tokeniser for keyword matching
_WORD_RE = re.compile(r"[A-Za-z_]\w*")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def retrieve(
    repo_id: str,
    query: str,
    top_k: int = 8,
) -> list[RetrievalResult]:
    """
    Retrieve the *top_k* most relevant chunks for *query* from the index
    associated with *repo_id*.

    Returns an empty list if the index does not exist or the query is blank.
    This function is synchronous and safe to call from ``asyncio.to_thread``.

    Parameters
    ----------
    repo_id:
        Repository identifier (matches the ingestion record).
    query:
        Natural-language question from the user.
    top_k:
        Maximum number of results to return.
    """
    query = query.strip()
    if not query:
        return []

    if not index_exists(repo_id):
        logger.warning("retrieve: no index for repo_id=%s", repo_id)
        return []

    loaded = load_index(repo_id)
    if loaded is None:
        return []

    vectors, chunks, meta = loaded
    if len(chunks) == 0 or vectors.shape[0] == 0:
        return []

    # ── Reconstruct query vector ──────────────────────────────────────────
    embedder = get_embedder()

    # Restore TF-IDF vocabulary so query tokens map to the same columns
    embedder_state = load_embedder_state(repo_id)
    if hasattr(embedder, "set_state") and embedder_state:
        embedder.set_state(embedder_state)
    else:
        # Dense model: no state needed; just ensure fit is no-op
        embedder.fit([])

    query_vec = embedder.transform_query(query)  # shape: (dim,)

    if query_vec.shape[0] != vectors.shape[1]:
        logger.error(
            "retrieve: vector dimension mismatch — query %d vs index %d",
            query_vec.shape[0], vectors.shape[1],
        )
        return []

    # ── Base scores (dot product of L2-normalised vectors = cosine sim) ──
    scores: np.ndarray = vectors @ query_vec  # shape: (n_chunks,)

    # ── Keyword boost ────────────────────────────────────────────────────
    query_tokens = set(t.lower() for t in _WORD_RE.findall(query))
    if query_tokens:
        for i, chunk in enumerate(chunks):
            chunk_lower = chunk.text.lower()
            hit_count   = sum(1 for tok in query_tokens if tok in chunk_lower)
            bonus = min(hit_count * _KEYWORD_BONUS_PER_TOKEN, _KEYWORD_BONUS_MAX)
            scores[i] += bonus

    # ── Importance boost ─────────────────────────────────────────────────
    for i, chunk in enumerate(chunks):
        if chunk.is_important:
            scores[i] += _IMPORTANCE_BONUS

    # Clamp to [0, 1]
    scores = np.clip(scores, 0.0, 1.0)

    # ── Rank and filter ───────────────────────────────────────────────────
    # Get indices sorted by score descending
    ranked_indices = np.argsort(scores)[::-1]

    results: list[RetrievalResult] = []
    rank = 1
    for idx in ranked_indices:
        if rank > top_k:
            break
        score = float(scores[idx])
        if score < _MIN_SCORE:
            break
        chunk = chunks[int(idx)]
        results.append(
            RetrievalResult(
                chunk_id   = chunk.chunk_id,
                file_path  = chunk.file_path,
                start_line = chunk.start_line,
                end_line   = chunk.end_line,
                language   = chunk.language,
                symbol     = chunk.symbol,
                text       = chunk.text,
                score      = round(score, 4),
                rank       = rank,
            )
        )
        rank += 1

    logger.debug(
        "retrieve: repo_id=%s query=%r → %d results (top score=%.3f)",
        repo_id, query[:60], len(results),
        results[0].score if results else 0.0,
    )
    return results
