"""
Source directory role classifier.

Walks the top two levels of the repository tree and assigns each directory
a functional role (source, tests, docs, config, scripts, assets, infra).

Roles
-----
source   — primary source code
tests    — automated tests
docs     — documentation
config   — configuration / build files
scripts  — shell/utility scripts
assets   — static assets (images, CSS, fonts)
infra    — infrastructure-as-code (Terraform, Kubernetes, Ansible)
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from backend.ingestion.models import FileNode, SourceDirectory

# ---------------------------------------------------------------------------
# Name-based rules (applied to the directory name, lowercased)
# ---------------------------------------------------------------------------

_NAME_ROLES: dict[str, str] = {
    # Tests
    "test":       "tests",  "tests":      "tests",
    "spec":       "tests",  "specs":      "tests",
    "__tests__":  "tests",  "e2e":        "tests",
    "integration_tests": "tests",
    # Documentation
    "docs":       "docs",   "doc":        "docs",
    "documentation": "docs","wiki":       "docs",
    # Scripts / tools
    "scripts":    "scripts","script":     "scripts",
    "tools":      "scripts","bin":        "scripts",
    "util":       "scripts","utils":      "scripts",
    "helpers":    "scripts",
    # Assets
    "assets":     "assets", "static":     "assets",
    "public":     "assets", "resources":  "assets",
    "images":     "assets", "fonts":      "assets",
    "media":      "assets",
    # Infrastructure
    "infra":      "infra",  "infrastructure": "infra",
    "terraform":  "infra",  "k8s":        "infra",
    "kubernetes": "infra",  "helm":       "infra",
    "ansible":    "infra",  "deploy":     "infra",
    "deployment": "infra",  "devops":     "infra",
    "ci":         "config", "cd":         "config",
    # Config
    "config":     "config", "configs":    "config",
    "conf":       "config", "settings":   "config",
    "env":        "config",
    # Source (explicit)
    "src":        "source", "source":     "source",
    "lib":        "source", "libs":       "source",
    "app":        "source", "core":       "source",
    "pkg":        "source", "packages":   "source",
    "internal":   "source", "cmd":        "source",
    "api":        "source", "service":    "source",
    "services":   "source", "models":     "source",
    "views":      "source", "controllers":"source",
    "routers":    "source", "routes":     "source",
    "handlers":   "source", "middleware": "source",
    "components": "source", "pages":      "source",
    "hooks":      "source", "store":      "source",
    "graphql":    "source",
}

# Extension sets used for language counting in a directory
_SOURCE_EXTS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".kt", ".rb", ".php", ".swift", ".cs", ".cpp", ".c", ".h",
    ".ex", ".exs", ".clj", ".hs", ".dart", ".scala",
}

_DOMINANT_LANG: dict[str, str] = {
    ".py": "Python",    ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript",".jsx": "JavaScript",".go": "Go",
    ".rs": "Rust",      ".java": "Java",     ".kt": "Kotlin",
    ".rb": "Ruby",      ".php": "PHP",       ".cs": "C#",
    ".cpp": "C++",      ".c": "C",           ".swift": "Swift",
    ".dart": "Dart",    ".ex": "Elixir",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_directories(
    clone_dir: Path,
    file_tree: FileNode,
) -> list[SourceDirectory]:
    """
    Walk the top two levels of *file_tree* and classify each directory.

    Parameters
    ----------
    clone_dir:
        Absolute path to the cloned repository root.
    file_tree:
        Root FileNode (from ScanResult).

    Returns
    -------
    list[SourceDirectory]
        One entry per classified top-level or second-level directory,
        sorted by role then path.
    """
    results: list[SourceDirectory] = []

    if file_tree.children is None:
        return results

    for child in file_tree.children:
        if child.type != "directory":
            continue
        role, lang, count = _classify_dir(clone_dir, child, depth=0)
        results.append(
            SourceDirectory(
                path=child.path,
                role=role,
                language=lang,
                file_count=count,
            )
        )
        # Also classify immediate sub-directories of "source" dirs
        if role == "source" and child.children:
            for subchild in child.children:
                if subchild.type != "directory":
                    continue
                subrole, sublang, subcount = _classify_dir(clone_dir, subchild, depth=1)
                if subrole != "source":   # only surface non-trivial sub-roles
                    results.append(
                        SourceDirectory(
                            path=subchild.path,
                            role=subrole,
                            language=sublang,
                            file_count=subcount,
                        )
                    )

    # Sort: role priority then path
    _role_order = {"source": 0, "tests": 1, "docs": 2, "config": 3,
                   "scripts": 4, "infra": 5, "assets": 6}
    results.sort(key=lambda d: (_role_order.get(d.role, 9), d.path))
    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_dir(
    clone_dir: Path,
    node: FileNode,
    depth: int,
) -> tuple[str, str, int]:
    """Return (role, dominant_language, file_count) for a directory node."""
    name_lower = Path(node.path).name.lower()

    # 1. Name-based rule (highest priority)
    if name_lower in _NAME_ROLES:
        role = _NAME_ROLES[name_lower]
    else:
        # 2. Content-based: look at file extensions inside the node
        role = _infer_role_from_children(node)

    # Count source files and detect dominant language
    lang_counts: Counter[str] = Counter()
    total = _count_files(node, lang_counts)

    dominant = ""
    if lang_counts:
        best_ext = lang_counts.most_common(1)[0][0]
        dominant = _DOMINANT_LANG.get(best_ext, "")

    return role, dominant, total


def _infer_role_from_children(node: FileNode) -> str:
    """Infer directory role from its file extension mix."""
    if not node.children:
        return "source"

    ext_counts: Counter[str] = Counter()
    _count_files(node, ext_counts)

    total = sum(ext_counts.values())
    if total == 0:
        return "source"

    # High fraction of test-named files
    test_exts = sum(
        c for ext, c in ext_counts.items()
        if ext in {".spec.ts", ".test.ts", ".spec.js", ".test.js"}
    )
    if test_exts / total > 0.4:
        return "tests"

    # Mostly markup → docs
    doc_exts = ext_counts.get(".md", 0) + ext_counts.get(".rst", 0)
    if doc_exts / total > 0.5:
        return "docs"

    # Mostly image/media → assets
    asset_exts = sum(
        ext_counts.get(e, 0)
        for e in {".png", ".jpg", ".svg", ".gif", ".ico", ".woff", ".ttf"}
    )
    if asset_exts / total > 0.4:
        return "assets"

    # Mostly IaC files → infra
    infra_exts = ext_counts.get(".tf", 0) + ext_counts.get(".hcl", 0)
    if infra_exts / total > 0.4:
        return "infra"

    return "source"


def _count_files(node: FileNode, counter: Counter) -> int:
    """Recursively count files and accumulate extension counts."""
    total = 0
    if node.type == "file":
        ext = Path(node.path).suffix.lower()
        counter[ext] += 1
        return 1
    for child in node.children or []:
        total += _count_files(child, counter)
    return total
