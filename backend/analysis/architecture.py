"""
Architecture flow layer builder.

Converts the already-detected frameworks, entry points, and route data into
a structured list of ArchLayer objects suitable for the frontend flow diagram
and future RAG context.

The output is deterministic and purely data-driven — no LLM involved.

Design
------
Layers are built from a priority-ordered set of "layer rules".  Each rule
describes a class of technology and which detected frameworks trigger it.
The rule also specifies which files are most relevant (surfaced as ArchNode
files) and what the natural layer ordering is in a typical request pipeline.

Request flow order (left → right in the frontend diagram)
----------------------------------------------------------
  client → [load balancer] → entry → app → routing → middleware → validation
  → [auth] → [database] → [cache] → [queue] → [external]
"""

from __future__ import annotations

from pathlib import Path

from backend.ingestion.models import (
    AnalysisResult, ArchLayer, ArchNode, EntryPoint,
    RouteDefinition, ScanResult,
)

# ---------------------------------------------------------------------------
# Layer rule definitions
# ---------------------------------------------------------------------------
# Each rule: dict with keys:
#   id        – stable slug used as ArchLayer.id
#   label     – human-readable label
#   color     – one of the palette names the frontend understands
#   triggers  – any of these framework names (lowercase) activate the layer
#   node_defs – list of (name, description, file_pattern) tuples
#               file_pattern is matched against important_files / routes
#
# Layers are emitted in the order they appear in this list.
# ---------------------------------------------------------------------------

_LAYER_RULES: list[dict] = [
    # ── Entry point ────────────────────────────────────────────────────────
    {
        "id": "entry",
        "label": "Entry Point",
        "color": "blue",
        "triggers": {
            "uvicorn", "gunicorn", "hypercorn", "daphne",  # Python ASGI servers
            "node", "bun", "deno",                          # JS runtimes
        },
        "dep_triggers": {"uvicorn", "gunicorn", "hypercorn"},
        "always": True,   # always emit this layer
        "node_defs": [
            ("ASGI/HTTP Server", "Receives HTTP requests and forwards to the app", "server"),
        ],
    },
    # ── Application root ───────────────────────────────────────────────────
    {
        "id": "app",
        "label": "Application",
        "color": "sky",
        "triggers": {
            "fastapi", "flask", "django", "starlette", "aiohttp", "tornado",
            "express", "fastify", "koa", "nestjs", "hono",
            "spring", "gin", "echo", "axum", "actix",
            "rails",
        },
        "always": True,
        "node_defs": [
            ("App Instance", "Root application object; mounts routers and middleware", "app"),
        ],
    },
    # ── Routing ────────────────────────────────────────────────────────────
    {
        "id": "routing",
        "label": "Routing",
        "color": "purple",
        "triggers": {
            "fastapi", "flask", "django", "express", "fastify",
            "spring", "gin", "echo", "axum", "rails",
        },
        "always": False,
        "node_defs": [
            ("Router / URLConf", "Maps URL patterns to handler functions", "rout"),
            ("Path Parameters", "Typed path / query parameter declarations", "param"),
        ],
    },
    # ── Middleware ─────────────────────────────────────────────────────────
    {
        "id": "middleware",
        "label": "Middleware",
        "color": "orange",
        "triggers": {
            "cors", "starlette", "fastapi", "express", "django",
            "koa", "gin", "actix",
        },
        "dep_triggers": {"starlette"},
        "always": False,
        "node_defs": [
            ("CORS", "Cross-origin request handling", "cors"),
            ("Auth Middleware", "JWT / session validation layer", "auth"),
            ("Logging", "Request / response logging", "log"),
        ],
    },
    # ── Validation ─────────────────────────────────────────────────────────
    {
        "id": "validation",
        "label": "Validation",
        "color": "green",
        "triggers": {"pydantic", "zod", "joi", "yup", "marshmallow", "cerberus"},
        "dep_triggers": {"pydantic", "zod", "joi"},
        "always": False,
        "node_defs": [
            ("Schema Validation", "Request body and parameter validation", "valid"),
            ("Data Models", "Typed request / response schemas", "model"),
        ],
    },
    # ── Authentication ─────────────────────────────────────────────────────
    {
        "id": "auth",
        "label": "Authentication",
        "color": "red",
        "triggers": {
            "oauth2", "jwt", "passport", "authlib", "casbin",
            "django-allauth", "python-jose", "pyjwt",
        },
        "dep_triggers": {
            "python-jose", "pyjwt", "authlib", "passport",
            "jsonwebtoken", "bcrypt",
        },
        "always": False,
        "node_defs": [
            ("Auth Handler", "Verifies identity (JWT / OAuth2 / sessions)", "auth"),
            ("Permissions", "Role-based access control", "permiss"),
        ],
    },
    # ── Database / ORM ─────────────────────────────────────────────────────
    {
        "id": "database",
        "label": "Database",
        "color": "cyan",
        "triggers": {
            "sqlalchemy", "alembic", "django orm",
            "prisma", "sequelize", "mongoose", "typeorm",
            "hibernate", "gorm", "ecto",
        },
        "dep_triggers": {
            "sqlalchemy", "databases", "asyncpg", "psycopg2",
            "pymysql", "motor", "mongoose", "prisma", "gorm",
        },
        "always": False,
        "node_defs": [
            ("ORM / Query Builder", "Manages database models and queries", "model"),
            ("Migrations", "Schema versioning and migration scripts", "migrat"),
        ],
    },
    # ── Cache ──────────────────────────────────────────────────────────────
    {
        "id": "cache",
        "label": "Cache",
        "color": "gray",
        "triggers": {"redis", "memcached", "valkey"},
        "dep_triggers": {"redis", "aioredis", "redis-py", "ioredis"},
        "always": False,
        "node_defs": [
            ("Cache Store", "In-memory key/value cache (Redis / Memcached)", "cache"),
        ],
    },
    # ── Message queue ──────────────────────────────────────────────────────
    {
        "id": "queue",
        "label": "Task Queue",
        "color": "gray",
        "triggers": {"celery", "rq", "dramatiq", "bull", "bullmq", "sidekiq"},
        "dep_triggers": {"celery", "rq", "dramatiq", "bull", "bullmq"},
        "always": False,
        "node_defs": [
            ("Task Worker", "Processes background jobs asynchronously", "task"),
            ("Message Broker", "Transports tasks between producers and workers", "broker"),
        ],
    },
    # ── Testing ────────────────────────────────────────────────────────────
    {
        "id": "testing",
        "label": "Testing",
        "color": "green",
        "triggers": {"pytest", "jest", "vitest", "unittest", "rspec", "mocha"},
        "dep_triggers": {"pytest", "jest", "vitest", "mocha", "jasmine"},
        "always": False,
        "node_defs": [
            ("Test Runner", "Executes the automated test suite", "test"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_arch_layers(
    scan: ScanResult,
    entry_points: list[EntryPoint],
    routes: list[RouteDefinition],
) -> list[ArchLayer]:
    """
    Build the architecture flow layer list from the static analysis results.

    Parameters
    ----------
    scan:
        The ScanResult produced by the file-system scanner.
    entry_points:
        Classified entry points.
    routes:
        Detected route definitions.

    Returns
    -------
    list[ArchLayer]
        Ordered layers suitable for the frontend flow diagram.
    """
    # Normalise for matching
    fw_lower   = {f.lower() for f in scan.frameworks}
    dep_lower: set[str] = set()
    for deps in scan.dependencies.values():
        for d in deps:
            dep_lower.add(d.lower())

    layers: list[ArchLayer] = []

    for rule in _LAYER_RULES:
        if not _should_emit(rule, fw_lower, dep_lower):
            continue

        nodes = _build_nodes(rule, scan, entry_points, routes)
        if not nodes:
            # Always include the rule's first node_def as a placeholder
            name, desc, _ = rule["node_defs"][0]
            nodes = [ArchNode(name=name, file="", description=desc)]

        layers.append(
            ArchLayer(id=rule["id"], label=rule["label"], color=rule["color"], nodes=nodes)
        )

    return layers


def build_summary_text(
    scan: ScanResult,
    layers: list[ArchLayer],
    routes: list[RouteDefinition],
    entry_points: list[EntryPoint],
) -> str:
    """
    Generate a plain-English architecture summary paragraph.
    Purely deterministic — no LLM.
    """
    lang = scan.primary_language
    fw   = ", ".join(scan.frameworks[:3]) if scan.frameworks else "no specific frameworks"
    files = scan.file_count
    route_count = len(routes)
    ep_count = len([e for e in entry_points if e.kind == "web_server"])
    layer_labels = [l.label for l in layers]

    parts: list[str] = []

    parts.append(
        f"This repository contains {files:,} files written primarily in {lang}"
        + (f" using {fw}." if fw else ".")
    )

    if ep_count:
        server_files = ", ".join(
            e.file for e in entry_points if e.kind == "web_server"
        )[:120]
        parts.append(
            f"The application server is started from {server_files}."
        )

    if route_count:
        frameworks_used = sorted({r.framework for r in routes if r.framework})
        fw_str = " and ".join(frameworks_used) if frameworks_used else "the detected framework"
        parts.append(
            f"{route_count} API route{'s' if route_count != 1 else ''} "
            f"{'were' if route_count != 1 else 'was'} detected, "
            f"registered via {fw_str}."
        )

    if layer_labels:
        parts.append(
            f"The detected architecture layers are: {', '.join(layer_labels)}."
        )

    if scan.dependencies:
        total_deps = sum(len(v) for v in scan.dependencies.values())
        parts.append(
            f"Dependency manifests list {total_deps} package reference"
            f"{'s' if total_deps != 1 else ''}."
        )

    return "  ".join(parts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_emit(rule: dict, fw_lower: set[str], dep_lower: set[str]) -> bool:
    """Return True if this layer should be included given the detected stack."""
    if rule.get("always"):
        return True
    triggers: set[str] = rule.get("triggers", set())
    dep_triggers: set[str] = rule.get("dep_triggers", set())
    return bool(triggers & fw_lower) or bool(dep_triggers & dep_lower)


def _build_nodes(
    rule: dict,
    scan: ScanResult,
    entry_points: list[EntryPoint],
    routes: list[RouteDefinition],
) -> list[ArchNode]:
    """Build ArchNode list for a layer by matching node_defs to known files."""
    nodes: list[ArchNode] = []

    for name, description, file_hint in rule["node_defs"]:
        # Find the most relevant file for this node
        best_file = _find_best_file(
            file_hint, scan.important_files, routes, entry_points
        )
        nodes.append(ArchNode(name=name, file=best_file, description=description))

    return nodes


def _find_best_file(
    hint: str,
    important_files: list[str],
    routes: list[RouteDefinition],
    entry_points: list[EntryPoint],
) -> str:
    """Return the most relevant repo-relative file path for a hint string."""
    hint_l = hint.lower()

    # Check important files first
    for f in important_files:
        if hint_l in f.lower():
            return f

    # Check route source files
    for r in routes:
        if hint_l in r.file.lower():
            return r.file

    # Check entry-point files
    for ep in entry_points:
        if hint_l in ep.file.lower():
            return ep.file

    return ""
