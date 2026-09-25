"""
Pluggable embedding provider.

The provider is selected by the ``EMBED_PROVIDER`` environment variable.

Providers
---------
tfidf  (default, zero extra deps)
    TF-IDF sparse vectors over a token vocabulary built from the corpus.
    Fast, deterministic, no model download, works offline.
    numpy arrays of shape (n_chunks, vocab_size).

sentence-transformers  (optional, requires sentence-transformers package)
    Dense semantic embeddings from a small local model.
    Set EMBED_MODEL to override the model name
    (default: "all-MiniLM-L6-v2" — 22 MB, CPU-friendly).

All providers implement the EmbedderProtocol:
    fit(texts)        → None         (build vocabulary / load model)
    transform(texts)  → np.ndarray   (shape: [n, dim])
    transform_query(text) → np.ndarray  (shape: [dim])
"""

from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from typing import Protocol, runtime_checkable

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbedderProtocol(Protocol):
    provider_name: str

    def fit(self, texts: list[str]) -> None:
        """Build vocabulary / load model from the corpus texts."""
        ...

    def transform(self, texts: list[str]) -> np.ndarray:
        """Return a 2-D float32 array, shape (len(texts), dim)."""
        ...

    def transform_query(self, text: str) -> np.ndarray:
        """Return a 1-D float32 array, shape (dim,)."""
        ...


# ---------------------------------------------------------------------------
# TF-IDF embedder (default — pure numpy, no extra deps)
# ---------------------------------------------------------------------------

# Tokeniser: split on non-alphanumeric, keep underscores (identifier-aware)
_TOKEN_RE = re.compile(r"[A-Za-z_]\w*|\d+")

# Sub-word split on camelCase / snake_case so "getUserById" also matches "user"
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _tokenise(text: str) -> list[str]:
    """Tokenise source text into lower-cased sub-word tokens."""
    tokens: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        # Split camelCase into sub-words
        parts = _CAMEL_RE.sub("_", raw).split("_")
        for p in parts:
            p = p.lower()
            if len(p) >= 2:           # skip single-char tokens
                tokens.append(p)
    return tokens


# Minimum document frequency for a token to enter the vocabulary
_MIN_DF = 2
# Maximum fraction of documents a token may appear in (stop-word-like)
_MAX_DF_RATIO = 0.85
# Hard vocabulary cap (keeps memory usage bounded on large repos)
_MAX_VOCAB = 20_000


class TFIDFEmbedder:
    """
    Lightweight TF-IDF vectoriser backed by numpy.

    Produces L2-normalised sparse-to-dense vectors suitable for cosine
    similarity retrieval.
    """

    provider_name = "tfidf"

    def __init__(self) -> None:
        self._vocab:  dict[str, int] = {}   # token → column index
        self._idf:    np.ndarray | None = None
        self._fitted  = False

    # ── fit ──────────────────────────────────────────────────────────────

    def fit(self, texts: list[str]) -> None:
        """Build vocabulary and IDF weights from the corpus."""
        n = len(texts)
        if n == 0:
            logger.warning("TFIDFEmbedder.fit called with empty corpus")
            return

        # Document frequency per token
        df: Counter[str] = Counter()
        tokenised: list[list[str]] = []
        for text in texts:
            toks = set(_tokenise(text))
            df.update(toks)
            tokenised.append(list(toks))  # store unique tokens per doc for speed

        # Filter vocabulary
        min_df  = max(_MIN_DF, 1)
        max_df  = int(n * _MAX_DF_RATIO)

        candidates = [
            (tok, freq) for tok, freq in df.items()
            if min_df <= freq <= max_df
        ]

        # Sort by IDF (rarer first) then by token, take top _MAX_VOCAB
        candidates.sort(key=lambda x: (x[1], x[0]))
        candidates = candidates[:_MAX_VOCAB]

        self._vocab = {tok: i for i, (tok, _) in enumerate(candidates)}
        vocab_size  = len(self._vocab)

        if vocab_size == 0:
            # Fallback: accept all tokens (tiny corpus)
            all_toks = sorted(df.keys())[:_MAX_VOCAB]
            self._vocab = {t: i for i, t in enumerate(all_toks)}
            vocab_size  = len(self._vocab)

        # Compute IDF: log((n + 1) / (df + 1)) + 1  (sklearn-compatible smooth)
        idf_arr = np.zeros(vocab_size, dtype=np.float32)
        for tok, idx in self._vocab.items():
            idf_arr[idx] = math.log((n + 1) / (df[tok] + 1)) + 1.0

        self._idf    = idf_arr
        self._fitted = True
        logger.debug("TFIDFEmbedder fitted: n_docs=%d vocab=%d", n, vocab_size)

    # ── transform ────────────────────────────────────────────────────────

    def transform(self, texts: list[str]) -> np.ndarray:
        """Vectorise a batch of texts. Returns float32 array [n, vocab]."""
        if not self._fitted or self._idf is None:
            raise RuntimeError("TFIDFEmbedder.fit() must be called before transform()")

        vocab_size = len(self._vocab)
        out = np.zeros((len(texts), vocab_size), dtype=np.float32)

        for row, text in enumerate(texts):
            toks = _tokenise(text)
            if not toks:
                continue
            tf: Counter[str] = Counter(toks)
            n_toks = len(toks)
            for tok, count in tf.items():
                idx = self._vocab.get(tok)
                if idx is not None:
                    out[row, idx] = (count / n_toks) * self._idf[idx]

        # L2 normalise each row
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        out /= norms
        return out

    def transform_query(self, text: str) -> np.ndarray:
        """Vectorise a single query string. Returns float32 array [vocab]."""
        result = self.transform([text])
        return result[0]

    # ── persistence helpers ───────────────────────────────────────────────

    def vocab_size(self) -> int:
        return len(self._vocab)

    def get_state(self) -> dict:
        """Return serialisable state for saving alongside the index."""
        if not self._fitted or self._idf is None:
            return {}
        return {
            "vocab": self._vocab,
            "idf":   self._idf.tolist(),
        }

    def set_state(self, state: dict) -> None:
        """Restore from a previously saved state dict."""
        if not state:
            return
        self._vocab  = state["vocab"]
        self._idf    = np.array(state["idf"], dtype=np.float32)
        self._fitted = True


# ---------------------------------------------------------------------------
# Sentence-Transformers embedder (optional)
# ---------------------------------------------------------------------------


class SentenceTransformerEmbedder:
    """
    Dense embedder backed by sentence-transformers (must be installed).
    Model is downloaded on first use and cached by the library.
    """

    provider_name = "sentence-transformers"

    _DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        model_name = os.getenv("EMBED_MODEL", self._DEFAULT_MODEL)
        try:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            self._model = SentenceTransformer(model_name)
            logger.info("SentenceTransformerEmbedder loaded model=%s", model_name)
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers  "
                "or set EMBED_PROVIDER=tfidf to use the built-in embedder."
            ) from exc

    def fit(self, texts: list[str]) -> None:
        pass  # model is pre-trained; no fitting needed

    def transform(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(
            texts,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    def transform_query(self, text: str) -> np.ndarray:
        return self.transform([text])[0]

    def vocab_size(self) -> int:
        return 0   # dense embedder; no discrete vocabulary

    def get_state(self) -> dict:
        return {}  # model is loaded from disk on every instantiation

    def set_state(self, state: dict) -> None:
        pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_embedder() -> TFIDFEmbedder | SentenceTransformerEmbedder:
    """
    Return an embedder instance selected by the ``EMBED_PROVIDER`` env var.

    Values
    ------
    tfidf                  (default) — no extra dependencies
    sentence-transformers  — requires ``pip install sentence-transformers``
    """
    provider = os.getenv("EMBED_PROVIDER", "tfidf").lower().strip()

    if provider == "tfidf":
        return TFIDFEmbedder()

    if provider in ("sentence-transformers", "sentence_transformers", "st"):
        return SentenceTransformerEmbedder()

    raise ValueError(
        f"Unknown EMBED_PROVIDER='{provider}'. "
        "Supported: 'tfidf' (default), 'sentence-transformers'."
    )
