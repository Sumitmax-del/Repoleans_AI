"""
API / route definition detector.

Scans source files for framework-specific route registration patterns and
returns a list of RouteDefinition objects.  All detection is purely static
(regex over source text) — no imports or execution.

Supported frameworks
--------------------
Python  : FastAPI, Flask, Django (urls.py), Starlette, aiohttp
Node.js : Express, Fastify, Koa, NestJS (decorators), Hono
Java    : Spring MVC (@GetMapping etc.)
Ruby    : Rails routes.rb
Go      : net/http HandleFunc, Gin, Echo, Chi
Rust    : Actix-web, Axum
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from backend.ingestion.models import RouteDefinition

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-language pattern tables
# Each entry: (compiled regex, http_method, framework_name)
# Group 1 must capture the path string; group 2 (optional) the handler name.
# ---------------------------------------------------------------------------

# Files larger than this are skipped (avoids reading minified JS bundles etc.)
_MAX_FILE_BYTES = 256 * 1024


# ── Python ──────────────────────────────────────────────────────────────────

# FastAPI / Starlette decorators:  @app.get("/path")  @router.post("/path")
_FASTAPI_RE = re.compile(
    r"""@\w+\.(get|post|put|delete|patch|head|options|websocket)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Flask:  @app.route("/path", methods=["GET"])  or  @bp.get("/path")
_FLASK_ROUTE_RE = re.compile(
    r"""@\w+\.route\s*\(\s*["']([^"']+)["'][^)]*methods\s*=\s*\[([^\]]*)\]""",
    re.IGNORECASE,
)
_FLASK_SHORTHAND_RE = re.compile(
    r"""@\w+\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Django urls.py:  path("route/", view_func)  or  re_path(r"^route/$", view)
_DJANGO_PATH_RE = re.compile(
    r"""(?:path|re_path|url)\s*\(\s*["'r]?([^"',\s]+)["']?\s*,\s*(\w+)""",
    re.IGNORECASE,
)

# aiohttp:  app.router.add_get("/path", handler)
_AIOHTTP_RE = re.compile(
    r"""\.add_(get|post|put|delete|patch|route)\s*\(\s*["']([^"']+)["']\s*,\s*(\w+)""",
    re.IGNORECASE,
)


# ── JavaScript / TypeScript ─────────────────────────────────────────────────

# Express / Koa / Hono:  app.get("/path", ...)  router.post("/path", ...)
_EXPRESS_RE = re.compile(
    r"""(?:app|router|server)\.(get|post|put|delete|patch|all|use)\s*\(\s*["'`]([^"'`]+)["'`]""",
    re.IGNORECASE,
)

# Fastify:  fastify.get("/path", ...)
_FASTIFY_RE = re.compile(
    r"""(?:fastify|server)\.(get|post|put|delete|patch|head|options)\s*\(\s*["'`]([^"'`]+)["'`]""",
    re.IGNORECASE,
)

# NestJS controller decorators:  @Get("/path")  @Post()
_NESTJS_RE = re.compile(
    r"""@(Get|Post|Put|Delete|Patch|Head|Options|All)\s*\(\s*(?:["'`]([^"'`]*)["'`])?\s*\)""",
    re.IGNORECASE,
)


# ── Java / Spring ───────────────────────────────────────────────────────────

# Spring:  @GetMapping("/path")  @RequestMapping(value="/path", method=GET)
_SPRING_MAPPING_RE = re.compile(
    r"""@(GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?["']([^"']+)["']""",
    re.IGNORECASE,
)


# ── Ruby on Rails ───────────────────────────────────────────────────────────

# routes.rb:  get "/path", to: "controller#action"
_RAILS_RE = re.compile(
    r"""(?:^|\s)(get|post|put|patch|delete|resources?|namespace)\s+["']([^"']+)["']""",
    re.IGNORECASE | re.MULTILINE,
)


# ── Go ──────────────────────────────────────────────────────────────────────

# net/http:  http.HandleFunc("/path", handler)
_GO_HTTP_RE = re.compile(
    r"""http\.HandleFunc\s*\(\s*["']([^"']+)["']\s*,\s*(\w+)""",
)

# Gin:  r.GET("/path", handler)
_GIN_RE = re.compile(
    r"""\.(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|Any)\s*\(\s*["']([^"']+)["']\s*,\s*(\w+)""",
)

# Echo:  e.GET("/path", handler)
_ECHO_RE = re.compile(
    r"""e\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s*\(\s*["']([^"']+)["']\s*,\s*(\w+)""",
    re.IGNORECASE,
)


# ── Rust / Actix / Axum ─────────────────────────────────────────────────────

# Actix:  #[get("/path")]  web::get().to(handler)
_ACTIX_ATTR_RE = re.compile(
    r"""#\[(get|post|put|delete|patch|head|options)\s*\(\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# Axum:  .route("/path", get(handler))
_AXUM_RE = re.compile(
    r"""\.route\s*\(\s*["']([^"']+)["']\s*,\s*(get|post|put|delete|patch)\s*\((\w+)\)""",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# File-type routing tables
# Maps file extension or name pattern → list of (regex, extract_fn)
# extract_fn(match) → (method, path, handler)
# ---------------------------------------------------------------------------

def _py_fastapi(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), ""

def _py_flask_route(m: re.Match) -> tuple[str, str, str]:
    methods_raw = m.group(2)
    methods = re.findall(r"['\"](\w+)['\"]", methods_raw)
    return ",".join(methods).upper() or "GET", m.group(1), ""

def _py_flask_short(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), ""

def _py_django(m: re.Match) -> tuple[str, str, str]:
    return "any", m.group(1), m.group(2)

def _py_aiohttp(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), m.group(3)

def _js_express(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), ""

def _js_fastify(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), ""

def _js_nestjs(m: re.Match) -> tuple[str, str, str]:
    path = m.group(2) or "/"
    return m.group(1).upper(), path if path.startswith("/") else f"/{path}", ""

def _java_spring(m: re.Match) -> tuple[str, str, str]:
    verb_map = {
        "getmapping": "GET", "postmapping": "POST", "putmapping": "PUT",
        "deletemapping": "DELETE", "patchmapping": "PATCH",
        "requestmapping": "any",
    }
    return verb_map.get(m.group(1).lower(), "any"), m.group(2), ""

def _ruby_rails(m: re.Match) -> tuple[str, str, str]:
    verb = m.group(1).lower()
    if verb in ("resources", "resource", "namespace"):
        return "any", m.group(2), ""
    return verb.upper(), m.group(2), ""

def _go_http(m: re.Match) -> tuple[str, str, str]:
    return "any", m.group(1), m.group(2)

def _go_gin(m: re.Match) -> tuple[str, str, str]:
    # method is captured inside the pattern name .GET
    verb = re.search(r"\.(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS|Any)", m.group(0))
    return (verb.group(1).upper() if verb else "any"), m.group(1), m.group(2)

def _go_echo(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), m.group(3)

def _rust_actix(m: re.Match) -> tuple[str, str, str]:
    return m.group(1).upper(), m.group(2), ""

def _rust_axum(m: re.Match) -> tuple[str, str, str]:
    return m.group(2).upper(), m.group(1), m.group(3)


# Ordered list of (extension_set, patterns_list)
# patterns_list: list of (regex, framework_name, extract_fn)
_PATTERNS: list[tuple[frozenset[str], list[tuple[re.Pattern, str, object]]]] = [
    (
        frozenset({".py"}),
        [
            (_FASTAPI_RE,        "FastAPI",   _py_fastapi),
            (_FLASK_ROUTE_RE,    "Flask",     _py_flask_route),
            (_FLASK_SHORTHAND_RE,"Flask",     _py_flask_short),
            (_DJANGO_PATH_RE,    "Django",    _py_django),
            (_AIOHTTP_RE,        "aiohttp",   _py_aiohttp),
        ],
    ),
    (
        frozenset({".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}),
        [
            (_EXPRESS_RE,  "Express",  _js_express),
            (_FASTIFY_RE,  "Fastify",  _js_fastify),
            (_NESTJS_RE,   "NestJS",   _js_nestjs),
        ],
    ),
    (
        frozenset({".java", ".kt"}),
        [
            (_SPRING_MAPPING_RE, "Spring", _java_spring),
        ],
    ),
    (
        frozenset({".rb"}),
        [
            (_RAILS_RE, "Rails", _ruby_rails),
        ],
    ),
    (
        frozenset({".go"}),
        [
            (_GO_HTTP_RE,  "net/http", _go_http),
            (_GIN_RE,      "Gin",      _go_gin),
            (_ECHO_RE,     "Echo",     _go_echo),
        ],
    ),
    (
        frozenset({".rs"}),
        [
            (_ACTIX_ATTR_RE, "Actix",  _rust_actix),
            (_AXUM_RE,       "Axum",   _rust_axum),
        ],
    ),
]

# Build a fast lookup: extension → patterns
_EXT_PATTERNS: dict[str, list[tuple[re.Pattern, str, object]]] = {}
for _exts, _pats in _PATTERNS:
    for _ext in _exts:
        _EXT_PATTERNS.setdefault(_ext, []).extend(_pats)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_routes(clone_dir: Path, file_paths: list[str]) -> list[RouteDefinition]:
    """
    Scan *file_paths* (repo-relative) under *clone_dir* and return every
    detected route definition.

    Parameters
    ----------
    clone_dir:
        Absolute path to the cloned repository root.
    file_paths:
        Repo-relative POSIX paths to scan (typically the full file list
        from ScanResult, but the caller may pre-filter if desired).
    """
    routes: list[RouteDefinition] = []
    seen: set[tuple[str, str, str]] = set()  # deduplicate (file, method, path)

    for rel_path in file_paths:
        ext = Path(rel_path).suffix.lower()
        patterns = _EXT_PATTERNS.get(ext)
        if not patterns:
            continue

        abs_path = clone_dir / rel_path
        if not abs_path.exists():
            continue

        try:
            size = abs_path.stat().st_size
            if size > _MAX_FILE_BYTES:
                continue
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        lines = text.splitlines()

        for pattern, framework, extract_fn in patterns:
            for m in pattern.finditer(text):
                try:
                    method, path, handler = extract_fn(m)  # type: ignore[operator]
                except Exception:
                    continue

                # Normalise
                path = path.strip()
                if not path:
                    path = "/"

                # Deduplicate
                key = (rel_path, method.lower(), path)
                if key in seen:
                    continue
                seen.add(key)

                # Calculate 1-based line number from match start
                line_no = text[: m.start()].count("\n") + 1

                routes.append(
                    RouteDefinition(
                        method=method,
                        path=path,
                        file=rel_path,
                        line=line_no,
                        handler=handler,
                        framework=framework,
                    )
                )

    # Sort by file, then line number for stable output
    routes.sort(key=lambda r: (r.file, r.line))
    return routes
