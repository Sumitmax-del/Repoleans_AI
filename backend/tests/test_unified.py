"""
Task 9 — Unified server validation.
Short, terminating. No network calls, no running server.
"""
import sys
from pathlib import Path

# Project root on sys.path
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_pass = 0
_fail = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global _pass, _fail
    if ok:
        print(f"  [PASS]  {name}")
        _pass += 1
    else:
        print(f"  [FAIL]  {name}" + (f"\n         | {detail}" if detail else ""))
        _fail += 1


print("\n" + "=" * 58)
print("  RepoLens Task 9 - Unified Server Validation")
print("=" * 58)

# ── 1. aiofiles ──────────────────────────────────────────────────────────────
try:
    import aiofiles  # noqa: F401
    check("aiofiles is installed", True)
except ImportError as e:
    check("aiofiles is installed", False, str(e))

# ── 2. main.py imports cleanly ───────────────────────────────────────────────
try:
    from backend.main import app, _DIST, _INDEX
    check("backend.main imports without error", True)
except Exception as e:
    check("backend.main imports without error", False, str(e))
    sys.exit(1)

# ── 3. API routes via OpenAPI schema (most reliable method) ──────────────────
try:
    openapi_paths = set(app.openapi()["paths"].keys())
    for path in [
        "/health",
        "/api/analyze",
        "/api/summary/{repo_id}",
        "/api/structure/{repo_id}",
        "/api/analysis/{repo_id}",
        "/api/chat",
    ]:
        check(f"{path} route registered", path in openapi_paths)
except Exception as e:
    check("OpenAPI path inspection", False, str(e))

# ── 4. SPA fallback catch-all registered ─────────────────────────────────────
spa_route = any(
    getattr(r, "path", "") == "/{full_path:path}"
    for r in app.routes
)
check("SPA fallback /{full_path:path} registered", spa_route)

# ── 5. /assets StaticFiles mount registered ──────────────────────────────────
from starlette.routing import Mount  # noqa: E402
asset_mount = any(
    isinstance(r, Mount) and getattr(r, "path", "") == "/assets"
    for r in app.routes
)
check("/assets StaticFiles mount registered", asset_mount)

# ── 6. dist/index.html exists ────────────────────────────────────────────────
dist  = _ROOT / "frontend" / "dist"
index = dist / "index.html"
check("frontend/dist/index.html exists", index.exists())
if index.exists():
    content = index.read_text(encoding="utf-8")
    check('index.html contains <div id="root">', '<div id="root">' in content)

# ── 7. dist/assets/ JS bundle present ───────────────────────────────────────
assets_dir = dist / "assets"
js_files = list(assets_dir.glob("*.js")) if assets_dir.is_dir() else []
check("frontend/dist/assets/ JS bundle present", len(js_files) > 0)

# ── 8. _DIST and _INDEX paths from main.py point to correct locations ────────
check("main.py _DIST resolves to frontend/dist",        _DIST == dist)
check("main.py _INDEX resolves to frontend/dist/index.html", _INDEX == index)

# ── 9. Backend tests still green ────────────────────────────────────────────
# Import the already-executed result lists from each test module.
try:
    from backend.tests.test_rag  import _results as rag_results
    from backend.tests.test_chat import _results as chat_results
    rag_ok  = all(ok for _, ok, _ in rag_results)
    chat_ok = all(ok for _, ok, _ in chat_results)
    check(f"RAG tests  ({len(rag_results)} tests)",  rag_ok,  "some tests failed")
    check(f"Chat tests ({len(chat_results)} tests)", chat_ok, "some tests failed")
except Exception as e:
    check("Backend test import", False, str(e))

print("=" * 58)
print(f"  {_pass}/{_pass + _fail} checks passed")
print("=" * 58 + "\n")

sys.exit(0 if _fail == 0 else 1)
