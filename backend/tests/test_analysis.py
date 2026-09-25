"""
Short, terminating validation tests for the Task 5 analysis layer.

Grouped into:
  1. Model round-trips
  2. Route detection unit tests
  3. Entry-point classifier unit tests
  4. Directory classifier unit tests
  5. Architecture builder unit tests
  6. Engine integration test (synthetic filesystem)
  7. API wiring (route registration)

Run with:
    python backend/tests/test_analysis.py
or:
    python -m pytest backend/tests/test_analysis.py -v
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path when run directly
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ---------------------------------------------------------------------------
# Minimal test harness (same pattern as test_ingestion.py)
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def _test(name: str):
    def decorator(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:
            _results.append((name, False, str(exc)))
        return fn
    return decorator


# ===========================================================================
# 1. Model round-trips
# ===========================================================================

from backend.ingestion.models import (
    AnalysisResult, ArchLayer, ArchNode, EntryPoint,
    RouteDefinition, SourceDirectory,
)


@_test("models: RouteDefinition serialises cleanly")
def _():
    r = RouteDefinition(method="GET", path="/users/{id}", file="api/users.py", line=42,
                        handler="get_user", framework="FastAPI")
    d = r.model_dump()
    assert d["method"] == "GET" and d["path"] == "/users/{id}"


@_test("models: EntryPoint serialises cleanly")
def _():
    e = EntryPoint(file="main.py", kind="web_server", confidence="high",
                   reason="Conventional Python app entry point")
    assert e.confidence == "high"


@_test("models: AnalysisResult serialises / deserialises cleanly")
def _():
    ar = AnalysisResult(
        repo_id="test123",
        routes=[RouteDefinition(method="POST", path="/items", file="app.py", line=10)],
        entry_points=[EntryPoint(file="main.py", kind="web_server",
                                 confidence="high", reason="uvicorn.run")],
        arch_layers=[ArchLayer(id="entry", label="Entry Point", color="blue",
                               nodes=[ArchNode(name="uvicorn", file="main.py",
                                               description="ASGI server")])],
        summary_text="A FastAPI application.",
        route_count=1,
    )
    json_str = ar.model_dump_json()
    ar2 = AnalysisResult.model_validate_json(json_str)
    assert ar2.repo_id == "test123"
    assert ar2.route_count == 1
    assert ar2.arch_layers[0].id == "entry"


# ===========================================================================
# 2. Route detection
# ===========================================================================

from backend.analysis.routes import detect_routes


@_test("routes: FastAPI decorator detected")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "app.py").write_text(
            '@app.get("/users")\nasync def list_users(): pass\n'
            '@router.post("/users")\nasync def create_user(): pass\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["app.py"])
    assert len(routes) == 2
    methods = {r.method for r in routes}
    paths   = {r.path   for r in routes}
    assert "GET"  in methods
    assert "POST" in methods
    assert "/users" in paths


@_test("routes: Flask route detected")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "views.py").write_text(
            '@app.route("/items", methods=["GET", "POST"])\ndef items(): pass\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["views.py"])
    assert len(routes) == 1
    assert routes[0].path == "/items"
    assert "GET" in routes[0].method


@_test("routes: Express route detected")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "server.js").write_text(
            'app.get("/health", (req, res) => res.json({ok:true}));\n'
            'app.post("/users", createUser);\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["server.js"])
    assert any(r.path == "/health" for r in routes)
    assert any(r.method == "POST" for r in routes)


@_test("routes: Spring GetMapping detected")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "UserController.java").write_text(
            '@GetMapping("/api/users")\npublic List<User> getUsers() {}\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["UserController.java"])
    assert len(routes) == 1
    assert routes[0].path == "/api/users"
    assert routes[0].method == "GET"


@_test("routes: Go Gin route detected")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "main.go").write_text(
            'r.GET("/ping", func(c *gin.Context) {})\n'
            'r.POST("/users", createUser)\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["main.go"])
    paths = {r.path for r in routes}
    assert "/ping"  in paths
    assert "/users" in paths


@_test("routes: duplicate routes are not emitted twice")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "app.py").write_text(
            '@app.get("/users")\nasync def a(): pass\n'
            '@app.get("/users")\nasync def b(): pass\n',
            encoding="utf-8",
        )
        routes = detect_routes(base, ["app.py"])
    assert len(routes) == 1


@_test("routes: non-source files are skipped gracefully")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        routes = detect_routes(base, ["nonexistent.py"])
    assert routes == []


# ===========================================================================
# 3. Entry-point classifier
# ===========================================================================

from backend.analysis.entrypoints import classify_entry_points


@_test("entrypoints: main.py classified as web_server high")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "main.py").write_text("import uvicorn\nuvicorn.run(app)\n", encoding="utf-8")
        eps = classify_entry_points(base, ["main.py"])
    assert any(e.file == "main.py" and e.kind == "web_server" and e.confidence == "high"
               for e in eps)


@_test("entrypoints: manage.py classified as cli")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "manage.py").write_text("#!/usr/bin/env python\n", encoding="utf-8")
        eps = classify_entry_points(base, ["manage.py"])
    assert any(e.kind == "cli" for e in eps)


@_test("entrypoints: package.json classified as config")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "package.json").write_text('{"name":"myapp"}', encoding="utf-8")
        eps = classify_entry_points(base, ["package.json"])
    assert any(e.kind == "config" for e in eps)


@_test("entrypoints: content hint picks up uvicorn.run")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        fname = "bootstrap.py"
        (base / fname).write_text(
            "import uvicorn\nif __name__ == '__main__':\n    uvicorn.run(app)\n",
            encoding="utf-8",
        )
        eps = classify_entry_points(base, [fname])
    assert any(e.kind == "web_server" for e in eps)


# ===========================================================================
# 4. Directory classifier
# ===========================================================================

from backend.ingestion.models import FileNode
from backend.analysis.directories import classify_directories


def _make_tree(dirs_and_files: dict[str, list[str]]) -> FileNode:
    """Build a minimal FileNode tree for testing."""
    children = []
    for dname, fnames in dirs_and_files.items():
        file_children = [
            FileNode(name=f, path=f"{dname}/{f}", type="file")
            for f in fnames
        ]
        children.append(FileNode(name=dname, path=dname, type="directory",
                                 children=file_children))
    return FileNode(name="root", path="", type="directory", children=children)


@_test("directories: tests/ classified as tests")
def _():
    tree = _make_tree({"tests": ["test_app.py", "test_router.py"]})
    with tempfile.TemporaryDirectory() as tmp:
        dirs = classify_directories(Path(tmp), tree)
    assert any(d.role == "tests" for d in dirs)


@_test("directories: docs/ classified as docs")
def _():
    tree = _make_tree({"docs": ["index.md", "guide.md"]})
    with tempfile.TemporaryDirectory() as tmp:
        dirs = classify_directories(Path(tmp), tree)
    assert any(d.role == "docs" for d in dirs)


@_test("directories: src/ classified as source")
def _():
    tree = _make_tree({"src": ["app.py", "utils.py"]})
    with tempfile.TemporaryDirectory() as tmp:
        dirs = classify_directories(Path(tmp), tree)
    assert any(d.role == "source" for d in dirs)


@_test("directories: infra/ classified as infra")
def _():
    tree = _make_tree({"infra": ["main.tf", "variables.tf"]})
    with tempfile.TemporaryDirectory() as tmp:
        dirs = classify_directories(Path(tmp), tree)
    assert any(d.role == "infra" for d in dirs)


# ===========================================================================
# 5. Architecture builder
# ===========================================================================

from backend.ingestion.models import ScanResult
from backend.analysis.architecture import build_arch_layers, build_summary_text


def _make_scan(frameworks: list[str], deps: dict | None = None,
               important_files: list[str] | None = None) -> ScanResult:
    tree = FileNode(name="root", path="", type="directory", children=[])
    return ScanResult(
        file_count=10, directory_count=2, total_size_bytes=1024,
        languages=["Python"], primary_language="Python",
        frameworks=frameworks,
        config_files=[],
        important_files=important_files or [],
        dependencies=deps or {},
        file_tree=tree,
    )


@_test("architecture: FastAPI stack produces entry + app + routing layers")
def _():
    scan = _make_scan(
        frameworks=["FastAPI", "Pydantic", "Starlette"],
        deps={"requirements.txt": ["fastapi", "uvicorn", "pydantic"]},
    )
    layers = build_arch_layers(scan, [], [])
    layer_ids = {l.id for l in layers}
    assert "entry"    in layer_ids
    assert "app"      in layer_ids
    assert "routing"  in layer_ids
    assert "validation" in layer_ids


@_test("architecture: Django stack produces entry + app + routing layers")
def _():
    scan = _make_scan(frameworks=["Django"])
    layers = build_arch_layers(scan, [], [])
    layer_ids = {l.id for l in layers}
    assert "entry" in layer_ids
    assert "app"   in layer_ids


@_test("architecture: Express stack produces entry + app + routing layers")
def _():
    scan = _make_scan(frameworks=["Express"])
    layers = build_arch_layers(scan, [], [])
    layer_ids = {l.id for l in layers}
    assert "entry"   in layer_ids
    assert "routing" in layer_ids


@_test("architecture: Celery dep triggers task queue layer")
def _():
    scan = _make_scan(
        frameworks=["FastAPI"],
        deps={"requirements.txt": ["fastapi", "celery"]},
    )
    layers = build_arch_layers(scan, [], [])
    assert any(l.id == "queue" for l in layers)


@_test("architecture: summary_text is non-empty")
def _():
    scan = _make_scan(frameworks=["FastAPI", "Pydantic"])
    layers = build_arch_layers(scan, [], [])
    text = build_summary_text(scan, layers, [], [])
    assert len(text) > 20
    assert "Python" in text


# ===========================================================================
# 6. Engine integration test (synthetic filesystem)
# ===========================================================================

from backend.analysis.engine import _run_analysis_sync, _collect_file_paths
from backend.ingestion.models import IngestionRecord, IngestionStatus


def _build_integration_record(tmp: str) -> IngestionRecord:
    """Build a minimal ready IngestionRecord pointing at a synthetic repo."""
    base = Path(tmp)

    # Create a minimal FastAPI-like repo
    (base / "main.py").write_text(
        "from fastapi import FastAPI\nimport uvicorn\n"
        "app = FastAPI()\n"
        "@app.get('/health')\ndef health(): return {'ok': True}\n"
        "@app.post('/users')\ndef create_user(): pass\n"
        "if __name__ == '__main__':\n    uvicorn.run(app)\n",
        encoding="utf-8",
    )
    (base / "README.md").write_text("# My App", encoding="utf-8")
    (base / "requirements.txt").write_text("fastapi\nuvicorn\npydantic\n", encoding="utf-8")
    tests = base / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_health(): pass\n", encoding="utf-8")

    # Build a scan result matching the filesystem
    from backend.ingestion.scanner import scan_repository
    scan = scan_repository(base)

    record = IngestionRecord(
        repo_id="integration_test",
        repo_url="https://github.com/test/repo",
        status=IngestionStatus.ready,
        work_dir=str(base),
        scan=scan,
    )
    return record


@_test("engine: _collect_file_paths flattens tree")
def _():
    tree = _make_tree({"src": ["a.py", "b.py"], "tests": ["test_a.py"]})
    # Add a root-level file
    tree.children.append(FileNode(name="README.md", path="README.md", type="file"))
    paths = _collect_file_paths(tree)
    assert "src/a.py" in paths
    assert "tests/test_a.py" in paths
    assert "README.md" in paths


@_test("engine: full analysis on synthetic FastAPI repo")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        record = _build_integration_record(tmp)
        result = _run_analysis_sync(record)

    assert result.repo_id == "integration_test"
    assert result.route_count >= 2
    assert any(r.path == "/health" for r in result.routes)
    assert any(r.path == "/users" for r in result.routes)
    assert any(e.file == "main.py" for e in result.entry_points)
    assert len(result.arch_layers) >= 2
    assert result.summary_text != ""


@_test("engine: analysis result serialises to valid JSON")
def _():
    with tempfile.TemporaryDirectory() as tmp:
        record = _build_integration_record(tmp)
        result = _run_analysis_sync(record)
    json_str = result.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["repo_id"] == "integration_test"
    assert isinstance(parsed["routes"], list)
    assert isinstance(parsed["arch_layers"], list)


# ===========================================================================
# 7. API route wiring
# ===========================================================================

from backend.main import app


@_test("wiring: GET /api/analysis/{repo_id} route is registered")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/analysis/{repo_id}" in routes, f"Routes: {sorted(routes)}"


@_test("wiring: all four analysis/ingestion routes present")
def _():
    routes = {r.path for r in app.routes}  # type: ignore[attr-defined]
    assert "/api/analyze"              in routes
    assert "/api/summary/{repo_id}"    in routes
    assert "/api/structure/{repo_id}"  in routes
    assert "/api/analysis/{repo_id}"   in routes


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    total  = len(_results)
    passed = sum(1 for _, ok, _ in _results if ok)

    print(f"\n{'='*60}")
    print(f"  RepoLens Task 5 - analysis layer validation")
    print(f"{'='*60}")
    for name, ok, err in _results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}]  {name}")
        if err:
            # Truncate long error messages
            msg = err[:200].replace("\n", " ")
            print(f"         >> {msg}")
    print(f"{'='*60}")
    print(f"  {passed}/{total} tests passed")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)
