"""
Short, terminating validation tests for the Task 4 ingestion layer.

Tests are grouped into two sections:
  1. Unit tests — pure Python, no network, no filesystem side-effects.
  2. Import / wiring tests — verify that all modules import cleanly and the
     FastAPI app assembles correctly.

Run with:
    python -m pytest backend/tests/test_ingestion.py -v
or directly:
    python backend/tests/test_ingestion.py
"""

from __future__ import annotations

import sys
import os
import json
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path when run directly
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PASS = "\033[32mPASS\033[0m"
_FAIL = "\033[31mFAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def _test(name: str):
    """Decorator that registers a test function."""
    def decorator(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:
            _results.append((name, False, str(exc)))
        return fn
    return decorator


# ===========================================================================
# 1. Validator tests
# ===========================================================================

from backend.ingestion.validator import validate_github_url, canonical_url, ValidationError


@_test("validator: valid HTTPS URL")
def _():
    owner, repo = validate_github_url("https://github.com/fastapi/fastapi")
    assert owner == "fastapi" and repo == "fastapi"


@_test("validator: URL with .git suffix")
def _():
    owner, repo = validate_github_url("https://github.com/owner/my-repo.git")
    assert owner == "owner" and repo == "my-repo"


@_test("validator: trailing slash is accepted")
def _():
    owner, repo = validate_github_url("https://github.com/tiangolo/full-stack-fastapi-template/")
    assert owner == "tiangolo" and repo == "full-stack-fastapi-template"


@_test("validator: rejects empty string")
def _():
    try:
        validate_github_url("")
        raise AssertionError("should have raised")
    except ValidationError:
        pass


@_test("validator: rejects non-github host")
def _():
    try:
        validate_github_url("https://gitlab.com/owner/repo")
        raise AssertionError("should have raised")
    except ValidationError:
        pass


@_test("validator: rejects URL with only owner (no repo)")
def _():
    try:
        validate_github_url("https://github.com/torvalds")
        raise AssertionError("should have raised")
    except ValidationError:
        pass


@_test("validator: rejects non-URL string")
def _():
    try:
        validate_github_url("not-a-url")
        raise AssertionError("should have raised")
    except ValidationError:
        pass


@_test("validator: canonical_url produces .git URL")
def _():
    url = canonical_url("owner", "repo")
    assert url == "https://github.com/owner/repo.git"


# ===========================================================================
# 2. Cloner — repo_id_for is deterministic
# ===========================================================================

from backend.ingestion.cloner import repo_id_for


@_test("cloner: repo_id_for is deterministic (same URL → same ID)")
def _():
    a = repo_id_for("https://github.com/fastapi/fastapi")
    b = repo_id_for("https://github.com/fastapi/fastapi")
    assert a == b, f"Expected same id, got {a!r} vs {b!r}"


@_test("cloner: repo_id_for is case-insensitive")
def _():
    a = repo_id_for("https://github.com/FastAPI/FastAPI")
    b = repo_id_for("https://github.com/fastapi/fastapi")
    assert a == b


@_test("cloner: repo_id_for is 16 hex chars")
def _():
    rid = repo_id_for("https://github.com/owner/repo")
    assert len(rid) == 16 and all(c in "0123456789abcdef" for c in rid)


@_test("cloner: different URLs → different IDs")
def _():
    a = repo_id_for("https://github.com/owner/repo-a")
    b = repo_id_for("https://github.com/owner/repo-b")
    assert a != b


# ===========================================================================
# 3. Scanner unit tests (no filesystem I/O)
# ===========================================================================

from backend.ingestion.scanner import (
    _detect_language,
    _parse_requirements_txt,
    _parse_package_json,
    _parse_go_mod,
    _is_important,
)


@_test("scanner: _detect_language by extension")
def _():
    assert _detect_language("app.py")  == "Python"
    assert _detect_language("index.ts") == "TypeScript"
    assert _detect_language("main.go")  == "Go"
    assert _detect_language("lib.rs")   == "Rust"
    assert _detect_language("README.md") == "Markdown"


@_test("scanner: _detect_language by exact filename")
def _():
    assert _detect_language("Dockerfile") == "Dockerfile"
    assert _detect_language("Makefile")   == "Makefile"


@_test("scanner: _detect_language returns None for unknown")
def _():
    assert _detect_language("somefile.xyz123") is None


@_test("scanner: _parse_requirements_txt")
def _():
    txt = "fastapi>=0.100\nuvicorn[standard]\n# comment\n-r other.txt\npydantic==2.0\n"
    deps = _parse_requirements_txt(txt)
    assert "fastapi"  in deps
    assert "uvicorn"  in deps
    assert "pydantic" in deps
    assert "comment"  not in deps


@_test("scanner: _parse_package_json")
def _():
    pkg = json.dumps({
        "dependencies":    {"react": "^18", "react-dom": "^18"},
        "devDependencies": {"vite": "^5", "typescript": "^5"},
    })
    deps = _parse_package_json(pkg)
    assert "react"      in deps
    assert "vite"       in deps
    assert "typescript" in deps


@_test("scanner: _parse_go_mod")
def _():
    gomod = (
        "module github.com/example/app\n\ngo 1.21\n\n"
        "require (\n"
        "\tgithub.com/gin-gonic/gin v1.9.1\n"
        "\tgithub.com/stretchr/testify v1.8.4\n"
        ")\n"
    )
    deps = _parse_go_mod(gomod)
    assert "github.com/gin-gonic/gin"      in deps
    assert "github.com/stretchr/testify"  in deps


@_test("scanner: _is_important identifies README and entry points")
def _():
    assert _is_important("README.md",    "README.md")   is True
    assert _is_important("main.py",      "main.py")     is True
    assert _is_important("index.ts",     "index.ts")    is True
    assert _is_important("package.json", "package.json")is True
    assert _is_important("random.xyz",   "random.xyz")  is False


# ===========================================================================
# 4. Models round-trip (Pydantic serialisation)
# ===========================================================================

from backend.ingestion.models import (
    IngestionRecord, IngestionStatus, FileNode, RepoMetadata, ScanResult
)


@_test("models: IngestionRecord serialises / deserialises cleanly")
def _():
    r = IngestionRecord(
        repo_id  = "abc123",
        repo_url = "https://github.com/owner/repo",
        status   = IngestionStatus.ready,
        work_dir = "/tmp/repolens/abc123/repo",
    )
    dumped = r.model_dump_json()
    r2 = IngestionRecord.model_validate_json(dumped)
    assert r2.repo_id == "abc123"
    assert r2.status  == IngestionStatus.ready


@_test("models: FileNode with children serialises correctly")
def _():
    node = FileNode(
        name="src", path="src", type="directory",
        children=[
            FileNode(name="main.py", path="src/main.py", type="file", language="Python"),
        ]
    )
    d = node.model_dump()
    assert d["children"][0]["language"] == "Python"


@_test("models: ScanResult fields are all present")
def _():
    tree = FileNode(name="root", path="", type="directory", children=[])
    scan = ScanResult(
        file_count=10, directory_count=3, total_size_bytes=1024,
        languages=["Python"], primary_language="Python",
        frameworks=["FastAPI"], config_files=["pyproject.toml"],
        important_files=["README.md"], dependencies={},
        file_tree=tree,
    )
    assert scan.primary_language == "Python"
    assert "FastAPI" in scan.frameworks


# ===========================================================================
# 5. FastAPI app wiring — imports and route registration
# ===========================================================================

from backend.main import app


@_test("wiring: FastAPI app imports without error")
def _():
    assert app is not None
    assert app.title == "RepoLens API"


@_test("wiring: POST /api/analyze route is registered")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/analyze" in routes, f"Routes found: {sorted(routes)}"


@_test("wiring: GET /api/summary/{{repo_id}} route is registered")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/summary/{repo_id}" in routes, f"Routes found: {sorted(routes)}"


@_test("wiring: GET /api/structure/{{repo_id}} route is registered")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/structure/{repo_id}" in routes, f"Routes found: {sorted(routes)}"


@_test("wiring: GET /health route is still registered")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/health" in routes


# ===========================================================================
# 6. Scanner filesystem integration — scan a real (tiny) directory
# ===========================================================================

from backend.ingestion.scanner import scan_repository


@_test("scanner: scan_repository on a minimal synthetic tree")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        # Create a minimal fake repo
        (base / "README.md").write_text("# Hello", encoding="utf-8")
        (base / "main.py").write_text("print('hello')", encoding="utf-8")
        src = base / "src"
        src.mkdir()
        (src / "utils.py").write_text("def helper(): pass", encoding="utf-8")
        pkg = base / "pyproject.toml"
        pkg.write_text(
            '[project]\nname = "myapp"\ndependencies = ["fastapi>=0.100", "pydantic"]\n',
            encoding="utf-8",
        )
        # Directories that should be skipped
        (base / "node_modules").mkdir()
        (base / "node_modules" / "some_pkg.js").write_text("", encoding="utf-8")
        (base / "__pycache__").mkdir()

        result = scan_repository(base)

    assert result.file_count >= 4
    assert "Python"   in result.languages
    assert "Markdown" in result.languages
    assert result.primary_language == "Python"
    assert result.file_tree.type == "directory"
    # node_modules / __pycache__ must NOT appear in the tree
    child_names = {c.name for c in (result.file_tree.children or [])}
    assert "node_modules" not in child_names
    assert "__pycache__"  not in child_names
    assert "main.py" in child_names


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    # Use UTF-8 output on Windows so special characters don't crash
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)

    print(f"\n{'='*60}")
    print(f"  RepoLens Task 4 - ingestion layer validation")
    print(f"{'='*60}")
    for name, ok, err in _results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if err:
            print(f"         >> {err}")
    print(f"{'='*60}")
    print(f"  {passed}/{total} tests passed")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)
