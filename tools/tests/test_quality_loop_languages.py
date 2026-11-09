"""Tests for .metrics/tools/quality_loop/languages.py: which languages a project holds, as the tools see it."""

import ast
from pathlib import Path

import pytest
from tests.quality_loop_support import QUALITY_TOOLS, write

from quality_loop import languages


def test_each_supported_language_is_found_by_its_source_file(tmp_path):
    for relative in ("a.clj", "b.go", "C.java", "d.py", "e.rs", "f.ts"):
        write(tmp_path, f"src/{relative}")

    assert languages.detect_languages(tmp_path) == languages.SUPPORTED


def test_javascript_counts_as_typescript_the_way_the_tools_count_it(tmp_path):
    write(tmp_path, "src/app.mjs")

    assert languages.detect_languages(tmp_path) == (languages.TYPESCRIPT,)


def test_the_folders_the_tools_skip_hold_no_language(tmp_path):
    for folder in (".metrics/tools/crapper/src", "node_modules/x", ".venv/lib", "target", "build", "tests", "test"):
        write(tmp_path, f"{folder}/skipped.py")

    assert languages.detect_languages(tmp_path) == ()


def test_test_files_and_type_declarations_are_not_source(tmp_path):
    for relative in ("test_a.py", "a_test.py", "conftest.py", "a_test.go", "a.test.ts", "a.spec.js", "types.d.ts"):
        write(tmp_path, f"src/{relative}")

    assert languages.source_files(tmp_path) == []


def test_a_kotlin_or_csharp_project_holds_no_supported_language(tmp_path):
    write(tmp_path, "src/Main.kt")
    write(tmp_path, "src/Program.cs")

    assert languages.detect_languages(tmp_path) == ()


def test_the_typescript_filters_select_every_typescript_and_javascript_extension():
    filters = languages.extension_filters(languages.TYPESCRIPT)

    assert set(filters) == {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"}
    assert all(languages.language_of(Path(f"x{suffix}")) == languages.TYPESCRIPT for suffix in filters)


def module_constants(path: Path) -> dict[str, object]:
    """The literal module-level constants of a vendored file, read with ast so none of its code runs."""
    constants = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except ValueError:
                continue
    return constants


@pytest.mark.parametrize("tool", ["crapper", "dryer"])
def test_the_copy_of_the_discovery_rules_matches_the_vendored_tool(tool):
    vendored = module_constants(QUALITY_TOOLS / tool / "src" / tool / "discover.py")

    assert languages.SKIPPED_DIRECTORIES == vendored["SKIP_DIRS"] | vendored["TEST_DIRS"]
    assert {extension: languages.EXTENSIONS.get(extension) for extension in vendored["EXTENSIONS"]} == vendored["EXTENSIONS"]
