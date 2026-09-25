#!/usr/bin/env python3
"""Blocks a reply whose prose carries banned formatting, and fixes what it can.

Strips fenced code blocks, inline code, link targets, bare URLs, table rows and
HTML entities, then blocks when what is left contains an em dash (U+2014), an
en dash (U+2013), a semicolon, bold, or italic. Bold and italic are matched as
paired delimiters in both spellings, `**text**` and `__text__` for bold,
`*text*` and `_text_` for italic, so a bullet marker, a multiplication sign and
a snake_case identifier are not mistaken for emphasis. One bold line is
allowed: a line that is entirely `**NOW: ...**`, the current-task line of the
status block that ends a reply. Its text is still checked for every other
marker.

Four of those markers can be fixed mechanically, and `fix_prose` does it: a
dash becomes a comma with clean spacing (a hyphen in a digit range), and bold
and italic lose their delimiters, the NOW line excepted. Code spans, fenced
blocks, link targets and URLs stay as written. The fix works line by line, so a
batch of whole lines comes out the same as the whole text would. A semicolon
joining two clauses cannot be fixed without reading the sentence, so it is only
ever reported.

Modes over the same detection and the same fix:

Stop hook (default, or --format claude, codex or copilot). Reads the Stop,
SubagentStop or agentStop payload as JSON on stdin and takes the reply from
`last_assistant_message`, falling back to the transcript the payload names.
Blocking prints {"decision": "block", "reason": "..."} on stdout and exits 0, a
clean reply prints nothing. The reason asks a reply on screen for corrected
lines only, and asks a subagent for its whole report again, because the
subagent's next reply replaces the report its caller receives.
`stop_hook_active`, or Copilot's `stopHookActive`, short-circuits the check so
one forced correction cannot loop, and a per-session
counter in a small state file allows the next stop after a block even on a
payload that carries neither flag. With --display-fixed, the lines the display
fix recorded as fixed on screen for this session are run through the same fix
first, so only what the display left behind blocks. A reply with no such
record, because the display hook never ran, is checked in full. A copy whose
own path lies outside the project directory, a user-level install, stays
silent when the project's own hook configuration already runs this check on the
same event, so the two never block the same reply twice. Anything it cannot
read leaves the check running. The Copilot CLI also runs the Claude wiring it
reads from .claude/settings.json, so a claude-format Stop payload in Copilot's
documented shape stays silent and leaves the reply to the agentStop wiring.

Display (--display, Claude Code MessageDisplay). Reads one batch of a streaming
message and prints the fixed batch as `displayContent`, or nothing when there
is nothing to fix. The fence open at the end of a batch, and every line the fix
changed, keyed by message id, are kept in a small file in the session's
scratchpad directory, or a private temp directory, so a code block that spans
batches stays untouched and the Stop check knows what the user saw fixed.
Display only: the transcript and the model keep the original.

Runner (--format plain). The contract at
https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md
defines one envelope as JSON on stdin. On `tool.execute.before` the prose comes
from its `assistant_text` field, and blocking prints the reason on stderr and
exits 2. On `experimental.text.complete` it fixes the envelope's `text` and
prints {"text": "..."} on stdout, which the plugin stores in place of the
finished text part.

Text (--text). Reads raw UTF-8 prose on stdin, same output shape as the runner
mode. For calling the check by hand.

Arguments are scanned by hand rather than with argparse, because argparse
exits 2 on a usage error and 2 is the deny code in the plain format.

Every failure path allows: a broken hook must never break a session.
"""

import json
import os
import re
import sys
from pathlib import Path

# Runner order. Formatting runs after the preflight gate, because a policy
# denial about the action being attempted outranks a note about prose that has
# already been sent.
HOOK_ORDER = 20

# The runner hands experimental.text.complete only to hooks that declare this.
HOOK_TEXT_EVENT = True

# Runner envelope versions this hook understands (docs/hooks-contract.md). A
# plain envelope naming any other version is allowed unread.
CONTRACTS = frozenset({3})

TEXT_EVENT = "experimental.text.complete"

EM_DASH = "—"
EN_DASH = "–"

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
INLINE_CODE_RE = re.compile(r"``[^\n]+?``|`[^`\n]*`")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
BARE_URL_RE = re.compile(r"<?\b[a-z][a-z0-9+.-]*://[^\s>)\]]+>?", re.IGNORECASE)
TABLE_ROW_RE = re.compile(r"^\s*\|")
HTML_ENTITY_RE = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
# A backslash-escaped delimiter is literal text in markdown, never emphasis.
# An escaped backslash is matched as a pair, so `\\*a*` stays italic.
ESCAPED_MARKER_RE = re.compile(r"\\[\\*_]")
STATUS_NOW_LINE_RE = re.compile(r"^\s*\*\*(NOW: [^*\n]+?)\*\*\s*$")

# Paired delimiters, both spellings. The opener may not be preceded by a word
# character or by another delimiter of the same kind, and the run may not start
# or end on whitespace, which is what separates emphasis from a `* ` bullet
# marker, an `a * b` multiplication, and a snake_case identifier. The group is
# the emphasised text, which is what the fix keeps.
BOLD_RE = re.compile(
    r"\*\*(?=\S)((?:[^*]|\*(?!\*))+?)(?<=\S)\*\*|__(?=\S)((?:[^_]|_(?!_))+?)(?<=\S)__"
)
# A run holding a slash is a path rather than emphasis, which is what keeps a
# sentence naming two unbackticked globs, `docs/*.md and tools/*.py`, from
# reading as one italic run between the two asterisks.
ITALIC_RE = re.compile(
    r"(?<![\w*])\*(?![\s*])([^*/\n]*?)(?<![\s*])\*(?![\w*])"
    r"|(?<![\w_])_(?![\s_])([^_/\n]*?)(?<![\s_])_(?![\w_])"
)

# What the fix must leave exactly as written: escaped delimiters, code spans,
# link targets and URLs. Each is swapped for one private-use character while
# the line is fixed.
PROTECTED_RE = re.compile(
    "|".join(
        (
            ESCAPED_MARKER_RE.pattern,
            INLINE_CODE_RE.pattern,
            LINK_TARGET_RE.pattern,
            "(?i:" + BARE_URL_RE.pattern + ")",
        )
    )
)
PLACEHOLDER_FIRST = 0xE000
PLACEHOLDER_RE = re.compile("[-]")
PLACEHOLDER_COUNT = 0xF8FF - PLACEHOLDER_FIRST + 1

DASH_RE = re.compile("[–—]+")
FIXABLE_CHARS = EM_DASH + EN_DASH + "*_"
# A display batch holding none of these can neither change nor move a fence.
DISPLAY_CHARS = FIXABLE_CHARS + "`~"
# How a dash is replaced depends on what surrounds it. Nothing is added after an
# opening bracket or before closing punctuation, and one space is enough after
# punctuation that already pauses.
OPENING = "([{"
CLOSING = ".,;:!?)]}"
PAUSING = ".,;:!?"

DISPLAY_EVENT = "MessageDisplay"
DISPLAY_STATE_FILE = "no-ai-markers-display-{session}.json"
STOP_STATE_FILE = "no-ai-markers-stop-{session}.json"
UNSAFE_NAME_RE = re.compile(r"[^A-Za-z0-9-]")
# The newest messages whose display fixes are kept for the Stop check.
FIXED_MESSAGE_CAP = 16

# Claude Code and Copilot's VS Code shaped payload spell the loop flag in snake
# case, and a camelCase Copilot payload may spell it the camelCase way.
LOOP_FLAGS = ("stop_hook_active", "stopHookActive")
SESSION_KEYS = ("session_id", "sessionId")
# Blocks in a row, per session, before the next stop is allowed unchecked.
MAX_CONSECUTIVE_BLOCKS = 1

EXCERPT_RADIUS = 30

REASON_HEAD = "Formatting violation in your last reply. The prose contains: "

REASON_FIXES = (
    " Replace an em dash or en dash with a comma, a period, a "
    "colon, or parentheses. Replace a semicolon with a period or a comma, or split "
    "the sentence. Remove bold and italic."
)

REASON_TAIL = (
    ". That reply is already on screen, so do not repeat it and do not rewrite it "
    "in full. Write only the sentences or lines that needed fixing, one per line, "
    'each starting with "Correction:" followed by the fixed text in quotes, and '
    "write nothing else." + REASON_FIXES
)

SUBAGENT_REASON_TAIL = (
    ". That reply is the report your caller receives, and your next reply "
    "replaces it, so write the whole report again with every violation fixed and "
    "nothing left out." + REASON_FIXES
)

# Claude Code names the event and carries agent_id only inside a subagent. The
# Copilot CLI hands the SubagentStop it borrows from .claude/settings.json a
# camelCase payload with no event name and the subagent's agentId.
SUBAGENT_STOP_KEYS = ("agent_id", "agentId")

# Project files that can wire this check, per format, as glob patterns under
# the project root. A copy running from outside the project stays silent when
# one of them already runs the check on the same event, so a user-level install
# and a project wiring never both block and never both rewrite.
PROJECT_WIRING = {
    "claude": (".claude/settings.json", ".claude/settings.local.json"),
    "codex": (".codex/config.toml", ".codex/hooks.json"),
    "copilot": (".github/hooks/*.json",),
}

# The event a payload means when it does not name one. Copilot's camelCase
# agentStop payload carries no event name at all.
DEFAULT_EVENT = {"claude": "Stop", "codex": "Stop", "copilot": "agentStop"}


def _last_assistant_text(lines: list[str]) -> str:
    """Return the text of the newest assistant message that carries any text.

    Assistant turns that hold only tool calls have no text. Skipping past them
    keeps the check on the prose the user actually reads. Claude Code and Codex
    write `{"message": {"role", "content"}}` lines, and the Copilot CLI writes
    `{"type": "assistant.message", "data": {"content"}}` events.
    """
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue

        try:
            entry = json.loads(line)
        except ValueError:
            continue

        if not isinstance(entry, dict):
            continue

        message = entry.get("message")
        message = message if isinstance(message, dict) else {}
        data = entry.get("data")
        data = data if isinstance(data, dict) else {}
        role = message.get("role") or entry.get("role") or entry.get("type")

        if role not in ("assistant", "assistant.message"):
            continue

        content = message.get("content", entry.get("content", data.get("content")))
        text = _content_text(content)

        if text.strip():
            return text

    return ""


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return ""

    parts: list[str] = []

    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            value = block.get("text")
            if isinstance(value, str):
                parts.append(value)

    return "\n".join(parts)


def _step_fence(line: str, fence: str) -> tuple[bool, str]:
    """Whether a line is a fence or fenced content, and the fence open after it.

    Fences are matched by character and length, so a four-backtick wrapper
    around a three-backtick sample stays one block instead of splitting. `fence`
    is the opening marker still open, or "" outside any block.
    """
    match = FENCE_RE.match(line)

    if not match:
        return bool(fence), fence

    marker = match.group(2)

    if not fence:
        return True, marker

    if marker[0] == fence[0] and len(marker) >= len(fence) and not match.group(3).strip():
        return True, ""

    return True, fence


def strip_code(text: str) -> str:
    """Drop everything that is not prose the reader is meant to read as prose.

    Fenced blocks, table rows, inline code spans, escaped delimiters, link
    targets, bare URLs and HTML entities all go. A table row goes whole, because its cell separators
    and its entities are markup rather than punctuation, and `&amp;` ends in a
    semicolon that is not one. The status block's NOW line keeps its text and
    loses only its bold delimiters.
    """
    kept: list[str] = []
    fence = ""

    for line in text.splitlines():
        code, fence = _step_fence(line, fence)

        if code or TABLE_ROW_RE.match(line):
            continue

        now_line = STATUS_NOW_LINE_RE.match(line)

        kept.append(now_line.group(1) if now_line else line)

    prose = "\n".join(kept)
    prose = INLINE_CODE_RE.sub(" ", prose)
    prose = ESCAPED_MARKER_RE.sub(" ", prose)
    prose = LINK_TARGET_RE.sub("]( )", prose)
    prose = BARE_URL_RE.sub(" ", prose)
    prose = HTML_ENTITY_RE.sub(" ", prose)

    return prose


def fix_prose(text: str, fence: str = "") -> tuple[str, str]:
    """Remove every marker a machine can fix, and return the fence open after the text.

    Args:
        fence: the fence already open before the first line, "" for none.
    """
    lines = text.split("\n")

    for index, line in enumerate(lines):
        code, fence = _step_fence(line, fence)

        if not code:
            lines[index] = _fix_line(line)

    return "\n".join(lines), fence


def _fix_line(line: str) -> str:
    body, ending = (line[:-1], "\r") if line.endswith("\r") else (line, "")
    now_line = STATUS_NOW_LINE_RE.match(body)

    if now_line:
        inner = _fix_span(now_line.group(1))

        return body[: now_line.start(1)] + inner + body[now_line.end(1) :] + ending

    return _fix_span(body) + ending


def _fix_span(text: str) -> str:
    """Fix one line, with code spans, link targets and URLs held aside."""
    if not any(char in text for char in FIXABLE_CHARS) or PLACEHOLDER_RE.search(text):
        return text

    held: list[str] = []

    def hold(match: re.Match[str]) -> str:
        held.append(match.group(0))

        return chr(PLACEHOLDER_FIRST + len(held) - 1)

    masked = PROTECTED_RE.sub(hold, text)

    if len(held) > PLACEHOLDER_COUNT:
        return text

    masked = _fix_dashes(masked)
    masked = BOLD_RE.sub(_emphasised_text, masked)
    masked = ITALIC_RE.sub(_emphasised_text, masked)

    return PLACEHOLDER_RE.sub(lambda match: held[ord(match.group(0)) - PLACEHOLDER_FIRST], masked)


def _emphasised_text(match: re.Match[str]) -> str:
    return next(group for group in match.groups() if group is not None)


def _fix_dashes(text: str) -> str:
    fixed = ""
    rest = text

    while match := DASH_RE.search(rest):
        before = fixed + rest[: match.start()]
        after = rest[match.end() :].lstrip(" \t")
        trimmed = before.rstrip(" \t")

        if not trimmed:
            fixed = before
        elif not after:
            fixed = trimmed
        else:
            fixed = trimmed + _dash_joiner(trimmed[-1], after[0], match.group(0))

        rest = after

    return fixed + rest


def _dash_joiner(before: str, after: str, dashes: str) -> str:
    if before in OPENING or after in CLOSING:
        return ""

    if before in PAUSING:
        return " "

    if dashes == EN_DASH and before.isdigit() and after.isdigit():
        return "-"

    return ", "


def _excerpt(prose: str, index: int) -> str:
    start = max(0, index - EXCERPT_RADIUS)
    end = min(len(prose), index + EXCERPT_RADIUS)
    snippet = " ".join(prose[start:end].split())

    return '"' + snippet + '"'


def find_violations(prose: str) -> list[str]:
    """Return one label per banned marker present, each with a short excerpt."""
    found: list[tuple[str, int]] = []

    for label, needle in (
        ("em dash (U+2014)", EM_DASH),
        ("en dash (U+2013)", EN_DASH),
        ("semicolon", ";"),
    ):
        index = prose.find(needle)
        if index != -1:
            found.append((label, index))

    for label, pattern in (("bold", BOLD_RE), ("italic", ITALIC_RE)):
        match = pattern.search(prose)
        if match:
            found.append((label, match.start()))

    return [label + " in " + _excerpt(prose, index) for label, index in found]


def reply_violations(text: str, displayed_fixes: frozenset[str] = frozenset()) -> list[str]:
    """The markers a reply still shows once the lines the display fixed are fixed here too.

    Args:
        displayed_fixes: the original text of every line the display fix changed on screen.
    """
    if displayed_fixes:
        text = _fix_displayed_lines(text, displayed_fixes)

    return find_violations(strip_code(text))


def _fix_displayed_lines(text: str, displayed_fixes: frozenset[str]) -> str:
    """Fix only the prose lines the display already showed fixed, and leave the rest."""
    lines = text.split("\n")
    fence = ""

    for index, line in enumerate(lines):
        code, fence = _step_fence(line, fence)

        if not code and line.rstrip("\r") in displayed_fixes:
            lines[index] = _fix_line(line)

    return "\n".join(lines)


def build_reason(violations: list[str], subagent: bool = False) -> str:
    return REASON_HEAD + ", ".join(violations) + (SUBAGENT_REASON_TAIL if subagent else REASON_TAIL)


def _is_subagent_stop(payload: dict[str, object]) -> bool:
    """Whether the stopping reply is a subagent's report rather than a reply on screen."""
    if payload.get("hook_event_name") == "SubagentStop":
        return True

    return any(isinstance(payload.get(key), str) and payload.get(key) for key in SUBAGENT_STOP_KEYS)


def _report(text: str) -> int:
    """Write the reason on stderr and deny, or stay silent and allow."""
    if not text.strip():
        return 0

    violations = reply_violations(text)

    if not violations:
        return 0

    sys.stderr.buffer.write(build_reason(violations).encode("utf-8"))
    sys.stderr.buffer.flush()

    return 2


def _stdin_text() -> str:
    """Decode stdin as UTF-8 explicitly, never through the system code page."""
    return sys.stdin.buffer.read().decode("utf-8", errors="replace")


def _text_mode() -> int:
    """Check raw prose from stdin, reporting on stderr with exit code 2."""
    try:
        return _report(_stdin_text())
    except Exception:
        return 0


def _speaks_contract(payload: dict[str, object]) -> bool:
    """Whether a runner envelope names a version this hook understands.

    A payload with no `contract` field is read as the current version.
    """
    version = payload.get("contract", max(CONTRACTS))

    return type(version) is int and version in CONTRACTS


def _runner_mode() -> int:
    """Check the envelope's prose, or fix the finished text part it carries."""
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict) or not _speaks_contract(payload):
            return 0

        if payload.get("event") == TEXT_EVENT:
            return _rewrite_text_part(payload)

        text = payload.get("assistant_text")

        if not isinstance(text, str):
            return 0

        return _report(text)
    except Exception:
        return 0


def _rewrite_text_part(payload: dict[str, object]) -> int:
    """Print the fixed text part for the plugin to store, or nothing."""
    text = payload.get("text")

    if not isinstance(text, str):
        return 0

    fixed = fix_prose(text)[0]

    if fixed != text:
        sys.stdout.write(json.dumps({"text": fixed}))

    return 0


def _reply_text(payload: dict[str, object]) -> str:
    """The finished reply, from the payload first and the transcript second.

    Claude Code and Codex both carry it in `last_assistant_message` on Stop
    and on SubagentStop, and Claude Code documents the transcript file as not
    guaranteed to hold the final message yet when Stop fires. The walk stays
    for a payload that carries the field empty or not at all, which includes
    every Copilot agentStop payload.
    """
    message = payload.get("last_assistant_message")

    if isinstance(message, str) and message.strip():
        return message

    return _transcript_text(payload)


def _transcript_text(payload: dict[str, object]) -> str:
    """Newest assistant prose in whichever transcript the payload names.

    On SubagentStop `transcript_path` is the parent session's file and
    `agent_transcript_path` is the subagent's own, so the subagent's file is
    read first whenever the payload carries one. Copilot's camelCase payload
    spells the field `transcriptPath`.
    """
    for key in ("agent_transcript_path", "transcript_path", "transcriptPath"):
        value = payload.get(key)

        if not isinstance(value, str) or not value:
            continue

        path = Path(value)

        if not path.is_file() or _names_another_session(payload, key, path):
            continue

        text = _last_assistant_text(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        )

        if text.strip():
            return text

    return ""


def _names_another_session(payload: dict[str, object], key: str, path: Path) -> bool:
    """Whether a Copilot agentStop names a session log that is not its own.

    The CLI keeps one log per session in a directory named after the session
    id. A subagent's agentStop carries the subagent's own id with the main
    session's log, and fires before the subagent's final reply is written
    there, so the newest prose in that log belongs to an earlier message.
    """
    session = payload.get("sessionId")

    return key == "transcriptPath" and isinstance(session, str) and bool(session) and path.parent.name != session


def _project_dir(payload: dict[str, object], fmt: str) -> Path | None:
    """The root of the project the session runs in, or None when unknown.

    Claude Code names the root in CLAUDE_PROJECT_DIR. Otherwise the payload's
    `cwd` is walked up to the nearest directory holding `.git`, because a
    session may start in a subdirectory.
    """
    named = os.environ.get("CLAUDE_PROJECT_DIR") if fmt == "claude" else None
    start = named or payload.get("cwd")

    if not isinstance(start, str) or not start:
        return None

    base = Path(start).resolve()

    for candidate in (base, *base.parents):
        if (candidate / ".git").exists():
            return candidate

    return base


def _wires_this_check(hooks: object, event: str) -> bool:
    """Whether a hooks table runs a file named like this one on `event`.

    Claude Code and Codex nest the entries in groups under `hooks`, and Copilot
    lists them flat under the event.
    """
    groups = hooks.get(event) if isinstance(hooks, dict) else None

    if not isinstance(groups, list):
        return False

    script = Path(__file__).name

    for group in groups:
        if not isinstance(group, dict):
            continue

        entries = group.get("hooks") if isinstance(group.get("hooks"), list) else [group]

        for entry in entries:
            if not isinstance(entry, dict):
                continue

            commands = (value for value in entry.values() if isinstance(value, str))

            if any(script in command for command in commands):
                return True

    return False


def _read_hooks_table(path: Path) -> object:
    if path.suffix == ".toml":
        import tomllib

        return tomllib.loads(path.read_text(encoding="utf-8")).get("hooks")

    return json.loads(path.read_text(encoding="utf-8")).get("hooks")


def _project_runs_its_own_copy(payload: dict[str, object], fmt: str) -> bool:
    """Whether this copy is a user-level install shadowed by a project wiring.

    False, which runs the check, whenever this copy lives inside the project
    or anything needed to decide cannot be read.
    """
    try:
        project = _project_dir(payload, fmt)

        if project is None or Path(__file__).resolve().is_relative_to(project):
            return False

        event = payload.get("hook_event_name")
        event = event if isinstance(event, str) and event else DEFAULT_EVENT.get(fmt, "Stop")

        for pattern in PROJECT_WIRING.get(fmt, ()):
            for path in sorted(project.glob(pattern)):
                if path.is_file() and _wires_this_check(_read_hooks_table(path), event):
                    return True
    except Exception:
        return False

    return False


def _borrowed_by_copilot(payload: dict[str, object], fmt: str) -> bool:
    """Whether the Copilot CLI is running the Claude Stop wiring it borrows.

    The CLI reads .claude/settings.json and hands a PascalCase Stop hook its
    VS Code compatible payload. The hooks reference documents that payload as
    carrying `stop_reason` and an ISO 8601 string `timestamp` and no
    `last_assistant_message`, while Claude Code's own Stop carries
    `last_assistant_message` and neither of the other two. All three must
    agree, so a Claude Code payload that gains one of those fields is still
    checked. The main agent's reply belongs to the agentStop wiring in
    .github/hooks/, so checking it here as well would block the same reply
    twice. Copilot's SubagentStop has no wiring of its own, so it is still
    checked here.
    """
    return (
        fmt == "claude"
        and payload.get("hook_event_name") == "Stop"
        and "stop_reason" in payload
        and isinstance(payload.get("timestamp"), str)
        and "last_assistant_message" not in payload
    )


def _stop_mode(fmt: str, display_fixed: bool) -> int:
    """Check the finished reply, reporting as Stop JSON on stdout with exit 0."""
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        if _borrowed_by_copilot(payload, fmt) or _project_runs_its_own_copy(payload, fmt):
            return 0

        if any(payload.get(flag) is True for flag in LOOP_FLAGS):
            _forget_blocks(payload)
            return 0

        text = _reply_text(payload)
        displayed_fixes = _take_displayed_fixes(payload) if display_fixed else frozenset()

        if not text.strip():
            return 0

        violations = reply_violations(text, displayed_fixes)

        if not violations:
            _forget_blocks(payload)
            return 0

        if not _count_block(payload):
            return 0

        sys.stdout.write(
            json.dumps({"decision": "block", "reason": build_reason(violations, _is_subagent_stop(payload))})
        )
    except Exception:
        return 0

    return 0


def _private_temp_dir(create: bool) -> str | None:
    """A temp directory only this user can write, or None when there is none.

    Created only when `create` is set, so a call that stores nothing leaves
    nothing behind.
    """
    base = os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
    owner = str(os.getuid()) if hasattr(os, "getuid") else os.environ.get("USERNAME", "")
    path = os.path.join(base, "agent-standards-" + UNSAFE_NAME_RE.sub("", owner))

    if create:
        os.makedirs(path, mode=0o700, exist_ok=True)
    elif not os.path.isdir(path):
        return path

    if hasattr(os, "getuid") and (os.path.islink(path) or os.lstat(path).st_uid != os.getuid()):
        return None

    return path


def _session_key(payload: dict[str, object]) -> str:
    """The payload's session id, reduced to a safe file name part, or "" for none."""
    for key in SESSION_KEYS:
        value = payload.get(key)

        if isinstance(value, str) and value:
            return UNSAFE_NAME_RE.sub("", value)

    return ""


def _state_path(payload: dict[str, object], template: str, create: bool = False) -> str | None:
    """Where this session keeps one kind of state, or None when nowhere is safe."""
    directory = payload.get("scratchpad_dir")

    if not isinstance(directory, str) or not directory:
        directory = _private_temp_dir(create)

    if directory is None:
        return None

    return os.path.join(directory, template.format(session=_session_key(payload) or "session"))


def _read_state(path: str) -> dict[str, object]:
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except FileNotFoundError:
        return {}

    return state if isinstance(state, dict) else {}


def _write_state(path: str, state: dict[str, object]) -> None:
    """Replace the state file whole, or remove it when nothing is left to keep."""
    if not state:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

        return

    staging = path + ".tmp"

    with open(staging, "w", encoding="utf-8") as handle:
        json.dump(state, handle)

    os.replace(staging, path)


def _count_block(payload: dict[str, object]) -> bool:
    """Record one more block in a row for this session, False once the cap is reached.

    A payload with no session id, or a session whose counter cannot be kept,
    blocks as before, bounded by the agent's own override after eight blocks
    in a row.
    """
    if not _session_key(payload):
        return True

    try:
        path = _state_path(payload, STOP_STATE_FILE, create=True)

        if path is None:
            return True

        blocks = _read_state(path).get("blocks")
        blocks = blocks if type(blocks) is int else 0

        if blocks >= MAX_CONSECUTIVE_BLOCKS:
            _write_state(path, {})
            return False

        _write_state(path, {"blocks": blocks + 1})
    except (OSError, ValueError):
        return True

    return True


def _forget_blocks(payload: dict[str, object]) -> None:
    """Reset the session's block counter, because this stop was allowed."""
    if not _session_key(payload):
        return

    try:
        path = _state_path(payload, STOP_STATE_FILE)

        if path is not None:
            _write_state(path, {})
    except OSError:
        pass


def _take_displayed_fixes(payload: dict[str, object]) -> frozenset[str]:
    """Every line the display fixed on screen in this session, and clear the record.

    The Stop payload names no message, and the display's message id cannot be
    matched to the transcript, so the lines of every recorded message count.
    Empty when the display never recorded anything, which checks the reply in
    full.
    """
    if not _session_key(payload):
        return frozenset()

    try:
        path = _state_path(payload, DISPLAY_STATE_FILE)

        if path is None:
            return frozenset()

        state = _read_state(path)
        fixed = state.pop("fixed", None)

        if not isinstance(fixed, dict):
            return frozenset()

        _write_state(path, state)
    except (OSError, ValueError):
        return frozenset()

    return frozenset(
        line
        for lines in fixed.values()
        if isinstance(lines, list)
        for line in lines
        if isinstance(line, str)
    )


def _open_fence(state: dict[str, object], payload: dict[str, object]) -> str:
    """The fence the previous batch of this message left open, "" for none."""
    record = state.get("fence")

    if not isinstance(record, dict) or record.get("message_id") != payload.get("message_id"):
        return ""

    fence = record.get("fence")

    return fence if isinstance(fence, str) and FENCE_RE.fullmatch(fence) else ""


def _changed_lines(delta: str, fixed: str) -> list[str]:
    """The original text of every line the fix changed, without a trailing CR."""
    return [
        original.rstrip("\r")
        for original, shown in zip(delta.split("\n"), fixed.split("\n"))
        if original != shown
    ]


def _next_display_state(
    state: dict[str, object], payload: dict[str, object], fence: str, changed: list[str]
) -> dict[str, object]:
    """The state after this batch: the fence still open, and the lines fixed per message."""
    message_id = payload.get("message_id")
    following: dict[str, object] = {}

    if fence and payload.get("final") is not True:
        following["fence"] = {"message_id": message_id, "fence": fence}

    fixed = state.get("fixed")
    fixed = dict(fixed) if isinstance(fixed, dict) else {}

    if changed and _session_key(payload) and isinstance(message_id, str) and message_id:
        earlier = fixed.pop(message_id, [])
        fixed[message_id] = (earlier if isinstance(earlier, list) else []) + changed

        while len(fixed) > FIXED_MESSAGE_CAP:
            fixed.pop(next(iter(fixed)))

    if fixed:
        following["fixed"] = fixed

    return following


def _display_mode(fmt: str) -> int:
    """Print the fixed batch as MessageDisplay output, or nothing to keep the original."""
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        delta = payload.get("delta")

        if not isinstance(delta, str) or not any(char in delta for char in DISPLAY_CHARS):
            return 0

        if _project_runs_its_own_copy(payload, fmt):
            return 0

        index = payload.get("index")
        continues = type(index) is int and index > 0
        path = _state_path(payload, DISPLAY_STATE_FILE)

        if path is None and continues:
            return 0

        try:
            state = _read_state(path) if path is not None else {}
        except ValueError:
            if continues:
                return 0

            state = {}

        before = _open_fence(state, payload) if continues else ""
        fixed, after = fix_prose(delta, before)
        following = _next_display_state(state, payload, after, _changed_lines(delta, fixed))

        if following != state:
            _store_display_state(payload, following)

        if fixed != delta:
            output = {"hookEventName": DISPLAY_EVENT, "displayContent": fixed}
            sys.stdout.write(json.dumps({"hookSpecificOutput": output}))
    except Exception:
        return 0

    return 0


def _store_display_state(payload: dict[str, object], state: dict[str, object]) -> None:
    """Keep the state, and leave the Stop check reading the whole reply when that fails."""
    try:
        path = _state_path(payload, DISPLAY_STATE_FILE, create=bool(state))

        if path is not None:
            _write_state(path, state)
    except OSError:
        pass


def _format(argv: list[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--format" and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith("--format="):
            return token.split("=", 1)[1]

    return ""


def main(argv: list[str]) -> int:
    if "--text" in argv:
        return _text_mode()

    fmt = _format(argv)

    if fmt == "plain":
        return _runner_mode()

    if "--display" in argv:
        return _display_mode(fmt or "claude")

    return _stop_mode(fmt or "claude", "--display-fixed" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
