"""Tests for the advisory hook at .agents/hooks/claude/standards-advisory-check/standards_advisory_check.py.

Driven as a subprocess, because the hook contract is the process contract:
stdin payload, --format flag, stdout shape, exit code. The hook reads only the
text in the payload, never the file on disk, so no test writes a file.
"""

import json
import sys

import pytest

from tests.conftest import REPO_ROOT, STANDARDS_ADVISORY_HOOK
from tests.process_tree import run_bounded

FULL_SHA = "0123456789abcdef0123456789abcdef01234567"


def run(payload, fmt="claude"):
    result = run_bounded(
        [sys.executable, "-S", "-E", str(STANDARDS_ADVISORY_HOOK), "--format", fmt],
        input=payload if isinstance(payload, str) else json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return result.returncode, result.stdout, result.stderr


def write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


def edit(path, old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old, "new_string": new}}


def context(out):
    output = json.loads(out)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUse"

    return output["additionalContext"]


def assert_silent(payload, fmt="claude"):
    assert run(payload, fmt) == (0, "", "")


def assert_warns(payload, expected):
    code, out, err = run(payload)

    assert (code, err) == (0, "")
    assert expected in context(out)


@pytest.mark.parametrize(
    "line",
    [
        "      - uses: actions/checkout@v5",
        "    uses: 'docker/login-action@main'",
        "uses: owner/repo/.github/workflows/ci.yml@v2",
    ],
    ids=["tag", "branch", "reusable-workflow"],
)
def test_an_action_on_a_moving_ref_warns(line):
    assert_warns(write(".github/workflows/ci.yml", line + "\n"), "full 40-character commit SHA")


def test_an_action_on_a_full_sha_with_its_release_comment_is_silent():
    assert_silent(write(".github/workflows/ci.yml", f"      - uses: actions/checkout@{FULL_SHA} # v5.0.1\n"))


def test_an_action_on_a_full_sha_without_a_release_comment_warns():
    assert_warns(write("action.yaml", f"    uses: actions/setup-node@{FULL_SHA}\n"), "`# vX.Y.Z` comment")


@pytest.mark.parametrize("line", ["uses: ./.github/actions/setup", "uses: docker://alpine:3"], ids=["local", "docker"])
def test_a_local_or_docker_action_is_not_an_action_pin(line):
    assert_silent(write(".github/workflows/ci.yml", line + "\n"))


def test_a_latest_runner_label_warns():
    assert_warns(write(".github/workflows/ci.yml", "    runs-on: ubuntu-latest\n"), "`-latest` label")


def test_a_fixed_runner_label_is_silent():
    assert_silent(write(".github/workflows/ci.yml", "    runs-on: ubuntu-24.04\n"))


def test_an_action_pin_outside_yaml_is_not_checked():
    assert_silent(write("docs/notes.txt", "uses: actions/checkout@v5\n"))


@pytest.mark.parametrize(
    ("path", "line"),
    [
        ("Dockerfile", "FROM node:latest"),
        ("infra/docker-compose.yaml", "    image: ${API_IMAGE:-ghcr.io/acme/api:latest}"),
        ("infra/docker-compose.yaml", "    image: cloudflare/cloudflared:latest"),
        ("src/test/java/RepoIT.java", '    new PostgreSQLContainer("postgres:latest");'),
    ],
    ids=["dockerfile", "compose-default", "compose", "testcontainers"],
)
def test_an_image_on_latest_warns(path, line):
    assert_warns(write(path, line + "\n"), "image on `:latest`")


def test_a_pinned_image_is_silent():
    assert_silent(write("Dockerfile", "FROM node:26-alpine@sha256:<digest>\n"))


@pytest.mark.parametrize("path", ["README.md", "docs/GUIDE.mdx", "notes.txt"])
def test_latest_in_prose_is_not_an_image(path):
    assert_silent(write(path, "Never pin `node:latest` in a Dockerfile.\n"))


@pytest.mark.parametrize(
    "line",
    [
        '    @Query("select s from SubmissionEntity s")',
        '@NamedQuery(name = "x", query = "select x")',
        '@Query (value = "SELECT 1", nativeQuery = true)',
    ],
    ids=["jpql", "named", "native"],
)
def test_a_query_annotation_in_java_warns(line):
    assert_warns(write("infra/persistence/SubmissionJpa.java", line + "\n"), "Specification")


def test_a_query_annotation_in_kotlin_warns():
    assert_warns(write("src/main/kotlin/Repo.kt", '@Query("select r from R r")\n'), "Specification")


def test_a_query_annotation_outside_jvm_source_is_silent():
    assert_silent(write("docs/persistence.txt", '@Query("select s from S s")\n'))


def test_a_specification_is_silent():
    assert_silent(write("Repo.java", "Page<S> findAll(Specification<S> spec, Pageable pageable);\n"))


@pytest.mark.parametrize(
    ("path", "line"),
    [
        ("src/test/java/com/acme/FooServiceTest.java", "    // ---- helpers ----"),
        ("apps/web/src/lib/api/expenses.test.ts", "// ─── MODULE MOCKS ───"),
        ("tools/tests/test_converter.py", "# ======================"),
        ("apps/api/src/integrationTest/java/BackupIT.java", "// ------------------------------"),
        ("apps/web/src/components/Form.spec.tsx", "  {/* ---- toast feedback ---- */}"),
        ("e2e/tests/login.ts", "/* ***** setup ***** */"),
    ],
    ids=["java", "typescript-box", "python", "it", "jsx", "test-dir"],
)
def test_a_divider_banner_in_a_test_warns(path, line):
    assert_warns(write(path, line + "\n"), "divider banner in a test")


@pytest.mark.parametrize("line", ["    // Given", "    // When & Then", "    # Then", "/**", " * Javadoc line"])
def test_the_phase_markers_and_doc_comments_are_not_banners(line):
    assert_silent(write("src/test/java/FooTest.java", line + "\n"))


def test_a_divider_banner_outside_a_test_file_is_not_reported_by_this_hook():
    assert_silent(write("src/main/java/com/acme/FooService.java", "    // ---- helpers ----\n"))


def test_an_edit_reports_only_lines_it_introduced():
    old = "FROM node:latest\n"
    new = "FROM node:latest\nRUN npm ci\n"

    assert_silent(edit("Dockerfile", old, new))


def test_an_edit_that_adds_a_violation_warns():
    assert_warns(edit("Dockerfile", "RUN npm ci\n", "FROM node:latest\nRUN npm ci\n"), "image on `:latest`")


def test_a_multi_edit_reads_every_new_string():
    payload = {
        "tool_name": "MultiEdit",
        "tool_input": {
            "file_path": "Repo.java",
            "edits": [
                {"old_string": "a", "new_string": "b"},
                {"old_string": "c", "new_string": '@Query("select r from R r")'},
            ],
        },
    }

    assert_warns(payload, "Specification")


def test_the_report_names_the_file_and_quotes_the_line():
    code, out, err = run(write(".github/workflows/ci.yml", "      - uses: actions/checkout@v5\n"))

    report = context(out)
    assert ".github/workflows/ci.yml" in report
    assert "`- uses: actions/checkout@v5`" in report


def test_many_findings_are_capped_with_a_count_of_the_rest():
    content = "".join(f"FROM image{index}:latest\n" for index in range(25))

    report = context(run(write("Dockerfile", content))[1])

    assert report.count("image on `:latest`") == 20
    assert "and 5 more" in report


@pytest.mark.parametrize("fmt", ["plain", "codex", "copilot", ""], ids=["plain", "codex", "copilot", "empty"])
def test_a_format_other_than_claude_reports_nothing(fmt):
    assert_silent(write("Dockerfile", "FROM node:latest\n"), fmt=fmt)


def test_no_format_flag_at_all_reports_nothing():
    result = run_bounded(
        [sys.executable, str(STANDARDS_ADVISORY_HOOK)],
        input=json.dumps(write("Dockerfile", "FROM node:latest\n")),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")


@pytest.mark.parametrize("tool", ["Read", "Bash", "Grep", ""], ids=["read", "bash", "grep", "none"])
def test_a_tool_that_writes_nothing_is_not_checked(tool):
    assert_silent({"tool_name": tool, "tool_input": {"file_path": "Dockerfile", "content": "FROM node:latest\n"}})


@pytest.mark.parametrize(
    "payload",
    [
        "{not json at all",
        "[]",
        json.dumps({"tool_name": "Write", "tool_input": "Dockerfile"}),
        json.dumps({"tool_name": "Write", "tool_input": {"content": "FROM node:latest"}}),
    ],
    ids=["malformed", "list", "string-input", "no-path"],
)
def test_an_unexpected_payload_reports_nothing(payload):
    assert_silent(payload)


def test_a_clean_write_reports_nothing():
    assert_silent(write("src/main/java/Foo.java", "class Foo {}\n"))


def test_claude_code_runs_it_after_every_edit():
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [
        hook["command"]
        for entry in settings["hooks"]["PostToolUse"]
        if entry.get("matcher") == "^(Edit|Write|MultiEdit)$"
        for hook in entry["hooks"]
    ]

    hook = ".agents/hooks/claude/standards-advisory-check/standards_advisory_check.py --format claude"
    wired = [command for command in commands if hook in command]
    assert len(wired) == 1
    assert wired[0].startswith('cd "${CLAUDE_PROJECT_DIR}"')
    assert wired[0].endswith("; exit 0")


def run_plugin_copy(tmp_path, wired):
    """The hook as the hook-standards-advisory-check plugin installs it, run for a project that may wire its own copy."""
    import os
    import shutil

    folder = tmp_path / "config" / "plugins" / "cache" / "agent-standards" / "hook-standards-advisory-check" / "1.0.0"
    folder.mkdir(parents=True)
    hook = folder / STANDARDS_ADVISORY_HOOK.name
    shutil.copy(STANDARDS_ADVISORY_HOOK, hook)
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)
    if wired:
        command = 'cd "${CLAUDE_PROJECT_DIR}" && python3 -S -E .agents/hooks/claude/standards-advisory-check/standards_advisory_check.py --format claude ; exit 0'
        (project / ".claude" / "settings.json").write_text(
            json.dumps({"hooks": {"PostToolUse": [{"matcher": "^(Edit|Write|MultiEdit)$", "hooks": [{"type": "command", "command": command}]}]}}), encoding="utf-8"
        )
        own = project / ".agents" / "hooks" / "claude" / "standards-advisory-check" / "standards_advisory_check.py"
        own.parent.mkdir(parents=True)
        own.write_text("# own\n", encoding="utf-8")
    payload = {**write("ci.yml", "uses: actions/checkout@v5\n"), "hook_event_name": "PostToolUse"}
    environment = {**os.environ, "CLAUDE_PROJECT_DIR": str(project), "CLAUDE_PLUGIN_ROOT": str(folder), "CLAUDE_CONFIG_DIR": str(tmp_path / "config")}
    result = run_bounded(
        [sys.executable, "-S", "-E", str(hook), "--format", "claude"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(project),
        env=environment,
    )

    return result.returncode, result.stdout


@pytest.mark.parametrize(("wired", "warns"), [(False, True), (True, False)], ids=["alone-warns", "project-wired-stands-down"])
def test_a_plugin_copy_warns_unless_the_project_wiring_runs_the_hook(tmp_path, wired, warns):
    code, out = run_plugin_copy(tmp_path, wired)

    assert code == 0
    assert bool(out) is warns
