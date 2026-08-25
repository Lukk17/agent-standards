#!/usr/bin/env python3
"""Blocks a reply whose prose carries banned formatting.

Strips fenced code blocks, inline code, and link targets, then blocks when what
is left contains an em dash (U+2014), an en dash (U+2013), a semicolon, or a
bold marker.

Two modes over the same detection:

Stop hook (default). Reads the Stop payload as JSON on stdin and pulls the last
assistant message out of the transcript. Blocking prints
{"decision": "block", "reason": "..."} on stdout and exits 0, a clean reply
prints nothing. `stop_hook_active` short-circuits the check so one forced
rewrite cannot loop.

Text (--text). Reads raw UTF-8 prose on stdin. Blocking prints the reason on
stderr and exits 2, a clean reply prints nothing and exits 0. This is the mode
the OpenCode and Kilo Code plugin uses, where the only blocking channel is a
failed tool call.

Every failure path allows: a broken hook must never break a session.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, List, Tuple

EM_DASH = "\u2014"
EN_DASH = "\u2013"

FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
INLINE_CODE_RE = re.compile(r"``[^\n]+?``|`[^`\n]*`")
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
BARE_URL_RE = re.compile(r"<?\b[a-z][a-z0-9+.-]*://[^\s>)\]]+>?", re.IGNORECASE)
BOLD_RE = re.compile(r"\*\*")

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
    """Drop fenced blocks, inline code spans, link targets, and bare URLs.

    Fences are matched by character and length, so a four-backtick wrapper
    around a three-backtick sample stays one block instead of splitting.
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

        kept.append(line)

    prose = "\n".join(kept)
    prose = INLINE_CODE_RE.sub(" ", prose)
    prose = LINK_TARGET_RE.sub("]( )", prose)
    prose = BARE_URL_RE.sub(" ", prose)

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

    bold = BOLD_RE.search(prose)
    if bold:
        found.append(("bold", bold.start()))

    return [label + " in " + _excerpt(prose, index) for label, index in found]


def build_reason(violations: List[str]) -> str:
    return REASON_HEAD + ", ".join(violations) + REASON_TAIL


def _text_mode() -> int:
    """Check raw prose from stdin, reporting on stderr with exit code 2."""
    try:
        text = sys.stdin.buffer.read().decode("utf-8", errors="replace")

        if not text.strip():
            return 0

        violations = find_violations(strip_code(text))

        if not violations:
            return 0

        sys.stderr.buffer.write(build_reason(violations).encode("utf-8"))
        sys.stderr.buffer.flush()

        return 2
    except Exception:
        return 0


def main(argv: List[str]) -> int:
    if "--text" in argv:
        return _text_mode()

    try:
        payload = json.loads(sys.stdin.read() or "{}")

        if not isinstance(payload, dict):
            return 0

        if payload.get("stop_hook_active") is True:
            return 0

        transcript = payload.get("transcript_path")

        if not isinstance(transcript, str) or not transcript:
            return 0

        path = Path(transcript)

        if not path.is_file():
            return 0

        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        text = _last_assistant_text(lines)

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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
