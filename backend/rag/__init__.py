# RAG pipeline — Task 6A.
#
# Modules
# -------
# models.py    — Chunk, RetrievalResult, IndexMeta (shared types)
# chunker.py   — line-range aware source file chunker
# embedder.py  — pluggable embedder (TF-IDF default; sentence-transformers optional)
# index.py     — index builder, persistence helpers (rag_*.npy / rag_*.json)
# retriever.py — semantic search: query → ranked RetrievalResult list
