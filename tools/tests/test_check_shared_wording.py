"""Tests for tools/check-shared-wording.py.

Every case builds a throwaway root holding tools/shared-wording.yaml and the
files it lists, and runs the script as a child process against it, the way CI
runs it. The last test runs the guard over the real repository and its real
map, so a shared wording that drifted in one copy can never reach a green
suite.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from tests.conftest import REPO_ROOT, SUBPROCESS_TIMEOUT_SECONDS

CHECK_SHARED_WORDING = REPO_ROOT / "tools" / "check-shared-wording.py"
MAP_PATH = Path("tools") / "shared-wording.yaml"

SHARED_RULES = "1. Print every draft in the chat.\n2. Post nothing until the user has approved it.\n"
ONE_COPY = ".agents/skills/one/SKILL.md"
OTHER_COPY = ".agents/skills/other/SKILL.md"

VALID_MAP = f"""entries:
  - id: drafts
    files:
      - {ONE_COPY}
      - {OTHER_COPY}
    text: |
      1. Print every draft in the chat.
      2. Post nothing until the user has approved it.
"""


class _Tree:
    def __init__(self, root: Path) -> None:
        self.root = root

    def write(self, relative: str | Path, content: str, newline: str = "\n") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline=newline)

        return path

    def map(self, content: str) -> Path:
        return self.write(MAP_PATH, content)


@pytest.fixture
def tree(tmp_path):
    shared_tree = _Tree(tmp_path)
    shared_tree.map(VALID_MAP)
    shared_tree.write(ONE_COPY, f"### Drafts\n\nKept the same in `other`.\n\n{SHARED_RULES}")
    shared_tree.write(OTHER_COPY, f"### Drafts\n\nKept the same in `one`.\n\n{SHARED_RULES}3. A rule of its own.\n")

    return shared_tree


def _run_guard(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK_SHARED_WORDING), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
    )


def _assert_passes(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stderr == ""


def _assert_exits_naming(result: subprocess.CompletedProcess[str], code: int, *fragments: str) -> None:
    assert result.returncode == code, result.stdout + result.stderr
    for fragment in fragments:
        assert fragment in result.stderr


def test_every_copy_matching_word_for_word_passes(tree):
    # When
    result = _run_guard(tree.root)

    # Then
    _assert_passes(result)


def test_a_copy_with_crlf_line_endings_still_passes(tree):
    # Given
    tree.write(ONE_COPY, f"### Drafts\n\n{SHARED_RULES}", newline="\r\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_passes(result)


def test_one_changed_copy_fails_naming_the_file_the_entry_and_the_line(tree):
    # Given
    tree.write(OTHER_COPY, "1. Print every draft in the chat.\n2. Post nothing until someone approved it.\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 1, OTHER_COPY, "`drafts`", "2. Post nothing until the user has approved it.")
    assert ONE_COPY not in result.stderr


def test_a_copy_with_its_lines_in_another_order_fails(tree):
    # Given
    tree.write(ONE_COPY, "2. Post nothing until the user has approved it.\n1. Print every draft in the chat.\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(
        result, 1, ONE_COPY, "`drafts`", 'ends after line 2 where the shared wording continues with "2. Post nothing'
    )


def test_a_changed_line_that_also_appears_elsewhere_is_reported_where_the_copy_differs(tree):
    # Given
    tree.write(
        OTHER_COPY,
        "2. Post nothing until the user has approved it.\n\n"
        "1. Print every draft in the chat.\n2. Post nothing until someone approved it.\n",
    )

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(
        result,
        1,
        OTHER_COPY,
        'line 4 reads "2. Post nothing until someone approved it." where the shared wording has '
        '"2. Post nothing until the user has approved it."',
    )


def test_a_copy_that_only_ends_with_the_first_line_fails(tree):
    # Given
    tree.write(ONE_COPY, f"1{SHARED_RULES}")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 1, ONE_COPY, "`drafts`")


def test_a_copy_whose_last_line_runs_on_fails(tree):
    # Given
    tree.write(ONE_COPY, SHARED_RULES.rstrip("\n") + " Or ask again.\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 1, ONE_COPY, "`drafts`")


def test_a_copy_at_the_very_end_of_a_file_without_a_final_newline_passes(tree):
    # Given
    tree.write(ONE_COPY, "### Drafts\n\n" + SHARED_RULES.rstrip("\n"))

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_passes(result)


def test_every_drifted_copy_is_reported_in_one_run(tree):
    # Given
    tree.write(ONE_COPY, "nothing shared\n")
    tree.write(OTHER_COPY, "nothing shared either\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 1, ONE_COPY, OTHER_COPY)


def test_a_listed_file_that_does_not_exist_exits_2(tree):
    # Given
    (tree.root / OTHER_COPY).unlink()

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 2, OTHER_COPY)


def test_a_listed_file_that_is_not_utf8_exits_2(tree):
    # Given
    (tree.root / OTHER_COPY).write_bytes(b"\xff\xfe not UTF-8\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 2, OTHER_COPY, "is not valid UTF-8")


def test_a_root_without_a_map_exits_2(tmp_path):
    # When
    result = _run_guard(tmp_path)

    # Then
    _assert_exits_naming(result, 2, MAP_PATH.as_posix())


@pytest.mark.parametrize(
    "bad_map",
    [
        pytest.param("entries: [\n", id="not-yaml"),
        pytest.param("- id: drafts\n", id="not-a-mapping"),
        pytest.param("entries: []\n", id="no-entries"),
        pytest.param("entries:\n  - drafts\n", id="entry-not-a-mapping"),
        pytest.param(f"entries:\n  - files: [{ONE_COPY}, {OTHER_COPY}]\n    text: x\n", id="missing-id"),
        pytest.param(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, {OTHER_COPY}]\n", id="missing-text"),
        pytest.param(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, {OTHER_COPY}]\n    text: ''\n", id="empty-text"),
        pytest.param("entries:\n  - id: drafts\n    text: x\n", id="missing-files"),
        pytest.param(f"entries:\n  - id: drafts\n    files: {ONE_COPY}\n    text: x\n", id="files-not-a-list"),
        pytest.param(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}]\n    text: x\n", id="one-file"),
        pytest.param(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, 7]\n    text: x\n", id="file-not-a-string"),
        pytest.param(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, {ONE_COPY}]\n    text: x\n", id="same-file-twice"),
        pytest.param(
            f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, {OTHER_COPY}]\n    text: x\n"
            f"  - id: drafts\n    files: [{ONE_COPY}, {OTHER_COPY}]\n    text: y\n",
            id="duplicate-id",
        ),
        pytest.param(
            f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, {OTHER_COPY}]\n    text: x\n    note: y\n",
            id="unknown-key",
        ),
    ],
)
def test_a_bad_map_exits_2(tree, bad_map):
    # Given
    tree.map(bad_map)

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 2, MAP_PATH.as_posix())


@pytest.mark.parametrize(
    "outside",
    [
        pytest.param("../outside.md", id="parent"),
        pytest.param(".agents/../../outside.md", id="parent-inside-the-path"),
        pytest.param("/etc/hostname", id="absolute"),
        pytest.param("C:/outside.md", id="windows-drive"),
    ],
)
def test_a_listed_path_outside_the_root_exits_2(tree, outside):
    # Given
    tree.map(f"entries:\n  - id: drafts\n    files: [{ONE_COPY}, '{outside}']\n    text: x\n")

    # When
    result = _run_guard(tree.root)

    # Then
    _assert_exits_naming(result, 2, MAP_PATH.as_posix(), f"`{outside}`", "inside the root")


def test_the_real_repository_passes():
    # When
    result = _run_guard(REPO_ROOT)

    # Then
    _assert_passes(result)
