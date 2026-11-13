#!/usr/bin/env python3
"""Warns about four review-rule violations in text the model just wrote.

A project owner reviewing agent-written pull requests kept leaving the same
comments: an action on a moving tag, an image on `:latest`, a Spring Data
`@Query` string, a divider banner in a test. The skills state those rules, and
the code-reviewer standards checklist catches them at review time. This hook
catches the cheap, unambiguous part of them at the moment of the edit, while
the file is still open:

- a `uses: owner/repo@ref` in a YAML file whose ref is not a full 40-character
  commit SHA, or a SHA with no `# vX.Y.Z` comment after it
  (`deployment-patterns`);
- an image reference ending in `:latest`, outside markdown, or a
  `runs-on: <os>-latest` runner label in YAML (`docker-patterns`,
  `deployment-patterns`);
- a `@Query(`, `@NamedQuery(` or `@NamedNativeQuery(` annotation in a Java or
  Kotlin file (`springboot-patterns`);
- a divider-banner comment, such as `// ---- helpers ----` or
  `# ======`, in a test file (`tdd-workflow`).

It reads only what the tool wrote: `content` for Write, `new_string` for Edit,
and every `edits[].new_string` for MultiEdit. For an edit, a line that was
already in `old_string` is not reported, so moving old code does not repeat a
warning about it.

It is advisory and never blocks. Every outcome prints at most one JSON object
with the findings as `additionalContext` under `hookSpecificOutput`, and exits
0. It applies to `--format claude` on PostToolUse only, the one surface whose
post-tool hook can hand context back to the model. Every other invocation, any
other tool, a clean write, and any error at all return 0 with nothing printed.

It lives under .agents/hooks/claude/ so the OpenCode and Kilo Code runner,
which discovers only a script directly inside a hook folder of
.agents/hooks/, never runs it on a tool call.
"""

import json
import os
import re
import sys
from pathlib import Path, PurePath
from typing import Any, Dict, Iterable, List, Tuple

CLAUDE_FORMAT = "claude"

EVENT_NAME = "PostToolUse"

EDIT_TOOLS = ("edit", "write", "multiedit")

MAX_REPORTED = 20

SNIPPET_LENGTH = 120

YAML_SUFFIXES = (".yml", ".yaml")

JPA_SUFFIXES = (".java", ".kt")

PROSE_SUFFIXES = (".md", ".mdx", ".markdown", ".rst", ".txt", ".adoc")

TEST_DIRECTORIES = frozenset({"test", "tests", "__tests__", "spec", "specs"})

TEST_FILE_NAME = re.compile(
    r"(Tests?|IT|Spec)\.(java|kt|groovy|scala)$"
    r"|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|^test_.*\.py$|_test\.(py|go)$|^conftest\.py$"
)

USES = re.compile(r"""^\s*(?:-\s*)?uses:\s*['"]?([^\s'"#]+)['"]?\s*(#.*)?$""")

FULL_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

VERSION_COMMENT = re.compile(r"#\s*v?\d+\.\d+\.\d+")

LATEST_IMAGE = re.compile(r"[A-Za-z0-9][\w./-]*:latest\b")

LATEST_RUNNER = re.compile(r"""\bruns-on:.*\b[a-z]+-latest\b""")

QUERY_ANNOTATION = re.compile(r"@(?:Query|NamedQuery|NamedNativeQuery)\s*\(")

DIVIDER_BANNER = re.compile(r"""^\s*(?://+|#+|/\*+|\{/\*+|\*)\s*(?:[-=_~*#+─-╿]\s*){3,}""")


def _stdin_text() -> str:
    """Decode stdin as UTF-8 explicitly, never through the system code page."""
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _flag(argv: List[str], name: str) -> str:
    """Read one --flag value by hand, because argparse exits 2 and 2 is the deny code."""
    for index, token in enumerate(argv):
        if token == name and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith(name + "="):
            return token.split("=", 1)[1]

    return ""


def _tool_name(payload: Dict[str, Any]) -> str:
    name = payload.get("tool_name")

    return name.strip().lower() if isinstance(name, str) else ""


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _written(tool_input: Dict[str, Any]) -> Tuple[str, List[Tuple[str, str]]]:
    """The edited path and each (new, old) text pair the tool wrote."""
    path = _text(tool_input.get("file_path")).strip()

    if "content" in tool_input:
        return path, [(_text(tool_input.get("content")), "")]

    if "new_string" in tool_input:
        return path, [(_text(tool_input.get("new_string")), _text(tool_input.get("old_string")))]

    pairs = []
    edits = tool_input.get("edits")

    for edit in edits if isinstance(edits, list) else []:
        if not isinstance(edit, dict):
            continue

        path = path or _text(edit.get("file_path")).strip()
        pairs.append((_text(edit.get("new_string")), _text(edit.get("old_string"))))

    return path, pairs


def _introduced_lines(pairs: Iterable[Tuple[str, str]]) -> List[str]:
    lines = []

    for new, old in pairs:
        existing = set(old.splitlines())
        lines.extend(line for line in new.splitlines() if line not in existing)

    return lines


def _is_test_file(path: PurePath) -> bool:
    if TEST_FILE_NAME.search(path.name):
        return True

    return any(part.lower() in TEST_DIRECTORIES for part in path.parts[:-1])


def _unpinned_action(line: str) -> str:
    match = USES.match(line)

    if not match:
        return ""

    target, comment = match.group(1), match.group(2) or ""

    if target.startswith(("./", "docker://")) or "@" not in target:
        return ""

    ref = target.rsplit("@", 1)[1]

    if not FULL_SHA.match(ref):
        return (
            "action pinned to a moving ref instead of a full 40-character commit SHA; resolve it with "
            "`git ls-remote --tags https://github.com/<owner>/<repo> refs/tags/<tag> refs/tags/<tag>^{}` "
            "and add a `# vX.Y.Z` comment (deployment-patterns)"
        )

    if not VERSION_COMMENT.search(comment):
        return "commit SHA with no `# vX.Y.Z` comment naming the release it was resolved from (deployment-patterns)"

    return ""


def _findings_for_line(line: str, path: PurePath) -> List[str]:
    suffix = path.suffix.lower()
    is_yaml = suffix in YAML_SUFFIXES
    found = []

    if is_yaml:
        action = _unpinned_action(line)

        if action:
            found.append(action)

        if LATEST_RUNNER.search(line):
            found.append(
                "runner on a moving `-latest` label; name a fixed one such as `ubuntu-24.04` (deployment-patterns)"
            )

    if suffix not in PROSE_SUFFIXES and LATEST_IMAGE.search(line):
        found.append("image on `:latest`; pin an exact version tag plus its `@sha256:` digest (docker-patterns)")

    if suffix in JPA_SUFFIXES and QUERY_ANNOTATION.search(line):
        found.append(
            "query string annotation; use a Spring Data `Specification` or a derived query method (springboot-patterns)"
        )

    if suffix not in PROSE_SUFFIXES and _is_test_file(path) and DIVIDER_BANNER.match(line):
        found.append(
            "divider banner in a test; the only test comments are `// Given`, `// When`, `// Then` (tdd-workflow)"
        )

    return found


def _snippet(line: str) -> str:
    stripped = line.strip().replace("`", "'")

    return stripped if len(stripped) <= SNIPPET_LENGTH else stripped[: SNIPPET_LENGTH - 3] + "..."


def _report(path: str, findings: List[str]) -> int:
    shown = findings[:MAX_REPORTED]
    hidden = len(findings) - len(shown)
    lines = [f"Standards advisory for {path}, fix before you move on:"]
    lines.extend(f"- {finding}" for finding in shown)

    if hidden:
        lines.append(f"- and {hidden} more of the same kinds")

    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": EVENT_NAME,
                    "additionalContext": "\n".join(lines),
                }
            }
        )
    )

    return 0


# A plugin copy of this hook stands down when the project's own Claude Code
# wiring already runs this same script for the same call, so one call never
# runs it twice. Claude Code exports CLAUDE_PLUGIN_ROOT and CLAUDE_PROJECT_DIR
# to a hook's process (https://code.claude.com/docs/en/hooks, "Reference
# scripts by path"). It stands down only on a payload that names its event,
# for a wiring group of that event whose matcher takes the call's tool, and
# for a command that runs a script of the same name under the project's own
# .agents/hooks/ that exists. Anything else, or any doubt, runs the hook.
# tools/tests/test_plugin_copy.py holds this block equal in every hook that
# carries it.
PLUGIN_ROOT_VARIABLE = "CLAUDE_PLUGIN_ROOT"
PROJECT_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"
PROJECT_CLAUDE_WIRING = (".claude", "settings.json")
PROJECT_HOOK_PATH = r"\.agents/hooks/(?:[a-z0-9-]+/)*"
TOOL_EVENTS = frozenset({"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest"})
MATCH_ALL = (None, "", "*")


def _project_runs_this_script(project: Path, command: str, script: str) -> bool:
    """True when the command runs this script from the project's .agents/hooks/ and that file exists."""
    for match in re.finditer(PROJECT_HOOK_PATH + re.escape(script) + r"(?![A-Za-z0-9_.])", command):
        if project.joinpath(*match.group(0).split("/")).is_file():
            return True

    return False


def _matcher_takes(group: object, event: str, tool: object) -> bool:
    """True when a wiring group of a tool event matches the call's tool, as Claude Code matches it."""
    if event not in TOOL_EVENTS:
        return True

    matcher = group.get("matcher") if isinstance(group, dict) else None

    if matcher in MATCH_ALL:
        return True

    try:
        return isinstance(tool, str) and re.fullmatch(str(matcher), tool) is not None
    except re.error:
        return False


def _plugin_copy_is_shadowed(payload: object) -> bool:
    """True when this copy runs as a Claude Code plugin and the project's own wiring runs it for this call."""
    try:
        plugin_root = os.environ.get(PLUGIN_ROOT_VARIABLE, "")
        script = Path(__file__).resolve()

        if not plugin_root or not script.is_relative_to(Path(plugin_root).resolve()):
            return False

        fields = payload if isinstance(payload, dict) else {}
        event = fields.get("hook_event_name")
        project = os.environ.get(PROJECT_DIR_VARIABLE) or fields.get("cwd")

        if not isinstance(event, str) or not event or not isinstance(project, str) or not project:
            return False

        root = Path(project)
        settings = json.loads(root.joinpath(*PROJECT_CLAUDE_WIRING).read_text(encoding="utf-8"))

        for group in settings["hooks"].get(event, []):
            if not _matcher_takes(group, event, fields.get("tool_name")):
                continue

            for entry in group["hooks"]:
                if _project_runs_this_script(root, str(entry.get("command", "")), script.name):
                    return True
    except Exception:
        return False

    return False


def main(argv: List[str]) -> int:
    try:
        if _flag(argv, "--format").lower() != CLAUDE_FORMAT:
            return 0

        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict) or _tool_name(payload) not in EDIT_TOOLS:
            return 0

        if _plugin_copy_is_shadowed(payload):
            return 0

        tool_input = payload.get("tool_input")

        if not isinstance(tool_input, dict):
            return 0

        path, pairs = _written(tool_input)

        if not path:
            return 0

        pure_path = PurePath(path.replace("\\", "/"))
        findings = []

        for line in _introduced_lines(pairs):
            for finding in _findings_for_line(line, pure_path):
                findings.append(f"`{_snippet(line)}`: {finding}")

        if not findings:
            return 0

        return _report(path, findings)
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
