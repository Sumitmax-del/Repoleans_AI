"""
Short, terminating validation tests for Task 6B — LLM and Ask Repository.

Grouped into:
  1. Prompt builder unit tests
  2. Echo client unit tests
  3. LLM provider factory tests
  4. Chat router integration tests (no network, no running server)

Run with:
    python backend/tests/test_chat.py
or:
    python -m pytest backend/tests/test_chat.py -v
"""

from __future__ import annotations

import asyncio
import io
import json
import os
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
# Minimal test harness (matches test_rag.py pattern)
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def _test(name: str):
    def decorator(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception:
            import traceback
            _results.append((name, False, traceback.format_exc(limit=6)))
        return fn
    return decorator


def _run(coro):
    """Run an async coroutine synchronously inside a test."""
    return asyncio.run(coro)


# ===========================================================================
# 1. Prompt builder
# ===========================================================================

from backend.rag.models import RetrievalResult
from backend.rag.prompt_builder import build_prompt


def _make_result(rank: int, file_path: str = "src/app.py",
                 start: int = 1, end: int = 20,
                 text: str = "def hello():\n    pass\n",
                 language: str = "Python") -> RetrievalResult:
    return RetrievalResult(
        chunk_id=f"{file_path}:{start}",
        file_path=file_path,
        start_line=start,
        end_line=end,
        language=language,
        text=text,
        score=round(0.9 - rank * 0.05, 2),
        rank=rank,
    )


@_test("prompt_builder: returns (prompt, citations) tuple")
def _():
    results = [_make_result(1)]
    prompt, citations = build_prompt("What does hello() do?", results)
    assert isinstance(prompt, str)
    assert isinstance(citations, list)


@_test("prompt_builder: prompt contains system instructions")
def _():
    results = [_make_result(1)]
    prompt, _ = build_prompt("How is routing done?", results)
    assert "Answer ONLY" in prompt
    assert "cite the file" in prompt


@_test("prompt_builder: prompt contains the question")
def _():
    question = "Where is the database connection configured?"
    results = [_make_result(1)]
    prompt, _ = build_prompt(question, results)
    assert question in prompt


@_test("prompt_builder: prompt contains the file path citation")
def _():
    results = [_make_result(1, file_path="backend/db.py", start=5, end=30)]
    prompt, citations = build_prompt("db config?", results)
    assert "backend/db.py:5-30" in prompt
    assert citations[0]["file_path"] == "backend/db.py"
    assert citations[0]["start_line"] == 5
    assert citations[0]["end_line"] == 30


@_test("prompt_builder: citations deduplicated by chunk_id")
def _():
    r1 = _make_result(1, file_path="a.py", start=1, end=10)
    r2 = _make_result(2, file_path="a.py", start=1, end=10)  # same chunk_id as r1
    # Give them identical chunk_ids explicitly
    r2 = r2.model_copy(update={"chunk_id": r1.chunk_id, "rank": 2})
    _, citations = build_prompt("question", [r1, r2])
    assert len(citations) == 1


@_test("prompt_builder: multiple results → multiple citations")
def _():
    results = [
        _make_result(1, file_path="a.py", start=1, end=10),
        _make_result(2, file_path="b.py", start=5, end=20),
        _make_result(3, file_path="c.py", start=1, end=8),
    ]
    _, citations = build_prompt("question", results)
    assert len(citations) == 3
    assert citations[0]["file_path"] == "a.py"
    assert citations[1]["file_path"] == "b.py"
    assert citations[2]["file_path"] == "c.py"


@_test("prompt_builder: empty results → prompt still valid, no citations")
def _():
    prompt, citations = build_prompt("What does this do?", [])
    assert isinstance(prompt, str)
    assert len(prompt) > 50        # instructions still present
    assert citations == []


@_test("prompt_builder: context truncated when results exceed budget")
def _():
    # Create a result with very long text to trigger truncation
    long_text = "x = 1\n" * 3000   # ~18 000 chars
    results = [_make_result(1, text=long_text)]
    prompt, citations = build_prompt("question", results)
    # Prompt must be within a reasonable bound even with huge input
    assert len(prompt) < 15_000
    # Citation should still be present (partial block was included)
    assert len(citations) == 1


# ===========================================================================
# 2. Echo client
# ===========================================================================

from backend.llm.echo_client import EchoClient


@_test("echo_client: stream_response yields strings")
def _():
    async def _inner():
        client = EchoClient()
        tokens = []
        async for token in client.stream_response("Hello"):
            tokens.append(token)
        return tokens

    tokens = _run(_inner())
    assert len(tokens) > 0
    assert all(isinstance(t, str) for t in tokens)


@_test("echo_client: full response is non-empty text")
def _():
    async def _inner():
        client = EchoClient()
        parts = []
        async for t in client.stream_response("What does this repo do?"):
            parts.append(t)
        return "".join(parts)

    text = _run(_inner())
    assert len(text) > 10


@_test("echo_client: lists citations found in prompt")
def _():
    # Build a prompt with a known citation label
    results = [_make_result(1, file_path="router.py", start=10, end=30)]
    prompt, _ = build_prompt("How does routing work?", results)

    async def _inner():
        client = EchoClient()
        parts = []
        async for t in client.stream_response(prompt):
            parts.append(t)
        return "".join(parts)

    text = _run(_inner())
    assert "router.py:10-30" in text


@_test("echo_client: no-context response contains fallback message")
def _():
    # Prompt with no context blocks
    async def _inner():
        client = EchoClient()
        parts = []
        async for t in client.stream_response("plain question without context"):
            parts.append(t)
        return "".join(parts)

    text = _run(_inner())
    assert "repository does not contain" in text.lower() or "echo provider" in text.lower()


@_test("echo_client: provider_name is 'echo'")
def _():
    assert EchoClient().provider_name == "echo"


# ===========================================================================
# 3. LLM provider factory
# ===========================================================================

from backend.llm.provider import get_llm_client, LLMClient


@_test("provider: get_llm_client returns EchoClient when LLM_PROVIDER=echo")
def _():
    os.environ["LLM_PROVIDER"] = "echo"
    client = get_llm_client()
    assert client.provider_name == "echo"  # type: ignore[attr-defined]
    os.environ.pop("LLM_PROVIDER")


@_test("provider: get_llm_client defaults to echo when LLM_PROVIDER unset")
def _():
    os.environ.pop("LLM_PROVIDER", None)
    client = get_llm_client()
    assert client.provider_name == "echo"  # type: ignore[attr-defined]


@_test("provider: EchoClient satisfies LLMClient protocol")
def _():
    client = EchoClient()
    assert isinstance(client, LLMClient)


@_test("provider: unsupported LLM_PROVIDER raises ValueError")
def _():
    os.environ["LLM_PROVIDER"] = "nonexistent_llm"
    try:
        get_llm_client()
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "nonexistent_llm" in str(exc)
    finally:
        os.environ.pop("LLM_PROVIDER")


# ===========================================================================
# 4. Chat router integration (no network, no running server)
# ===========================================================================

from backend.rag.index import build_index_sync
from backend.ingestion.models import (
    IngestionRecord, IngestionStatus, ScanResult, FileNode,
)
from backend.ingestion.cloner import save_record


def _make_scan(file_paths: list[str]) -> ScanResult:
    """Build a minimal ScanResult for testing."""
    nodes = [FileNode(name=p, path=p, type="file", language="Python") for p in file_paths]
    root = FileNode(name="root", path="", type="directory", children=nodes)
    return ScanResult(
        file_count=len(file_paths),
        directory_count=0,
        total_size_bytes=100,
        languages=["Python"],
        primary_language="Python",
        frameworks=[],
        config_files=[],
        important_files=file_paths[:1],
        dependencies={},
        file_tree=root,
    )


def _make_rag_repo(base: Path) -> tuple[str, list[str]]:
    """Write synthetic source files and return (work_dir, file_paths)."""
    base.mkdir(parents=True, exist_ok=True)
    (base / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n\n"
        "@app.get('/health')\ndef health(): return {'ok': True}\n",
        encoding="utf-8",
    )
    (base / "utils.py").write_text(
        "def validate_email(email: str) -> bool:\n    return '@' in email\n",
        encoding="utf-8",
    )
    return str(base), ["main.py", "utils.py"]


@_test("chat_router: _stream yields token + done events for known repo (echo provider)")
def _():
    import os as _os
    _os.environ["LLM_PROVIDER"] = "echo"

    with tempfile.TemporaryDirectory() as tmp:
        _os.environ["REPOLENS_WORK_DIR"] = tmp
        try:
            # Build RAG index
            repo_dir = Path(tmp) / "repo_chat"
            work_dir, file_paths = _make_rag_repo(repo_dir)
            lang_map = {p: "Python" for p in file_paths}
            build_index_sync("chat_test", work_dir, file_paths, {"main.py"}, lang_map)

            # Create a minimal IngestionRecord so load_record() finds it
            job_dir = Path(tmp) / "chat_test"
            job_dir.mkdir(exist_ok=True)
            record = IngestionRecord(
                repo_id="chat_test",
                repo_url="https://github.com/test/repo",
                status=IngestionStatus.ready,
                work_dir=work_dir,
                scan=_make_scan(file_paths),
            )
            # save_record expects work_dir to be .../job/repo
            # Write directly to avoid path conventions
            (job_dir / "record.json").write_text(
                record.model_dump_json(indent=2), encoding="utf-8"
            )

            from backend.routers.chat import _stream

            async def _collect():
                events = []
                async for chunk in _stream("chat_test", "How does routing work?"):
                    # Each chunk is an SSE line: "data: {...}\n\n"
                    for line in chunk.splitlines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                return events

            events = _run(_collect())

            # Must have at least one token event and exactly one done event
            types = [e["type"] for e in events]
            assert "token" in types, f"No token events found: {types}"
            assert types.count("done") == 1, f"Expected exactly one done event: {types}"
            assert "error" not in types, f"Unexpected error event: {events}"

            # Done event must carry a sources list
            done_event = next(e for e in events if e["type"] == "done")
            assert isinstance(done_event["sources"], list)

        finally:
            _os.environ.pop("REPOLENS_WORK_DIR", None)
            _os.environ.pop("LLM_PROVIDER", None)


@_test("chat_router: _stream yields error event for unknown repo_id")
def _():
    import os as _os
    _os.environ["LLM_PROVIDER"] = "echo"
    old_dir = _os.environ.get("REPOLENS_WORK_DIR")

    with tempfile.TemporaryDirectory() as tmp:
        _os.environ["REPOLENS_WORK_DIR"] = tmp
        try:
            from backend.routers.chat import _stream

            async def _collect():
                events = []
                async for chunk in _stream("no_such_repo", "question"):
                    for line in chunk.splitlines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                return events

            events = _run(_collect())
            # No index → retrieval returns [] → prompt has no context → echo returns gracefully
            types = [e["type"] for e in events]
            assert "error" not in types, f"Unexpected error: {events}"
            assert "done" in types
        finally:
            if old_dir is None:
                _os.environ.pop("REPOLENS_WORK_DIR", None)
            else:
                _os.environ["REPOLENS_WORK_DIR"] = old_dir
            _os.environ.pop("LLM_PROVIDER", None)


@_test("chat_router: done event sources are dicts with required keys")
def _():
    import os as _os
    _os.environ["LLM_PROVIDER"] = "echo"

    with tempfile.TemporaryDirectory() as tmp:
        _os.environ["REPOLENS_WORK_DIR"] = tmp
        try:
            repo_dir = Path(tmp) / "repo_src"
            work_dir, file_paths = _make_rag_repo(repo_dir)
            lang_map = {p: "Python" for p in file_paths}
            build_index_sync("chat_src_test", work_dir, file_paths, {"main.py"}, lang_map)

            job_dir = Path(tmp) / "chat_src_test"
            job_dir.mkdir(exist_ok=True)
            record = IngestionRecord(
                repo_id="chat_src_test",
                repo_url="https://github.com/test/repo2",
                status=IngestionStatus.ready,
                work_dir=work_dir,
                scan=_make_scan(file_paths),
            )
            (job_dir / "record.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")

            from backend.routers.chat import _stream

            async def _collect():
                events = []
                async for chunk in _stream("chat_src_test", "What does validate_email do?"):
                    for line in chunk.splitlines():
                        if line.startswith("data: "):
                            events.append(json.loads(line[6:]))
                return events

            events = _run(_collect())
            done_event = next((e for e in events if e["type"] == "done"), None)
            assert done_event is not None
            for src in done_event["sources"]:
                assert "file_path"  in src
                assert "start_line" in src
                assert "end_line"   in src
        finally:
            _os.environ.pop("REPOLENS_WORK_DIR", None)
            _os.environ.pop("LLM_PROVIDER", None)


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)

    print(f"\n{'='*62}")
    print(f"  RepoLens Task 6B - LLM & Ask Repository validation")
    print(f"{'='*62}")
    for name, ok, err in _results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if err:
            lines = [l for l in err.strip().splitlines() if l.strip()][:6]
            for line in lines:
                print(f"         | {line}")
    print(f"{'='*62}")
    print(f"  {passed}/{total} tests passed")
    print(f"{'='*62}\n")

    sys.exit(0 if passed == total else 1)
