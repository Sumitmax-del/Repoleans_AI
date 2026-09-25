"""
Short, terminating validation tests for the Task 6A RAG layer.

Grouped into:
  1. Chunk model round-trips
  2. Chunker unit tests (synthetic source files)
  3. TF-IDF embedder unit tests
  4. Index builder integration test (synthetic filesystem)
  5. Retriever integration test (query → ranked results)
  6. Pipeline wiring (no network calls)

Run with:
    python backend/tests/test_rag.py
or:
    python -m pytest backend/tests/test_rag.py -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Minimal test harness
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def _test(name: str):
    def decorator(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:
            import traceback
            _results.append((name, False, traceback.format_exc(limit=3)))
        return fn
    return decorator


# ===========================================================================
# 1. Model round-trips
# ===========================================================================

from backend.rag.models import Chunk, RetrievalResult, IndexMeta


@_test("models: Chunk serialises cleanly")
def _():
    c = Chunk(
        chunk_id="src/app.py:1", repo_id="abc", file_path="src/app.py",
        start_line=1, end_line=40, language="Python",
        text="def main():\n    pass\n", symbol="main", is_important=True,
    )
    d = c.model_dump()
    assert d["chunk_id"] == "src/app.py:1"
    assert d["is_important"] is True


@_test("models: RetrievalResult serialises cleanly")
def _():
    r = RetrievalResult(
        chunk_id="src/app.py:1", file_path="src/app.py",
        start_line=1, end_line=40, language="Python",
        text="def main(): pass", score=0.85, rank=1,
    )
    assert r.rank == 1 and r.score == 0.85


@_test("models: IndexMeta serialises / deserialises cleanly")
def _():
    m = IndexMeta(repo_id="abc", embed_provider="tfidf",
                  chunk_count=120, vocab_size=5000, vector_dim=5000)
    m2 = IndexMeta.model_validate_json(m.model_dump_json())
    assert m2.chunk_count == 120


# ===========================================================================
# 2. Chunker
# ===========================================================================

from backend.rag.chunker import chunk_repository, _tokenise, _nearest_symbol


@_test("chunker: _tokenise splits camelCase and snake_case")
def _():
    toks = _tokenise("getUserById")
    assert "get" in toks
    assert "user" in toks
    assert "by" in toks
    assert "id" in toks

    toks2 = _tokenise("my_function_name")
    assert "my" in toks2
    assert "function" in toks2


@_test("chunker: _nearest_symbol finds def name")
def _():
    lines = ["def calculate_total(items):", "    return sum(items)"]
    assert _nearest_symbol(lines) == "calculate_total"


@_test("chunker: _nearest_symbol finds class name")
def _():
    lines = ["class UserService:", "    pass"]
    assert _nearest_symbol(lines) == "UserService"


@_test("chunker: small Python file → single chunk with correct line numbers")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        src = "def hello():\n    print('hi')\n"
        (base / "hello.py").write_text(src, encoding="utf-8")
        chunks = chunk_repository(base, ["hello.py"], "r1",
                                  important_files={"hello.py"},
                                  language_map={"hello.py": "Python"})
    assert len(chunks) == 1
    c = chunks[0]
    assert c.file_path == "hello.py"
    assert c.start_line == 1
    assert c.end_line == 2
    assert c.language == "Python"
    assert c.is_important is True
    assert c.symbol == "hello"


@_test("chunker: large Python file splits into multiple chunks")
def _():
    # 120 lines with function boundaries every 10 lines
    lines = []
    for i in range(12):
        lines.append(f"def func_{i}(x):")
        lines += [f"    return x + {j}" for j in range(9)]
    src = "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "big.py").write_text(src, encoding="utf-8")
        chunks = chunk_repository(base, ["big.py"], "r1",
                                  language_map={"big.py": "Python"})
    assert len(chunks) >= 2
    # Line numbers must be contiguous and 1-based
    for c in chunks:
        assert c.start_line >= 1
        assert c.end_line >= c.start_line


@_test("chunker: markdown file splits on headings")
def _():
    md = "# Title\n\nIntro paragraph.\n\n## Section 1\n\nContent 1.\n\n## Section 2\n\nContent 2.\n"
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "README.md").write_text(md, encoding="utf-8")
        chunks = chunk_repository(base, ["README.md"], "r1",
                                  language_map={"README.md": "Markdown"})
    assert len(chunks) >= 1
    assert all(c.file_path == "README.md" for c in chunks)


@_test("chunker: lock files and binaries are skipped")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "package-lock.json").write_text("{}", encoding="utf-8")
        (base / "image.png").write_bytes(b"\x89PNG\r\n")
        chunks = chunk_repository(base, ["package-lock.json", "image.png"], "r1")
    assert chunks == []


@_test("chunker: chunk_id format is file_path:start_line")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "app.py").write_text("x = 1\n", encoding="utf-8")
        chunks = chunk_repository(base, ["app.py"], "r1")
    assert chunks[0].chunk_id == "app.py:1"


# ===========================================================================
# 3. TF-IDF embedder
# ===========================================================================

from backend.rag.embedder import TFIDFEmbedder, get_embedder
import numpy as np


@_test("embedder: TFIDFEmbedder fit+transform produces correct shape")
def _():
    emb = TFIDFEmbedder()
    texts = [
        "def get_user(user_id): return db.query(user_id)",
        "def create_user(name, email): db.insert(name, email)",
        "class UserService: pass",
        "router = APIRouter()",
        "app = FastAPI()",
    ]
    emb.fit(texts)
    vecs = emb.transform(texts)
    assert vecs.shape[0] == len(texts)
    assert vecs.shape[1] > 0
    assert vecs.dtype == np.float32


@_test("embedder: TFIDFEmbedder vectors are L2-normalised")
def _():
    emb = TFIDFEmbedder()
    texts = ["hello world function", "class foo bar", "import os sys path"]
    emb.fit(texts)
    vecs = emb.transform(texts)
    norms = np.linalg.norm(vecs, axis=1)
    # Non-zero rows should have norm ≈ 1
    non_zero = norms[norms > 1e-6]
    assert np.allclose(non_zero, 1.0, atol=1e-5)


@_test("embedder: transform_query returns 1-D array matching vocab dim")
def _():
    emb = TFIDFEmbedder()
    texts = ["routing function handler path", "database model query", "middleware auth"]
    emb.fit(texts)
    q = emb.transform_query("how does routing work")
    assert q.ndim == 1
    assert q.shape[0] == emb.vocab_size()


@_test("embedder: state save/restore round-trip")
def _():
    emb = TFIDFEmbedder()
    texts = ["alpha beta gamma", "delta epsilon zeta", "eta theta iota"]
    emb.fit(texts)
    state = emb.get_state()
    assert "vocab" in state and "idf" in state

    emb2 = TFIDFEmbedder()
    emb2.set_state(state)
    v1 = emb.transform_query("alpha gamma")
    v2 = emb2.transform_query("alpha gamma")
    assert np.allclose(v1, v2, atol=1e-6)


@_test("embedder: get_embedder() returns TFIDFEmbedder by default")
def _():
    import os
    os.environ.pop("EMBED_PROVIDER", None)
    e = get_embedder()
    assert isinstance(e, TFIDFEmbedder)


@_test("embedder: cosine similarity between similar texts is higher than dissimilar")
def _():
    emb = TFIDFEmbedder()
    texts = [
        "def get_user(id): return users[id]",
        "def fetch_user(user_id): return db.get(user_id)",
        "SELECT * FROM orders WHERE status = 'active'",
        "terraform resource aws_instance server {}",
    ]
    emb.fit(texts)
    vecs = emb.transform(texts)
    # user retrieval functions should be closer to each other than to SQL
    sim_similar    = float(vecs[0] @ vecs[1])
    sim_dissimilar = float(vecs[0] @ vecs[2])
    assert sim_similar > sim_dissimilar, (
        f"Expected sim_similar={sim_similar:.4f} > sim_dissimilar={sim_dissimilar:.4f}"
    )


# ===========================================================================
# 4. Index builder integration
# ===========================================================================

from backend.rag.index import build_index_sync, load_index, index_exists


def _make_repo(tmp: str) -> tuple[str, list[str], set[str], dict[str, str]]:
    """Create a minimal synthetic repo, return (work_dir, file_paths, important, lang_map)."""
    base = Path(tmp)
    (base / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n\n"
        "@app.get('/health')\ndef health(): return {'ok': True}\n\n"
        "@app.post('/users')\ndef create_user(name: str): pass\n",
        encoding="utf-8",
    )
    (base / "utils.py").write_text(
        "def validate_email(email: str) -> bool:\n    return '@' in email\n\n"
        "def hash_password(pw: str) -> str:\n    import hashlib\n    return hashlib.md5(pw.encode()).hexdigest()\n",
        encoding="utf-8",
    )
    (base / "README.md").write_text(
        "# My App\n\n## Overview\nA FastAPI application.\n\n## Installation\n`pip install -r requirements.txt`\n",
        encoding="utf-8",
    )
    (base / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
    file_paths  = ["main.py", "utils.py", "README.md", "requirements.txt"]
    important   = {"main.py", "README.md"}
    lang_map    = {"main.py": "Python", "utils.py": "Python",
                   "README.md": "Markdown", "requirements.txt": "Text"}
    return str(base), file_paths, important, lang_map


@_test("index: build_index_sync produces valid IndexMeta")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        work_dir, file_paths, important, lang_map = _make_repo(tmp)
        meta = build_index_sync("idx_test", work_dir, file_paths, important, lang_map)
    assert meta.repo_id == "idx_test"
    assert meta.chunk_count > 0
    assert meta.vector_dim > 0
    assert meta.embed_provider == "tfidf"


@_test("index: index_exists returns True after build")
def _():
    with tempfile.TemporaryDirectory() as repodir:
        import os
        os.environ["REPOLENS_WORK_DIR"] = repodir   # isolate index files
        work_dir, file_paths, important, lang_map = _make_repo(repodir + "/repo")
        Path(repodir + "/repo").mkdir(exist_ok=True)
        build_index_sync("exists_test", work_dir, file_paths, important, lang_map)
        assert index_exists("exists_test")
        os.environ.pop("REPOLENS_WORK_DIR")


@_test("index: load_index returns (vectors, chunks, meta) after build")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        import os
        os.environ["REPOLENS_WORK_DIR"] = tmp
        work_dir, file_paths, important, lang_map = _make_repo(tmp + "/repo")
        Path(tmp + "/repo").mkdir(exist_ok=True)
        build_index_sync("load_test", work_dir, file_paths, important, lang_map)
        loaded = load_index("load_test")
        os.environ.pop("REPOLENS_WORK_DIR")

    assert loaded is not None
    vectors, chunks, meta = loaded
    assert vectors.ndim == 2
    assert len(chunks) == meta.chunk_count
    assert vectors.shape[0] == meta.chunk_count
    assert vectors.shape[1] == meta.vector_dim


@_test("index: all chunks have correct repo_id and non-empty text")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        import os
        os.environ["REPOLENS_WORK_DIR"] = tmp
        work_dir, file_paths, important, lang_map = _make_repo(tmp + "/repo")
        Path(tmp + "/repo").mkdir(exist_ok=True)
        build_index_sync("chunks_test", work_dir, file_paths, important, lang_map)
        loaded = load_index("chunks_test")
        os.environ.pop("REPOLENS_WORK_DIR")

    assert loaded is not None
    _, chunks, _ = loaded
    for c in chunks:
        assert c.repo_id == "chunks_test"
        assert c.text.strip() != ""
        assert c.start_line >= 1
        assert c.end_line >= c.start_line


# ===========================================================================
# 5. Retriever integration
# ===========================================================================

from backend.rag.retriever import retrieve


@_test("retriever: returns empty list for unknown repo_id")
def _():
    results = retrieve("definitely_nonexistent_repo_xyz", "what does this do")
    assert results == []


@_test("retriever: returns empty list for blank query")
def _():
    results = retrieve("any_repo", "")
    assert results == []


@_test("retriever: returns ranked results for a real index")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        import os
        os.environ["REPOLENS_WORK_DIR"] = tmp
        work_dir, file_paths, important, lang_map = _make_repo(tmp + "/repo")
        Path(tmp + "/repo").mkdir(exist_ok=True)
        build_index_sync("retr_test", work_dir, file_paths, important, lang_map)
        results = retrieve("retr_test", "how does routing work in FastAPI")
        os.environ.pop("REPOLENS_WORK_DIR")

    assert len(results) > 0
    # Results must be ranked 1, 2, 3, …
    for i, r in enumerate(results):
        assert r.rank == i + 1
    # Scores must be descending
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@_test("retriever: top result for 'validate email' contains validation logic")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        import os
        os.environ["REPOLENS_WORK_DIR"] = tmp
        work_dir, file_paths, important, lang_map = _make_repo(tmp + "/repo")
        Path(tmp + "/repo").mkdir(exist_ok=True)
        build_index_sync("retr_test2", work_dir, file_paths, important, lang_map)
        results = retrieve("retr_test2", "email validation function", top_k=3)
        os.environ.pop("REPOLENS_WORK_DIR")

    assert len(results) > 0
    # The utils.py file with validate_email should appear somewhere in top-3
    files = [r.file_path for r in results]
    assert any("utils" in f for f in files), f"Expected utils.py in top results, got: {files}"


@_test("retriever: each result has file_path, start_line, end_line, score, text")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        import os
        os.environ["REPOLENS_WORK_DIR"] = tmp
        work_dir, file_paths, important, lang_map = _make_repo(tmp + "/repo")
        Path(tmp + "/repo").mkdir(exist_ok=True)
        build_index_sync("retr_test3", work_dir, file_paths, important, lang_map)
        results = retrieve("retr_test3", "create user endpoint", top_k=5)
        os.environ.pop("REPOLENS_WORK_DIR")

    assert len(results) > 0
    for r in results:
        assert r.file_path != ""
        assert r.start_line >= 1
        assert r.end_line >= r.start_line
        assert 0.0 <= r.score <= 1.0
        assert r.text.strip() != ""


# ===========================================================================
# 6. Pipeline wiring (import check — no network)
# ===========================================================================

from backend.ingestion.pipeline import run_ingestion, _build_language_map, _walk


@_test("pipeline: _build_language_map flattens FileNode tree correctly")
def _():
    from backend.ingestion.models import FileNode
    tree = FileNode(
        name="root", path="", type="directory",
        children=[
            FileNode(name="main.py", path="main.py", type="file", language="Python"),
            FileNode(name="src", path="src", type="directory", children=[
                FileNode(name="app.ts", path="src/app.ts", type="file", language="TypeScript"),
            ]),
        ]
    )
    lang_map = _build_language_map(tree)
    assert lang_map["main.py"]    == "Python"
    assert lang_map["src/app.ts"] == "TypeScript"


@_test("pipeline: build_index and index_exists imported cleanly")
def _():
    from backend.rag.index import build_index, index_exists
    assert callable(build_index)
    assert callable(index_exists)


@_test("pipeline: retrieve imported cleanly from rag.retriever")
def _():
    from backend.rag.retriever import retrieve
    assert callable(retrieve)


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)

    print(f"\n{'='*62}")
    print(f"  RepoLens Task 6A - RAG layer validation")
    print(f"{'='*62}")
    for name, ok, err in _results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if err:
            # Show first 3 lines of traceback
            lines = [l for l in err.strip().splitlines() if l.strip()][:4]
            for line in lines:
                print(f"         | {line}")
    print(f"{'='*62}")
    print(f"  {passed}/{total} tests passed")
    print(f"{'='*62}\n")

    sys.exit(0 if passed == total else 1)
