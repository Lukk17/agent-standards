#!/usr/bin/env python3
"""Shared preflight gate for every agent surface.

Reads one hook payload as JSON on stdin and decides whether a tool call may
proceed. Three rules:

A. The main thread may not write any file. It delegates the change to a
   subagent that owns the area. This covers the edit tools and the shell: a
   command is lexed and matched against the programs that write files, so
   reaching for sed, a redirection or a patch is not a way around the rule.
B. A subagent whose own definition declares no skills may not act. The caller
   spawns a specialist that declares its skills instead.
C. The main thread may not run a web fetch or web search tool directly, on
   the formats where that tool is known by name (currently Claude Code only,
   see RESEARCH_TOOLS). It spawns a subagent to do the research and report
   back instead.

Every rule above denies only once the caller is positively identified as the
main thread. A format whose payload carries nothing that could identify the
caller (currently Copilot, see _caller_identity) is left ungated rather than
guessed at: denying blind risks blocking a legitimate subagent as often as it
blocks the main thread, and an agent that cannot edit cannot work at all.

The output shape is picked with --format:

  claude, codex   PreToolUse JSON on stdout, exit 0
  copilot         flat permission JSON on stdout, exit 0
  plain           reason on stderr, exit 2

Claude Code, Codex and Copilot each call this script directly with their own
format. The plain format is the runner contract described at
https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md,
which the OpenCode and Kilo Code plugin uses: one envelope on stdin, exit 2 to
deny.

Allowing prints nothing and exits 0 in every format. Any parse error, missing
key, or unexpected payload also allows: a broken gate must never break a
session. The one deliberate exception is the repository-boundary helpers
(_resolves_inside_repo, _path_exists_in_repo): a path they cannot resolve
fails toward True, which denies rather than allows, because the whole point
of those helpers is to decide what Rule A protects.
"""

import argparse
import io
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, Dict, List, NamedTuple, Optional, TextIO, Tuple

# Runner order. The gate goes first: a policy denial about the action being
# attempted outranks a note about prose that has already been sent.
HOOK_ORDER = 10

EDIT_TOOLS = {
    "edit",
    "write",
    "multiedit",
    "notebookedit",
    "create",
    "update",
    "str_replace_editor",
    "apply_patch",
    "applypatch",
}

SHELL_TOOLS = {"bash", "shell", "powershell", "pwsh", "terminal", "run_command"}

# apply_patch carries no path key at all: Codex's own matcher in
# .codex/config.toml names it as a distinct tool from Edit/Write, and its
# call arguments are a patch body, not a file path (see AGENTS.md Defect 3).
APPLY_PATCH_TOOLS = {"apply_patch", "applypatch"}

PATH_KEYS = ("file_path", "filePath", "path", "notebook_path", "notebookPath")

COMMAND_KEYS = ("command", "cmd", "script")

# The two forms apply_patch's own custom diff format and a standard unified
# diff use to name the file a hunk applies to. The exact key Codex's payload
# uses to carry the patch body is not confirmed (see AGENTS.md Defect 3), so
# every string value in the tool call is searched rather than one named key.
_APPLY_PATCH_FILE_RE = re.compile(
    r"^\*\*\* (?:Update|Add) File: (?P<named>.+?)\s*$|^\+\+\+ b/(?P<unified>.+?)\s*$",
    re.MULTILINE,
)

# Formats whose payload names a fetch or search tool the gate recognises.
# Claude Code's tools are confirmed as WebFetch and WebSearch. Codex has no
# confirmed equivalent name (see AGENTS.md), so it stays out of this set
# until one is verified; adding it here is the whole follow-up once it is.
RESEARCH_FORMATS = frozenset({"claude"})
RESEARCH_TOOLS = {"webfetch", "websearch"}


class AgentTree(NamedTuple):
    directory: str
    extension: str


AGENT_TREES = (
    AgentTree(".claude/agents", ".md"),
    AgentTree(".agents/agents", ".md"),
    AgentTree(".codex/agents", ".toml"),
    AgentTree(".github/agents", ".agent.md"),
    AgentTree(".opencode/agents", ".md"),
    AgentTree(".kilo/agents", ".md"),
)

FRONT_MATTER_SKILLS_RE = re.compile(r"^skills:[ \t]*(.*)$")
SKILLS_HEADING_RE = re.compile(r"^#{1,6}[ \t]+.*\bskills\b", re.IGNORECASE)
LIST_ITEM_RE = re.compile(r"^[ \t]*[-*][ \t]+\S")

RULE_A_REASON = (
    "PREFLIGHT: the main thread may not write files directly. Delegate this "
    "change to a subagent that owns the area, name the skills it must load, and let "
    "it make the edit. Blocked target: {target}"
)

RULE_B_REASON = (
    "PREFLIGHT: subagent '{agent}' declares no skills in its definition, so it is not "
    "a specialist. Spawn a subagent that declares the skills the task needs and "
    "delegate the work to it."
)

RULE_C_REASON = (
    "PREFLIGHT: the main thread may not run web research directly. Spawn a "
    "subagent that owns the area to fetch or search and report back, then "
    "continue from its findings. Blocked tool: {tool}"
)


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _tool_name(payload: Dict[str, Any]) -> str:
    for key in ("tool_name", "toolName"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value.strip().lower()
    return ""


def _tool_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("tool_input", "toolArgs", "toolInput", "tool_args"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


# One of "subagent", "main_thread", or "unknown". "unknown" means this
# format's payload carries nothing that could tell a subagent from the main
# thread, so neither rule A, B nor C may fire: a positive identification is
# required to deny, per the module docstring.
_SUBAGENT = "subagent"
_MAIN_THREAD = "main_thread"
_UNKNOWN = "unknown"


def _caller_identity(payload: Dict[str, Any], fmt: str, flag: bool) -> str:
    if flag:
        return _SUBAGENT

    if fmt in ("claude", "codex"):
        # Both formats document agent_id as present only inside a subagent
        # call (see AGENTS.md "Required opening move"), so its absence here
        # positively identifies the main thread rather than leaving it unknown.
        agent_id = payload.get("agent_id")
        return _SUBAGENT if isinstance(agent_id, str) and agent_id.strip() else _MAIN_THREAD

    if fmt == "copilot":
        # Copilot's own preToolUse payload carries no agent_id equivalent,
        # and its wiring in .github/hooks/preflight.json never passes
        # --subagent, so this surface cannot identify the caller at all.
        return _UNKNOWN

    # "plain": the runner envelope contract (docs/hooks-contract.md) always
    # sets is_subagent explicitly, so it is authoritative here.
    return _SUBAGENT if payload.get("is_subagent") is True else _MAIN_THREAD


def _agent_type(payload: Dict[str, Any]) -> str:
    for key in ("agent_type", "agentType", "subagent_type", "agent"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _direct_target(tool_input: Dict[str, Any]) -> str:
    for key in PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _apply_patch_body(tool_input: Dict[str, Any]) -> str:
    """Every top-level string value in an apply_patch call, concatenated.

    The key that carries the patch text is not confirmed (see AGENTS.md
    Defect 3), so nothing is named; every string field is searched instead.
    """
    return "\n".join(value for value in tool_input.values() if isinstance(value, str))


def _apply_patch_candidates(tool_input: Dict[str, Any]) -> List[str]:
    """Every file path named in an apply_patch call's own file headers."""
    body = _apply_patch_body(tool_input)

    return [
        match.group("named") or match.group("unified")
        for match in _APPLY_PATCH_FILE_RE.finditer(body)
    ]


# Shell analysis. Rule A has to hold through the shell as well as through the
# edit tools, so a command is lexed the way a shell reads it (quotes,
# redirections, heredoc bodies, separators) and each resulting command is
# matched against a table of programs that write files. A regex over the raw
# string cannot do this: it misses `sed -i "s|a|b|" f.sh`, whose script holds
# the pipe character, and it fires on `git commit -m "fix > a.py"`, whose
# redirection is quoted prose.

_MAX_NESTING = 3

_QUOTED_LITERAL_RE = re.compile(r"""['"]([^'"]*)['"]""")
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")
_VERSIONED_TOOL_RE = re.compile(r"^(python|node|php|ruby|perl|awk|gawk)[0-9.]*$")
_SHORT_INPLACE_RE = re.compile(r"^-[A-Za-z]{0,3}i(?:\.[^\s]*)?$")

_ESCAPABLE = set(" \t\"'\\;|&<>()$`")

_SED_TOOLS = {"sed", "gsed", "ssed"}
_AWK_TOOLS = {"awk", "gawk", "mawk", "nawk"}
_PERLISH_TOOLS = {"perl", "ruby"}
_INPLACE_TOOLS = _SED_TOOLS | _AWK_TOOLS | _PERLISH_TOOLS

_SED_VALUE_FLAGS = {"-e", "--expression", "-f", "--file", "-l", "--line-length"}
_AWK_VALUE_FLAGS = {
    "-v",
    "--assign",
    "-f",
    "--file",
    "-F",
    "--field-separator",
    "-i",
    "--include",
    "--source",
}
_PERLISH_VALUE_FLAGS = {"-e", "-E", "-I", "-r", "-F", "-m", "-M"}

_INLINE_CODE_TOOLS = {
    "python",
    "py",
    "node",
    "nodejs",
    "bun",
    "deno",
    "ruby",
    "perl",
    "php",
}

_INLINE_CODE_FLAGS = ("-c", "--command", "-e", "--eval", "-p", "--print", "-r")

_WRITE_MODES = {
    "w",
    "wb",
    "wt",
    "w+",
    "w+b",
    "wb+",
    "a",
    "ab",
    "at",
    "a+",
    "a+b",
    "ab+",
    "x",
    "xb",
    "xt",
    "x+",
    "r+",
    "r+b",
    "rb+",
}

_INLINE_WRITE_RE = re.compile(
    r"\.write\s*\(|\bwrite_text\b|\bwrite_bytes\b|\bwritelines\b|\bwriteFile(?:Sync)?\b"
    r"|\bappendFile(?:Sync)?\b|\bcreateWriteStream\b|\bcopyFile(?:Sync)?\b"
    r"|\brename(?:Sync)?\b|\bunlink(?:Sync)?\b|\btruncate\b|\bshutil\.\w+"
    r"|\bos\.(?:remove|replace|rename|rmdir)\b|\bmkstemp\b|\bdump\s*\("
)

_COPY_TOOLS = {"cp", "mv", "install", "ln", "rsync", "copy", "move"}
_COPY_VALUE_FLAGS = {
    "-t",
    "--target-directory",
    "-S",
    "--suffix",
    "-m",
    "--mode",
    "-o",
    "--owner",
    "-g",
    "--group",
    "--backup",
    "-e",
    "--exclude",
}
_TRUNCATE_VALUE_FLAGS = {"-s", "--size", "-r", "--reference", "-o", "--io-blocks"}
_PATCH_VALUE_FLAGS = {
    "-p",
    "-i",
    "--input",
    "-o",
    "--output",
    "-d",
    "--directory",
    "-B",
    "--prefix",
    "-D",
    "-F",
    "-r",
    "--reject-file",
    "-z",
    "--suffix",
}
_PATCH_CHECK_FLAGS = {"--dry-run", "--check"}

_GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_GIT_TREE_SUBCOMMANDS = {"checkout", "restore"}
# Only checkout switches branches, so only checkout is ambiguous between a
# branch/revision and a pathspec. restore has no branch semantics at all: a
# bare restore operand is always a file, existing or not.
_GIT_AMBIGUOUS_SUBCOMMANDS = {"checkout"}
_GIT_PATCH_SUBCOMMANDS = {"apply", "am"}
_GIT_CHECKOUT_VALUE_FLAGS = {"-b", "-B", "-s", "--source", "--conflict", "--pathspec-from-file"}
_GIT_PATCH_CHECK_FLAGS = {"--check", "--stat", "--numstat", "--summary", "--dry-run"}
_WILDCARD_PATHSPECS = {".", "./", "*", ":/", "*.*"}

# The POSIX null device. Never a write target, in any shell, unconditionally.
_POSIX_NULL_DEVICE = "/dev/null"

# Windows null-device spellings. Only meaningful inside a PowerShell (or cmd)
# context: a POSIX shell treats "nul" or "$null" as an ordinary filename, so
# these are gated on the invoking tool being a PowerShell tool rather than
# always excluded. Without that gate, `rm nul` from Bash would silently
# discard a real repository file named nul instead of writing to it.
_WINDOWS_NULL_DEVICE_TOKENS = {"$null", "nul"}

_POSIX_SHELLS = {"sh", "bash", "zsh", "dash", "ash", "ksh", "busybox"}
_POWERSHELL_SHELLS = {"pwsh", "powershell"}
_SHELL_CODE_FLAGS = {"-c", "--command", "-command", "/c"}

_WRAPPER_TOOLS = {
    "sudo",
    "doas",
    "env",
    "command",
    "nohup",
    "exec",
    "stdbuf",
    "nice",
    "ionice",
    "time",
}
_DURATION_WRAPPERS = {"timeout", "gtimeout"}
_WRAPPER_VALUE_FLAGS = {"-u", "-g", "-p", "-C", "-n", "-k", "--signal", "-o", "-e", "-i"}
_XARGS_VALUE_FLAGS = {
    "-n",
    "-P",
    "-I",
    "-i",
    "-a",
    "-d",
    "-E",
    "-e",
    "-L",
    "-l",
    "-s",
    "--max-args",
    "--replace",
}

_FIND_EXEC_MARKERS = {"-exec", "-execdir", "-ok", "-okdir"}
_FIND_NAME_FLAGS = {"-name", "-iname", "-path", "-ipath", "-wholename", "-iwholename", "-regex"}

_PS_PATH_PARAMS = {
    "-path",
    "-literalpath",
    "-filepath",
    "-destination",
    "-target",
    "-newname",
    "-name",
}
_PS_VALUE_PARAMS = _PS_PATH_PARAMS | {
    "-value",
    "-encoding",
    "-itemtype",
    "-filter",
    "-include",
    "-exclude",
    "-erroraction",
    "-delimiter",
    "-stream",
    "-inputobject",
    "-width",
}
_PS_WRITE_CMDLETS = {
    "set-content",
    "add-content",
    "clear-content",
    "out-file",
    "new-item",
    "remove-item",
    "rename-item",
    "tee-object",
    "ac",
    "clc",
    "ni",
    "ri",
    "rni",
    "del",
    "erase",
}
_PS_COPY_CMDLETS = {"copy-item", "move-item", "cpi", "mi"}


class _ShellParseError(Exception):
    """The command cannot be lexed with confidence, so the gate allows."""


class ShellSegment(NamedTuple):
    argv: Tuple[str, ...]
    redirects: Tuple[str, ...]


def _read_double_quoted(text: str, index: int) -> Tuple[str, int]:
    index += 1
    out: List[str] = []

    while index < len(text):
        char = text[index]

        if char == '"':
            return "".join(out), index + 1

        if char == "\\" and index + 1 < len(text) and text[index + 1] in '"\\$`\n':
            if text[index + 1] != "\n":
                out.append(text[index + 1])
            index += 2
            continue

        out.append(char)
        index += 1

    raise _ShellParseError("unterminated double quote")


def _read_word(text: str, index: int) -> Tuple[str, int]:
    """Read one bare word, honouring quotes. Used for heredoc delimiters."""
    word = ""

    while index < len(text):
        char = text[index]

        if char in " \t\n;|&<>()":
            break

        if char == "'":
            close = text.find("'", index + 1)
            if close < 0:
                raise _ShellParseError("unterminated single quote")
            word += text[index + 1 : close]
            index = close + 1
            continue

        if char == '"':
            piece, index = _read_double_quoted(text, index)
            word += piece
            continue

        word += char
        index += 1

    return word, index


def _consume_heredocs(text: str, index: int, delimiters: List[str]) -> int:
    """Skip every pending heredoc body so it is never read as code."""
    while delimiters:
        delimiter = delimiters.pop(0)

        while index < len(text):
            end = text.find("\n", index)
            line = text[index:] if end < 0 else text[index:end]
            index = len(text) if end < 0 else end + 1

            if line.strip() == delimiter:
                break

    return index


def _lex(command: str) -> List[ShellSegment]:
    """Split a command into segments of argv plus redirection targets."""
    segments: List[ShellSegment] = []
    argv: List[str] = []
    redirects: List[str] = []
    heredocs: List[str] = []
    token = ""
    started = False
    pending = ""
    index = 0
    length = len(command)

    def flush() -> None:
        nonlocal token, started, pending

        if not started:
            return

        if pending == "redirect":
            redirects.append(token)
        elif pending == "dup":
            if not (token.isdigit() or token == "-"):
                redirects.append(token)
        elif pending != "discard":
            argv.append(token)

        token = ""
        started = False
        pending = ""

    def end_segment() -> None:
        nonlocal argv, redirects

        flush()

        if argv or redirects:
            segments.append(ShellSegment(tuple(argv), tuple(redirects)))

        argv = []
        redirects = []

    while index < length:
        char = command[index]

        if char == "'":
            close = command.find("'", index + 1)
            if close < 0:
                raise _ShellParseError("unterminated single quote")
            token += command[index + 1 : close]
            started = True
            index = close + 1
            continue

        if char == '"':
            piece, index = _read_double_quoted(command, index)
            token += piece
            started = True
            continue

        if char == "\\":
            follower = command[index + 1] if index + 1 < length else ""

            if follower == "\n":
                index += 2
                continue

            if follower and follower in _ESCAPABLE:
                token += follower
                started = True
                index += 2
                continue

            token += char
            started = True
            index += 1
            continue

        if char in " \t":
            flush()
            index += 1
            continue

        if char == "\n":
            end_segment()
            index = _consume_heredocs(command, index + 1, heredocs)
            continue

        if char == "#" and not started:
            end = command.find("\n", index)
            index = length if end < 0 else end
            continue

        if char in ";()":
            end_segment()
            index += 1
            continue

        if char == "&":
            if command.startswith("&>", index):
                flush()
                index += 3 if command.startswith("&>>", index) else 2
                pending = "redirect"
                continue

            end_segment()
            index += 2 if command.startswith("&&", index) else 1
            continue

        if char == "|":
            end_segment()
            index += 2 if command.startswith("||", index) else 1
            continue

        if char == ">":
            if started and token.isdigit():
                token = ""
                started = False

            flush()
            index += 1

            if index < length and command[index] == ">":
                index += 1
            if index < length and command[index] == "|":
                index += 1

            if index < length and command[index] == "&":
                index += 1
                pending = "dup"
            else:
                pending = "redirect"

            continue

        if char == "<":
            if started and token.isdigit():
                token = ""
                started = False

            flush()

            if command.startswith("<<<", index):
                index += 3
                pending = "discard"
                continue

            if command.startswith("<<", index):
                index += 2

                if index < length and command[index] == "-":
                    index += 1

                while index < length and command[index] in " \t":
                    index += 1

                delimiter, index = _read_word(command, index)

                if delimiter:
                    heredocs.append(delimiter)

                continue

            index += 1
            pending = "discard"
            continue

        token += char
        started = True
        index += 1

    end_segment()

    return segments


def _basename(token: str) -> str:
    name = token.replace("\\", "/").rsplit("/", 1)[-1].lower()

    if name.endswith(".exe"):
        name = name[:-4]

    return name


def _program_name(token: str) -> str:
    name = _basename(token)
    match = _VERSIONED_TOOL_RE.match(name)

    return match.group(1) if match else name


def _operands(tokens: List[str], value_flags: AbstractSet[str] = frozenset()) -> List[str]:
    """Positional operands, with flags and their separate values removed."""
    operands: List[str] = []
    index = 0
    literal = False

    while index < len(tokens):
        token = tokens[index]

        if literal:
            operands.append(token)
            index += 1
            continue

        if token == "--":
            literal = True
            index += 1
            continue

        if token.startswith("-") and len(token) > 1:
            if "=" not in token and token in value_flags:
                index += 2
                continue
            index += 1
            continue

        operands.append(token)
        index += 1

    return operands


def _sourced(candidates: List[str], powershell: bool = False) -> List[str]:
    return [candidate for candidate in candidates if _is_write_target(candidate, powershell)]


def _inplace_targets(name: str, tokens: List[str], powershell: bool = False) -> List[str]:
    """Files an in-place editor rewrites, in every spelling of the flag."""
    flags = tokens[1:]

    if name in _AWK_TOOLS:
        inplace = "inplace" in flags or any(flag.endswith("=inplace") for flag in flags)
        value_flags = _AWK_VALUE_FLAGS
        script_is_first = not any(flag == "-f" or flag.startswith("--file") for flag in flags)
    else:
        inplace = any(
            flag in ("--in-place", "--inplace")
            or flag.startswith("--in-place=")
            or _SHORT_INPLACE_RE.match(flag)
            for flag in flags
        )

        if name in _PERLISH_TOOLS:
            value_flags = _PERLISH_VALUE_FLAGS
            script_is_first = not any(flag in ("-e", "-E") for flag in flags)
        else:
            value_flags = _SED_VALUE_FLAGS
            script_is_first = not any(
                flag in ("-e", "-f")
                or flag.startswith("--expression")
                or flag.startswith("--file")
                for flag in flags
            )

    if not inplace:
        return []

    operands = _operands(flags, value_flags)

    if script_is_first and operands:
        operands = operands[1:]

    return _sourced(operands, powershell)


def _inline_code(tokens: List[str]) -> str:
    for index, token in enumerate(tokens[1:], start=1):
        if token in _INLINE_CODE_FLAGS and index + 1 < len(tokens):
            return tokens[index + 1]

        for flag in _INLINE_CODE_FLAGS:
            if token.startswith(flag + "="):
                return token[len(flag) + 1 :]

    return ""


def _inline_code_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Paths an inline -c or -e program opens for writing."""
    code = _inline_code(tokens)

    if not code:
        return []

    literals = _QUOTED_LITERAL_RE.findall(code)
    writes = bool(_INLINE_WRITE_RE.search(code)) or any(item in _WRITE_MODES for item in literals)

    if not writes:
        return []

    return _sourced(literals, powershell)


def _tee_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:]), powershell)


def _copy_destinations(sources: List[str], destination: str) -> List[str]:
    if not destination:
        return []

    if destination.endswith(("/", "\\")) or destination in (".", ".."):
        return [PurePosixPath(source.replace("\\", "/")).name for source in sources]

    return [destination]


def _copy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    directory = ""

    for index, token in enumerate(tokens):
        if token in ("-t", "--target-directory") and index + 1 < len(tokens):
            directory = tokens[index + 1]
        elif token.startswith("--target-directory="):
            directory = token.split("=", 1)[1]

    operands = _operands(tokens[1:], _COPY_VALUE_FLAGS)

    if directory:
        return _sourced(_copy_destinations(operands, directory.rstrip("/\\") + "/"), powershell)

    if len(operands) < 2:
        return []

    return _sourced(_copy_destinations(operands[:-1], operands[-1]), powershell)


def _truncate_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:], _TRUNCATE_VALUE_FLAGS), powershell)


def _dd_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced([token[3:] for token in tokens[1:] if token.startswith("of=")], powershell)


def _remove_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:]), powershell)


def _patch_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """A patch writes whatever the diff says, so only a check run is allowed."""
    flags = tokens[1:]

    if any(flag in _PATCH_CHECK_FLAGS for flag in flags):
        return []

    named = _sourced(_operands(flags, _PATCH_VALUE_FLAGS), powershell)

    return named or [_basename(tokens[0])]


def _git_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token in _GIT_VALUE_FLAGS:
            index += 2
            continue

        if token.startswith("-"):
            index += 1
            continue

        break

    if index >= len(tokens):
        return []

    subcommand = tokens[index].lower()
    rest = tokens[index + 1 :]

    if subcommand in _GIT_PATCH_SUBCOMMANDS:
        if any(flag in _GIT_PATCH_CHECK_FLAGS for flag in rest):
            return []

        return ["git " + subcommand]

    if subcommand in _GIT_TREE_SUBCOMMANDS:
        if "--staged" in rest and "--worktree" not in rest and "-W" not in rest:
            return []

        if subcommand in _GIT_AMBIGUOUS_SUBCOMMANDS:
            return _checkout_targets(rest, powershell)

        return _sourced(_operands(rest, _GIT_CHECKOUT_VALUE_FLAGS), powershell)

    return []


def _checkout_targets(rest: List[str], powershell: bool = False) -> List[str]:
    """git checkout is ambiguous only with a single bare operand and no --:
    the same bare word can switch to a branch or revert a file. With two or
    more operands and no --, git's own rule removes the ambiguity instead:
    operand zero is always a tree-ish and every operand after it is always a
    pathspec, so `git checkout HEAD~1 tools/gen.py` writes that file
    unconditionally even when it does not currently exist in the working
    tree. What follows -- is unconditionally a pathspec in every case. A
    lone bare operand (with no -- and no second operand) counts only when it
    is a git magic pathspec (see _WILDCARD_PATHSPECS) or resolves to a path
    that actually exists, so `git checkout master` is read as the branch it
    is rather than a file write.
    """
    if "--" in rest:
        split = rest.index("--")
        candidates = _operands(rest[:split], _GIT_CHECKOUT_VALUE_FLAGS)
        pathspecs = list(rest[split + 1 :])
    else:
        candidates = _operands(rest, _GIT_CHECKOUT_VALUE_FLAGS)
        pathspecs = []

    if not pathspecs and len(candidates) >= 2:
        return _sourced(candidates[1:], powershell)

    ambiguous = [
        candidate
        for candidate in candidates
        if candidate in _WILDCARD_PATHSPECS or _path_exists_in_repo(candidate)
    ]

    return _sourced(pathspecs + ambiguous, powershell)


def _powershell_split(tokens: List[str]) -> Tuple[List[str], List[str]]:
    """Split a cmdlet call into path-parameter values and positional values."""
    paths: List[str] = []
    positional: List[str] = []
    index = 1

    while index < len(tokens):
        token = tokens[index]
        lowered = token.lower()

        if lowered.startswith("-") and len(lowered) > 1:
            if lowered in _PS_VALUE_PARAMS and index + 1 < len(tokens):
                if lowered in _PS_PATH_PARAMS:
                    paths.append(tokens[index + 1])
                index += 2
                continue

            index += 1
            continue

        positional.append(token)
        index += 1

    return paths, positional


def _powershell_write_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    paths, positional = _powershell_split(tokens)

    return _sourced(paths + positional, powershell)


def _powershell_copy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    paths, positional = _powershell_split(tokens)
    operands = paths + positional

    if len(operands) < 2:
        return _sourced(operands, powershell)

    return _sourced(_copy_destinations(operands[:-1], operands[-1]), powershell)


_WRITE_HANDLERS = {
    "tee": _tee_targets,
    "truncate": _truncate_targets,
    "dd": _dd_targets,
    "rm": _remove_targets,
    "git": _git_targets,
    "patch": _patch_targets,
    "gpatch": _patch_targets,
}
_WRITE_HANDLERS.update({name: _copy_targets for name in _COPY_TOOLS})
_WRITE_HANDLERS.update({name: _powershell_write_targets for name in _PS_WRITE_CMDLETS})
_WRITE_HANDLERS.update({name: _powershell_copy_targets for name in _PS_COPY_CMDLETS})


def _strip_wrappers(tokens: List[str]) -> List[str]:
    """Drop leading assignments and wrappers such as sudo, env, timeout, xargs."""
    rest = list(tokens)

    for _ in range(2 * _MAX_NESTING):
        while rest and _ASSIGNMENT_RE.match(rest[0]):
            rest.pop(0)

        if not rest:
            return rest

        name = _basename(rest[0])

        if name in _WRAPPER_TOOLS or name in _DURATION_WRAPPERS or name == "xargs":
            value_flags = _XARGS_VALUE_FLAGS if name == "xargs" else _WRAPPER_VALUE_FLAGS
            rest.pop(0)

            while rest and rest[0].startswith("-") and len(rest[0]) > 1:
                flag = rest.pop(0)
                if flag in value_flags and rest:
                    rest.pop(0)

            if name in _DURATION_WRAPPERS and rest:
                rest.pop(0)

            continue

        return rest

    return rest


def _nested_shell_code(name: str, tokens: List[str]) -> Optional[str]:
    if name not in _POSIX_SHELLS and name not in _POWERSHELL_SHELLS:
        return None

    for index, token in enumerate(tokens[1:], start=1):
        if token.lower() in _SHELL_CODE_FLAGS and index + 1 < len(tokens):
            return tokens[index + 1]

    return None


def _find_targets(tokens: List[str], depth: int, powershell: bool = False) -> List[str]:
    """Files rewritten by find -exec, with {} standing in for the -name pattern."""
    patterns = [
        tokens[index + 1]
        for index, token in enumerate(tokens)
        if token in _FIND_NAME_FLAGS and index + 1 < len(tokens)
    ]
    targets: List[str] = []

    for index, token in enumerate(tokens):
        if token not in _FIND_EXEC_MARKERS:
            continue

        command: List[str] = []

        for item in tokens[index + 1 :]:
            if item in (";", "+"):
                break
            command.append(item)

        if not command:
            continue

        for pattern in patterns or [""]:
            expanded = [pattern if item == "{}" else item for item in command]
            targets += _segment_targets(expanded, depth + 1, powershell)

    return targets


def _segment_targets(tokens: List[str], depth: int, powershell: bool = False) -> List[str]:
    rest = _strip_wrappers(tokens)

    if not rest or depth > _MAX_NESTING:
        return []

    name = _program_name(rest[0])
    nested = _nested_shell_code(name, rest)

    if nested is not None:
        # A nested shell invocation is judged by its own name, not inherited
        # from the outer one: `bash -c "pwsh -Command '...'"` must switch the
        # null-device gate on for the nested segment even though the outer
        # tool was Bash, and the reverse must switch it back off.
        return _command_targets(nested, depth + 1, name in _POWERSHELL_SHELLS)

    if name == "find":
        return _find_targets(rest, depth, powershell)

    targets: List[str] = []

    if name in _INPLACE_TOOLS:
        targets += _inplace_targets(name, rest, powershell)

    if name in _INLINE_CODE_TOOLS:
        targets += _inline_code_targets(rest, powershell)

    handler = _WRITE_HANDLERS.get(name)

    if handler is not None:
        targets += handler(rest, powershell)

    return targets


def _command_targets(command: str, depth: int = 0, powershell: bool = False) -> List[str]:
    """Every write target this command touches, as far as the text reveals it."""
    if depth > _MAX_NESTING:
        return []

    targets: List[str] = []

    for segment in _lex(command):
        targets += _sourced(list(segment.redirects), powershell)

        if segment.argv:
            targets += _segment_targets(list(segment.argv), depth, powershell)

    return targets


def _is_null_device(target: str, powershell: bool = False) -> bool:
    normalized = target.strip().lower()

    if normalized == _POSIX_NULL_DEVICE:
        return True

    return powershell and normalized in _WINDOWS_NULL_DEVICE_TOKENS


def _resolves_inside_repo(target: str) -> bool:
    """True when target resolves inside the repository boundary.

    Rule A protects this repository, not the rest of the filesystem. Every
    wiring is supposed to cd into the project root before invoking the gate
    (see AGENTS.md "Required opening move"), and that guarantee has broken
    silently once before, which would turn every file above a stray working
    directory into a writable target. A relative path is therefore resolved
    against, and checked against, every root in _roots() (the gate's
    invocation directory and the gate's own on-disk location two parents up,
    the same two-root treatment _read_agent_definition already uses), and it
    counts as inside when it resolves inside any one of them. A `cd` inside
    the command itself is not simulated, and an unresolvable path fails
    toward True: failing safe here means denying, not allowing.
    """
    path = Path(target.replace("\\", "/"))

    for root in _roots():
        try:
            resolved = (path if path.is_absolute() else (root / path)).resolve(strict=False)
        except (OSError, ValueError):
            return True

        if resolved.is_relative_to(root):
            return True

    return False


def _path_exists_in_repo(candidate: str) -> bool:
    """True when a bare git checkout/restore operand names a path that
    actually exists in any repository root (see _roots()), the one case
    where such an operand is unambiguously a file rather than a branch or
    revision. An unresolvable path fails toward True for the same reason as
    _resolves_inside_repo.
    """
    path = Path(candidate.replace("\\", "/"))

    for root in _roots():
        try:
            if (path if path.is_absolute() else (root / path)).resolve(strict=False).exists():
                return True
        except (OSError, ValueError):
            return True

    return False


def _is_write_target(target: str, powershell: bool = False) -> bool:
    """True for any concrete file path inside the repository, with no
    exemption by extension.

    Rule A denies a main-thread write of any file inside this repository,
    documentation and configuration included: see AGENTS.md "Required
    opening move" for why the earlier per-extension exemption was removed,
    and for why the check stops at the repository boundary and never treats
    the null device as a write.
    """
    if not target:
        return False

    if _is_null_device(target, powershell):
        return False

    if target in _WILDCARD_PATHSPECS:
        return True

    return _resolves_inside_repo(target)


def _roots() -> List[Path]:
    roots: List[Path] = []

    for candidate in (Path.cwd(), Path(__file__).resolve().parents[2]):
        resolved = candidate.resolve()
        if resolved not in roots:
            roots.append(resolved)

    return roots


def _read_agent_definition(agent_type: str) -> Optional[str]:
    if not agent_type or "/" in agent_type or "\\" in agent_type or ".." in agent_type:
        return None

    for root in _roots():
        for tree in AGENT_TREES:
            path = root / tree.directory / (agent_type + tree.extension)
            if path.is_file():
                return path.read_text(encoding="utf-8", errors="replace")

    return None


def _front_matter_end(lines: List[str]) -> int:
    """Index of the closing front-matter marker, or 0 when there is none."""
    if not lines or lines[0].strip() != "---":
        return 0

    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return index

    return 0


def _front_matter_declares_skills(lines: List[str], end: int) -> bool:
    for index in range(1, end):
        match = FRONT_MATTER_SKILLS_RE.match(lines[index])
        if not match:
            continue

        inline = match.group(1).strip()
        if inline and inline not in ("[]", "~", "null", "''", '""'):
            return True

        for follower in lines[index + 1 : end]:
            stripped = follower.strip()
            if not stripped:
                continue
            if follower[:1] not in (" ", "\t", "-"):
                break
            if stripped.startswith("- ") and stripped[2:].strip():
                return True
            break

        return False

    return False


def _body_declares_skills(lines: List[str], start: int) -> bool:
    """True when a body section headed 'skills' lists at least one entry.

    The generated OpenCode-format definitions carry no front matter key. They
    name their skills under a `## Preloaded skills` heading instead.
    """
    in_section = False

    for line in lines[start:]:
        if line.startswith("#"):
            in_section = bool(SKILLS_HEADING_RE.match(line))
            continue

        if in_section and LIST_ITEM_RE.match(line):
            return True

    return False


def _declares_skills(text: str) -> bool:
    lines = text.splitlines()
    end = _front_matter_end(lines)

    if _front_matter_declares_skills(lines, end):
        return True

    return _body_declares_skills(lines, end + 1 if end else 0)


def _decide(payload: Dict[str, Any], fmt: str, subagent_flag: bool) -> Optional[str]:
    """Return a deny reason, or None to allow."""
    identity = _caller_identity(payload, fmt, subagent_flag)

    if identity == _UNKNOWN:
        return None

    if identity == _SUBAGENT:
        agent_type = _agent_type(payload)
        definition = _read_agent_definition(agent_type)

        if definition is None:
            return None

        if _declares_skills(definition):
            return None

        return RULE_B_REASON.format(agent=agent_type)

    tool = _tool_name(payload)
    tool_input = _tool_input(payload)

    if fmt in RESEARCH_FORMATS and tool in RESEARCH_TOOLS:
        return RULE_C_REASON.format(tool=tool)

    if tool in EDIT_TOOLS:
        target = _direct_target(tool_input)

        if not target and tool in APPLY_PATCH_TOOLS:
            candidates = _apply_patch_candidates(tool_input)

            if not candidates:
                # No path key, and no file header the gate could read out of
                # the patch body either: deny rather than trust an edit tool
                # whose write target the gate cannot resolve, per AGENTS.md
                # Defect 3.
                return RULE_A_REASON.format(target="apply_patch (unreadable patch body)")

            write_targets = _sourced(candidates)

            if write_targets:
                return RULE_A_REASON.format(target=write_targets[0])

            return None

        if _is_write_target(target):
            return RULE_A_REASON.format(target=target)
        return None

    if tool in SHELL_TOOLS:
        command = ""
        for key in COMMAND_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value.strip():
                command = value
                break

        if not command:
            return None

        try:
            targets = _command_targets(command, powershell=tool in _POWERSHELL_SHELLS)
        except _ShellParseError:
            return None

        if targets:
            return RULE_A_REASON.format(target=targets[0])

    return None


def _emit(reason: str, fmt: str, real_stderr: Optional[TextIO] = None) -> int:
    if fmt in ("claude", "codex"):
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        sys.stdout.write(json.dumps(payload))
        return 0

    if fmt == "copilot":
        payload = {"permissionDecision": "deny", "permissionDecisionReason": reason}
        sys.stdout.write(json.dumps(payload))
        return 0

    (real_stderr if real_stderr is not None else sys.stderr).write(reason)
    return 2


def _parse_args(argv: Optional[List[str]]) -> Tuple[str, bool]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        required=True,
        choices=("claude", "codex", "copilot", "plain"),
    )
    parser.add_argument("--subagent", action="store_true")
    args, _unknown = parser.parse_known_args(argv)

    return args.format, args.subagent


def main(argv: Optional[List[str]] = None) -> int:
    real_stderr = sys.stderr
    sys.stderr = io.StringIO()

    try:
        try:
            fmt, subagent_flag = _parse_args(argv)
        except SystemExit:
            return 0

        try:
            raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
            payload = _as_dict(json.loads(raw or "{}"))
            reason = _decide(payload, fmt, subagent_flag)
        except Exception:
            return 0

        if not reason:
            return 0

        try:
            return _emit(reason, fmt, real_stderr)
        except Exception:
            return 0
    finally:
        sys.stderr = real_stderr


if __name__ == "__main__":
    sys.exit(main())
