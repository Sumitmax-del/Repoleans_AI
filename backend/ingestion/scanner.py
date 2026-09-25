"""
Repository file-system scanner.

Walks the cloned repository directory and produces:
  - A full FileNode tree (directories + files)
  - Language statistics (by file count)
  - Framework / tooling detection (filenames & content heuristics)
  - Dependency extraction from well-known manifest formats
  - A list of notable config / CI files
  - A list of "important" entry-point files

No third-party libraries required — pure stdlib.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from pathlib import Path
from typing import Optional

from backend.ingestion.models import FileNode, ScanResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Extension → language mapping
# ---------------------------------------------------------------------------

_EXT_TO_LANG: dict[str, str] = {
    # Python
    ".py":   "Python",  ".pyi":  "Python",
    # JavaScript / TypeScript
    ".js":   "JavaScript", ".mjs":  "JavaScript", ".cjs":  "JavaScript",
    ".jsx":  "JavaScript",
    ".ts":   "TypeScript", ".tsx":  "TypeScript", ".mts":  "TypeScript",
    # Web
    ".html": "HTML",    ".htm":  "HTML",
    ".css":  "CSS",     ".scss": "CSS",    ".sass": "CSS",   ".less": "CSS",
    # Rust
    ".rs":   "Rust",
    # Go
    ".go":   "Go",
    # Java / JVM
    ".java": "Java",    ".kt":   "Kotlin", ".kts": "Kotlin",
    ".scala":"Scala",   ".groovy":"Groovy",
    # C / C++
    ".c":    "C",       ".h":    "C",
    ".cpp":  "C++",     ".cc":   "C++",    ".cxx": "C++",
    ".hpp":  "C++",     ".hxx":  "C++",
    # C#
    ".cs":   "C#",
    # Ruby
    ".rb":   "Ruby",    ".rake": "Ruby",
    # PHP
    ".php":  "PHP",
    # Swift
    ".swift":"Swift",
    # Shell
    ".sh":   "Shell",   ".bash": "Shell",  ".zsh": "Shell",
    ".fish": "Shell",   ".ps1":  "PowerShell",
    # Config / markup
    ".toml": "TOML",    ".yaml": "YAML",   ".yml": "YAML",
    ".json": "JSON",    ".xml":  "XML",    ".ini": "INI",
    ".cfg":  "INI",     ".conf": "INI",    ".env": "INI",
    # Docs
    ".md":   "Markdown",".rst":  "reStructuredText", ".txt": "Text",
    # Data
    ".sql":  "SQL",     ".proto":"Protobuf",
    ".graphql":"GraphQL", ".gql":"GraphQL",
    # Infrastructure
    ".tf":   "Terraform", ".hcl": "HCL",
    ".dockerfile": "Dockerfile",
    # Elixir / Erlang
    ".ex":   "Elixir",  ".exs": "Elixir",  ".erl": "Erlang",
    # Clojure
    ".clj":  "Clojure", ".cljs": "ClojureScript",
    # Haskell
    ".hs":   "Haskell",
    # Lua
    ".lua":  "Lua",
    # Dart
    ".dart": "Dart",
}

# Filenames that override extension-based detection
_FILENAME_LANG: dict[str, str] = {
    "Dockerfile":         "Dockerfile",
    "Makefile":           "Makefile",
    "Jenkinsfile":        "Groovy",
    "Gemfile":            "Ruby",
    "Rakefile":           "Ruby",
    "Podfile":            "Ruby",
    "Cartfile":           "Swift",
    ".htaccess":          "Apache Config",
    "nginx.conf":         "Nginx Config",
}

# ---------------------------------------------------------------------------
# Framework / tooling detection
# ---------------------------------------------------------------------------

# File name → framework name(s)
_FILE_FRAMEWORKS: dict[str, list[str]] = {
    # Python
    "fastapi":            ["FastAPI"],
    "flask":              ["Flask"],
    "django":             ["Django"],
    "starlette":          ["Starlette"],
    "tornado":            ["Tornado"],
    "aiohttp":            ["aiohttp"],
    "celery":             ["Celery"],
    "sqlalchemy":         ["SQLAlchemy"],
    "alembic":            ["Alembic"],
    "pydantic":           ["Pydantic"],
    "pytest":             ["Pytest"],
    "unittest":           ["unittest"],
    # JS/TS
    "react":              ["React"],
    "vue":                ["Vue"],
    "angular":            ["Angular"],
    "svelte":             ["Svelte"],
    "next":               ["Next.js"],
    "nuxt":               ["Nuxt"],
    "express":            ["Express"],
    "fastify":            ["Fastify"],
    "nestjs":             ["NestJS"],
    "prisma":             ["Prisma"],
    "sequelize":          ["Sequelize"],
    "mongoose":           ["Mongoose"],
    "jest":               ["Jest"],
    "vitest":             ["Vitest"],
    "webpack":            ["Webpack"],
    "vite":               ["Vite"],
    "rollup":             ["Rollup"],
    "tailwind":           ["Tailwind CSS"],
    "redux":              ["Redux"],
    "zustand":            ["Zustand"],
    # Java
    "spring":             ["Spring"],
    "hibernate":          ["Hibernate"],
    "junit":              ["JUnit"],
    # Ruby
    "rails":              ["Rails"],
    "rspec":              ["RSpec"],
    # Go
    "gin":                ["Gin"],
    "echo":               ["Echo"],
    # Rust
    "actix":              ["Actix"],
    "axum":               ["Axum"],
    "tokio":              ["Tokio"],
    # Infrastructure
    "terraform":          ["Terraform"],
    "kubernetes":         ["Kubernetes"],
    "docker":             ["Docker"],
    "ansible":            ["Ansible"],
    "pulumi":             ["Pulumi"],
}

# Exact filenames that indicate specific frameworks / tools
_INDICATOR_FILES: dict[str, list[str]] = {
    "next.config.js":     ["Next.js"],
    "next.config.ts":     ["Next.js"],
    "nuxt.config.ts":     ["Nuxt"],
    "nuxt.config.js":     ["Nuxt"],
    "angular.json":       ["Angular"],
    "svelte.config.js":   ["Svelte"],
    "vite.config.ts":     ["Vite"],
    "vite.config.js":     ["Vite"],
    "tailwind.config.js": ["Tailwind CSS"],
    "tailwind.config.ts": ["Tailwind CSS"],
    "jest.config.js":     ["Jest"],
    "jest.config.ts":     ["Jest"],
    "vitest.config.ts":   ["Vitest"],
    "vitest.config.js":   ["Vitest"],
    "webpack.config.js":  ["Webpack"],
    "rollup.config.js":   ["Rollup"],
    "Dockerfile":         ["Docker"],
    "docker-compose.yml": ["Docker"],
    "docker-compose.yaml":["Docker"],
    "manage.py":          ["Django"],
    "wsgi.py":            ["Django"],   # could also be generic WSGI
    "asgi.py":            ["Django"],
    "alembic.ini":        ["Alembic"],
    "Gemfile":            ["Ruby"],
    "Rakefile":           ["Ruby"],
    "pubspec.yaml":       ["Flutter"],
    "mix.exs":            ["Elixir"],
    "go.mod":             ["Go modules"],
    "Cargo.toml":         ["Rust / Cargo"],
    "pom.xml":            ["Maven"],
    "build.gradle":       ["Gradle"],
    "build.gradle.kts":   ["Gradle"],
    ".terraform":         ["Terraform"],
    "Pulumi.yaml":        ["Pulumi"],
}

# Dep manifests we can parse for package names
_DEP_MANIFESTS = {
    "requirements.txt", "requirements-dev.txt", "requirements-test.txt",
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "Pipfile.lock",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.toml", "go.mod", "Gemfile", "composer.json",
    "pom.xml", "build.gradle",
}

# Config / CI files worth surfacing
_CONFIG_FILE_NAMES = {
    "pyproject.toml", "setup.cfg", "setup.py", ".flake8", "mypy.ini",
    "tox.ini", ".pre-commit-config.yaml", "Makefile",
    ".github/workflows", ".gitlab-ci.yml", ".circleci/config.yml",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".prettierrc",
    "tsconfig.json", "jsconfig.json", ".babelrc", "babel.config.js",
    "codecov.yml", ".coveragerc",
}

# Directories to skip entirely during scan
_SKIP_DIRS = {
    ".git", ".hg", ".svn",
    "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox",
    "build", "dist", "out", "target",
    ".idea", ".vscode", ".vs",
    "vendor", "third_party", "Pods",
    ".next", ".nuxt", ".turbo",
    "coverage", ".nyc_output",
    ".eggs", "*.egg-info",
}

# Max files to include in the tree (avoids enormous trees for huge repos)
_MAX_TREE_FILES = 2000

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_repository(clone_dir: Path) -> ScanResult:
    """
    Walk *clone_dir* and return a :class:`ScanResult`.

    Parameters
    ----------
    clone_dir:
        Absolute path to the cloned (and already de-git-ted) repository root.
    """
    lang_counter: Counter[str] = Counter()
    all_files: list[Path] = []
    dir_count = 0
    total_bytes = 0
    framework_set: set[str] = set()
    config_files: list[str] = []
    important_files: list[str] = []
    dep_data: dict[str, list[str]] = {}

    # ── Walk file system ───────────────────────────────────────────────────
    for root, dirs, files in os.walk(clone_dir):
        root_path = Path(root)
        rel_root  = root_path.relative_to(clone_dir)

        # Prune unwanted directories in-place
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS
            and not d.endswith(".egg-info")
            and not d.startswith(".")
            or d in {".github", ".circleci"}   # allow useful dot-dirs
        ]

        dir_count += len(dirs)

        for fname in files:
            fpath = root_path / fname
            rel   = (rel_root / fname).as_posix()

            try:
                size = fpath.stat().st_size
            except OSError:
                continue

            total_bytes += size
            all_files.append(fpath)

            # Language detection
            lang = _detect_language(fname)
            if lang:
                lang_counter[lang] += 1

            # Framework detection via exact filename
            if fname in _INDICATOR_FILES:
                framework_set.update(_INDICATOR_FILES[fname])

            # Config files
            if fname in _CONFIG_FILE_NAMES or rel in _CONFIG_FILE_NAMES:
                config_files.append(rel)

            # Important files heuristic
            if _is_important(fname, rel):
                important_files.append(rel)

            # Dependency extraction
            if fname in _DEP_MANIFESTS:
                deps = _extract_deps(fpath, fname)
                if deps:
                    dep_data[rel] = deps
                    # Framework detection from dependency names
                    for pkg in deps:
                        for keyword, fws in _FILE_FRAMEWORKS.items():
                            if keyword in pkg.lower():
                                framework_set.update(fws)

    # ── Framework detection from directory / file names ───────────────────
    for fpath in all_files[:_MAX_TREE_FILES]:
        name_lower = fpath.name.lower()
        for keyword, fws in _FILE_FRAMEWORKS.items():
            if keyword in name_lower:
                framework_set.update(fws)

    # ── Build tree ────────────────────────────────────────────────────────
    tree = _build_tree(clone_dir, clone_dir)

    # ── Order languages by frequency ──────────────────────────────────────
    languages = [lang for lang, _ in lang_counter.most_common()]
    primary   = languages[0] if languages else "Unknown"

    # Deduplicate preserving order
    seen: set[str] = set()
    frameworks: list[str] = []
    for fw in sorted(framework_set):
        if fw not in seen:
            seen.add(fw)
            frameworks.append(fw)

    return ScanResult(
        file_count=len(all_files),
        directory_count=dir_count,
        total_size_bytes=total_bytes,
        languages=languages,
        primary_language=primary,
        frameworks=frameworks,
        config_files=sorted(set(config_files)),
        important_files=sorted(set(important_files)),
        dependencies=dep_data,
        file_tree=tree,
    )


# ---------------------------------------------------------------------------
# Language detection helpers
# ---------------------------------------------------------------------------


def _detect_language(filename: str) -> Optional[str]:
    # Exact filename match first
    if filename in _FILENAME_LANG:
        return _FILENAME_LANG[filename]
    ext = Path(filename).suffix.lower()
    return _EXT_TO_LANG.get(ext)


# ---------------------------------------------------------------------------
# File importance heuristic
# ---------------------------------------------------------------------------

_IMPORTANT_NAMES = {
    "readme.md", "readme.rst", "readme.txt", "readme",
    "main.py", "app.py", "server.py", "wsgi.py", "asgi.py",
    "index.ts", "index.js", "index.tsx", "app.ts", "app.js",
    "main.ts", "main.js", "main.go", "main.rs", "main.c",
    "manage.py",                                    # Django
    "pyproject.toml", "setup.py", "setup.cfg",      # Python packaging
    "package.json",                                 # Node packaging
    "cargo.toml",                                   # Rust
    "go.mod",                                       # Go
    "pom.xml", "build.gradle",                      # Java
    "gemfile",                                      # Ruby
}


def _is_important(fname: str, rel: str) -> bool:
    """Return True if this file should be surfaced as 'important'."""
    if fname.lower() in _IMPORTANT_NAMES:
        return True
    # Top-level only for most heuristics
    if "/" not in rel:
        if fname.endswith((".py", ".ts", ".js", ".go", ".rs")) and "test" not in fname.lower():
            return True
    return False


# ---------------------------------------------------------------------------
# Dependency extraction
# ---------------------------------------------------------------------------


def _extract_deps(path: Path, filename: str) -> list[str]:
    """Best-effort extraction of package names from a manifest file."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    fname = filename.lower()

    if fname == "requirements.txt" or fname.startswith("requirements"):
        return _parse_requirements_txt(text)

    if fname == "pyproject.toml":
        return _parse_pyproject_toml(text)

    if fname in ("package.json",):
        return _parse_package_json(text)

    if fname == "cargo.toml":
        return _parse_cargo_toml(text)

    if fname == "go.mod":
        return _parse_go_mod(text)

    if fname == "gemfile":
        return _parse_gemfile(text)

    return []


_REQ_LINE = re.compile(r"^([A-Za-z0-9_\-\.]+)")


def _parse_requirements_txt(text: str) -> list[str]:
    deps: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-", "git+", "http")):
            continue
        m = _REQ_LINE.match(line)
        if m:
            deps.append(m.group(1))
    return deps


def _parse_pyproject_toml(text: str) -> list[str]:
    """Extract dependencies from pyproject.toml without a TOML parser."""
    deps: list[str] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        # Enter dependency sections
        if stripped in ("[project]", "[tool.poetry.dependencies]",
                        "[tool.pdm.dev-dependencies]", "[build-system]"):
            in_deps = "dependencies" in stripped or stripped == "[project]"
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_deps = False
            continue
        if in_deps or "dependencies" in stripped:
            m = re.findall(r'"([A-Za-z0-9_\-\.]+)[>=<!\^~\s"\[]', stripped)
            deps.extend(m)
    return list(dict.fromkeys(deps))  # deduplicate preserving order


def _parse_package_json(text: str) -> list[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    deps: list[str] = []
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        deps.extend(data.get(section, {}).keys())
    return list(dict.fromkeys(deps))


def _parse_cargo_toml(text: str) -> list[str]:
    deps: list[str] = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in ("[dependencies]", "[dev-dependencies]", "[build-dependencies]"):
            in_deps = True
            continue
        if stripped.startswith("["):
            in_deps = False
            continue
        if in_deps:
            m = re.match(r'^([A-Za-z0-9_\-]+)\s*[=\[]', stripped)
            if m:
                deps.append(m.group(1))
    return deps


def _parse_go_mod(text: str) -> list[str]:
    deps: list[str] = []
    in_require = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require = True
            continue
        if in_require:
            if stripped == ")":
                in_require = False
                continue
            parts = stripped.split()
            if parts:
                # module path, e.g. "github.com/gin-gonic/gin v1.9.0"
                deps.append(parts[0])
        elif stripped.startswith("require ") and not stripped.endswith("("):
            parts = stripped[8:].split()
            if parts:
                deps.append(parts[0])
    return deps


def _parse_gemfile(text: str) -> list[str]:
    deps: list[str] = []
    for line in text.splitlines():
        m = re.match(r"""^\s*gem\s+['"]([A-Za-z0-9_\-\.]+)['"]""", line)
        if m:
            deps.append(m.group(1))
    return deps


# ---------------------------------------------------------------------------
# File tree builder
# ---------------------------------------------------------------------------


def _build_tree(path: Path, root: Path, depth: int = 0) -> FileNode:
    """Recursively build a FileNode tree, respecting skip rules."""
    rel = path.relative_to(root).as_posix() if path != root else ""

    if path.is_file():
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        return FileNode(
            name=path.name,
            path=rel,
            type="file",
            language=_detect_language(path.name),
            size_bytes=size,
        )

    # Directory
    children: list[FileNode] = []
    try:
        entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        entries = []

    for entry in entries:
        # Skip unwanted directories
        if entry.is_dir():
            if (
                entry.name in _SKIP_DIRS
                or entry.name.endswith(".egg-info")
                or (entry.name.startswith(".") and entry.name not in {".github", ".circleci"})
            ):
                continue
        children.append(_build_tree(entry, root, depth + 1))

    return FileNode(
        name=path.name if path != root else path.name,
        path=rel,
        type="directory",
        children=children,
    )
