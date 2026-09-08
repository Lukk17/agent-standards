#!/usr/bin/env python3
"""Blocks a reply whose prose carries banned formatting.

Strips fenced code blocks, inline code, link targets, bare URLs, table rows and
HTML entities, then blocks when what is left contains an em dash (U+2014), an
en dash (U+2013), a semicolon, bold, or italic. Bold and italic are matched as
paired delimiters in both spellings, `**text**` and `__text__` for bold,
`*text*` and `_text_` for italic, so a bullet marker, a multiplication sign and
a snake_case identifier are not mistaken for emphasis.

Three modes over the same detection:

Stop hook (default, or --format claude, or --format codex). Reads the Stop or
SubagentStop payload as JSON on stdin and takes the reply from
`last_assistant_message`, falling back to the transcript walk when the payload
carries no text. Blocking prints {"decision": "block", "reason": "..."} on
stdout and exits 0, a clean reply prints nothing. `stop_hook_active`
short-circuits the check so one forced rewrite cannot loop. Claude Code and
Codex both call it this way, and both document the same field on both events.

Runner (--format plain). The contract at
https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md
defines one envelope as JSON on stdin, prose taken from its `assistant_text`
field. Blocking prints the reason on stderr and exits 2. This is how the
OpenCode and Kilo Code plugin calls it, where the only blocking channel is a
failed tool call. The runner delivers each distinct text once per session, so
this mode does no de-duplication of its own.

Text (--text). Reads raw UTF-8 prose on stdin, same output shape as the runner
mode. For calling the check by hand.

Arguments are scanned by hand rather than with argparse, because argparse
exits 2 on a usage error and 2 is the deny code in the plain format.

Every failure path allows: a broken hook must never break a session.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Runner order. Formatting runs after the preflight gate, because a policy
# denial about the action being attempted outranks a note about prose that has
# already been sent.
HOOK_ORDER = 20

EM_DASH = "\u2014"
EN_DASH = "\u2013"

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
INLINE_CODE_RE = re.compile(r"``[^\n]+?``|`[^`\n]*`")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
BARE_URL_RE = re.compile(r"<?\b[a-z][a-z0-9+.-]*://[^\s>)\]]+>?", re.IGNORECASE)
TABLE_ROW_RE = re.compile(r"^\s*\|")
HTML_ENTITY_RE = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")

# Paired delimiters, both spellings. The opener may not be preceded by a word
# character or by another delimiter of the same kind, and the run may not start
# or end on whitespace, which is what separates emphasis from a `* ` bullet
# marker, an `a * b` multiplication, and a snake_case identifier.
BOLD_RE = re.compile(
    r"\*\*(?=\S)(?:[^*]|\*(?!\*))+?(?<=\S)\*\*|__(?=\S)(?:[^_]|_(?!_))+?(?<=\S)__"
)
# A run holding a slash is a path rather than emphasis, which is what keeps a
# sentence naming two unbackticked globs, `docs/*.md and tools/*.py`, from
# reading as one italic run between the two asterisks.
ITALIC_RE = re.compile(
    r"(?<![\w*])\*(?![\s*])[^*/\n]*?(?<![\s*])\*(?![\w*])"
    r"|(?<![\w_])_(?![\s_])[^_/\n]*?(?<![\s_])_(?![\w_])"
)

EXCERPT_RADIUS = 30

REASON_HEAD = "Formatting violation in your last reply. The prose contains: "

REASON_TAIL = (
    ". Rewrite the whole reply with none of them. Replace an em dash or en dash "
    "with a comma, a period, a colon, or parentheses. Replace a semicolon with a "
    "period or a comma, or split the sentence. Remove bold and italic. Output only "
    "the corrected reply."
)


def _last_assistant_text(lines: List[str]) -> str:
    """Return the text of the newest assistant message that carries any text.

    Assistant turns that hold only tool calls have no text. Skipping past them
    keeps the check on the prose the user actually reads.
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
        role = message.get("role") or entry.get("role") or entry.get("type")

        if role != "assistant":
            continue

        content = message.get("content", entry.get("content"))
        text = _content_text(content)

        if text.strip():
            return text

    return ""


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content

    if not isinstance(content, list):
        return ""

    parts: List[str] = []

    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            value = block.get("text")
            if isinstance(value, str):
                parts.append(value)

    return "\n".join(parts)


def strip_code(text: str) -> str:
    """Drop everything that is not prose the reader is meant to read as prose.

    Fenced blocks, table rows, inline code spans, link targets, bare URLs and
    HTML entities all go. Fences are matched by character and length, so a
    four-backtick wrapper around a three-backtick sample stays one block
    instead of splitting. A table row goes whole, because its cell separators
    and its entities are markup rather than punctuation, and `&amp;` ends in a
    semicolon that is not one.
    """
    kept: List[str] = []
    fence_char = ""
    fence_len = 0

    for line in text.splitlines():
        match = FENCE_RE.match(line)

        if match:
            marker = match.group(2)
            info = match.group(3).strip()

            if not fence_char:
                fence_char = marker[0]
                fence_len = len(marker)
                continue

            if marker[0] == fence_char and len(marker) >= fence_len and not info:
                fence_char = ""
                fence_len = 0

            continue

        if fence_char:
            continue

        if TABLE_ROW_RE.match(line):
            continue

        kept.append(line)

    prose = "\n".join(kept)
    prose = INLINE_CODE_RE.sub(" ", prose)
    prose = LINK_TARGET_RE.sub("]( )", prose)
    prose = BARE_URL_RE.sub(" ", prose)
    prose = HTML_ENTITY_RE.sub(" ", prose)

    return prose


def _excerpt(prose: str, index: int) -> str:
    start = max(0, index - EXCERPT_RADIUS)
    end = min(len(prose), index + EXCERPT_RADIUS)
    snippet = " ".join(prose[start:end].split())

    return '"' + snippet + '"'


def find_violations(prose: str) -> List[str]:
    """Return one label per banned marker present, each with a short excerpt."""
    found: List[Tuple[str, int]] = []

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


def build_reason(violations: List[str]) -> str:
    return REASON_HEAD + ", ".join(violations) + REASON_TAIL


def _report(text: str) -> int:
    """Write the reason on stderr and deny, or stay silent and allow."""
    if not text.strip():
        return 0

    violations = find_violations(strip_code(text))

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


def _runner_mode() -> int:
    """Check the envelope's assistant prose, reporting on stderr with exit 2."""
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        text = payload.get("assistant_text")

        if not isinstance(text, str):
            return 0

        return _report(text)
    except Exception:
        return 0


def _reply_text(payload: Dict[str, Any]) -> str:
    """The finished reply, from the payload first and the transcript second.

    Claude Code and Codex both carry it in `last_assistant_message` on Stop
    and on SubagentStop, and Claude Code documents the transcript file as not
    guaranteed to hold the final message yet when Stop fires. The walk stays
    only as the fallback for a payload that carries the field empty or not at
    all.
    """
    message = payload.get("last_assistant_message")

    if isinstance(message, str) and message.strip():
        return message

    return _transcript_text(payload)


def _transcript_text(payload: Dict[str, Any]) -> str:
    """Newest assistant prose in whichever transcript the payload names.

    On SubagentStop `transcript_path` is the parent session's file and
    `agent_transcript_path` is the subagent's own, so the subagent's file is
    read first whenever the payload carries one.
    """
    for key in ("agent_transcript_path", "transcript_path"):
        value = payload.get(key)

        if not isinstance(value, str) or not value:
            continue

        path = Path(value)

        if not path.is_file():
            continue

        text = _last_assistant_text(
            path.read_text(encoding="utf-8", errors="replace").splitlines()
        )

        if text.strip():
            return text

    return ""


def _stop_mode() -> int:
    """Check the finished reply, reporting as Stop JSON on stdout with exit 0."""
    try:
        payload = json.loads(_stdin_text() or "{}")

        if not isinstance(payload, dict):
            return 0

        if payload.get("stop_hook_active") is True:
            return 0

        text = _reply_text(payload)

        if not text.strip():
            return 0

        violations = find_violations(strip_code(text))

        if not violations:
            return 0

        sys.stdout.write(
            json.dumps({"decision": "block", "reason": build_reason(violations)})
        )
    except Exception:
        return 0

    return 0


def _format(argv: List[str]) -> str:
    for index, token in enumerate(argv):
        if token == "--format" and index + 1 < len(argv):
            return argv[index + 1]

        if token.startswith("--format="):
            return token.split("=", 1)[1]

    return ""


def main(argv: List[str]) -> int:
    if "--text" in argv:
        return _text_mode()

    if _format(argv) == "plain":
        return _runner_mode()

    return _stop_mode()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
