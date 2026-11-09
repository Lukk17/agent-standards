"""Which supported languages a project holds, found the way Robert C. Martin's tools find them.

The extension map, the skipped directories and the test-file rules repeat crapper's
`discover.py`, with the `.cljd` extension dryer adds. The wrapper runs under the user's
own Python and cannot import the tools from their environments, so it keeps this copy.
"""

from __future__ import annotations

import os
from pathlib import Path

CLOJURE = "clojure"
GO = "go"
JAVA = "java"
PYTHON = "python"
RUST = "rust"
TYPESCRIPT = "typescript"

SUPPORTED = (CLOJURE, GO, JAVA, PYTHON, RUST, TYPESCRIPT)

EXTENSIONS: dict[str, str] = {
    ".clj": CLOJURE,
    ".cljc": CLOJURE,
    ".cljs": CLOJURE,
    ".cljd": CLOJURE,
    ".bb": CLOJURE,
    ".java": JAVA,
    ".go": GO,
    ".ts": TYPESCRIPT,
    ".tsx": TYPESCRIPT,
    ".mts": TYPESCRIPT,
    ".cts": TYPESCRIPT,
    ".js": TYPESCRIPT,
    ".jsx": TYPESCRIPT,
    ".mjs": TYPESCRIPT,
    ".cjs": TYPESCRIPT,
    ".rs": RUST,
    ".py": PYTHON,
}

SKIPPED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".venv",
        "venv",
        "node_modules",
        "vendor",
        "target",
        "dist",
        "build",
        "out",
        "coverage",
        ".metrics",
        "testdata",
        "__pycache__",
        ".clj-kondo",
        "test",
        "tests",
        "spec",
        "specs",
        "__tests__",
    }
)

_TEST_SUFFIXES = (
    "_test.go",
    "_test.clj",
    "_test.cljc",
    "_test.cljs",
    "_test.cljd",
    "_test.bb",
    "_test.py",
    ".test.ts",
    ".spec.ts",
    ".test.tsx",
    ".spec.tsx",
    ".test.mts",
    ".spec.mts",
    ".test.cts",
    ".spec.cts",
    ".test.js",
    ".spec.js",
    ".test.jsx",
    ".spec.jsx",
    ".test.mjs",
    ".spec.mjs",
    ".test.cjs",
    ".spec.cjs",
)


def language_of(path: Path) -> str | None:
    """The language a source file is written in, or None for any other file."""
    if path.name.endswith(".d.ts"):
        return None
    return EXTENSIONS.get(path.suffix)


def is_test_file(path: Path) -> bool:
    """True for a file the tools treat as a test rather than as source to measure."""
    name = path.name
    if name == "conftest.py" or name.endswith(_TEST_SUFFIXES):
        return True
    return name.startswith("test_") and name.endswith(".py")


def source_files(root: Path) -> list[Path]:
    """Every source file under root that the tools would measure, sorted."""
    found: list[Path] = []
    for directory, subdirectories, names in os.walk(root):
        subdirectories[:] = sorted(name for name in subdirectories if name not in SKIPPED_DIRECTORIES)
        for name in sorted(names):
            path = Path(directory) / name
            if language_of(path) is not None and not is_test_file(path):
                found.append(path)
    return found


def detect_languages(root: Path) -> tuple[str, ...]:
    """The supported languages with at least one source file under root, in SUPPORTED order."""
    present = {language_of(path) for path in source_files(root)}
    return tuple(language for language in SUPPORTED if language in present)


def extension_filters(language: str) -> tuple[str, ...]:
    """The path fragments that select one language's files through the tools' filter arguments."""
    return tuple(sorted(extension for extension, owner in EXTENSIONS.items() if owner == language))
