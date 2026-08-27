#!/usr/bin/env python3
"""Shared preflight gate for every agent surface.

Reads one hook payload as JSON on stdin and decides whether a tool call may
proceed. Two rules:

A. The main thread may not edit source files. It delegates the change to a
   subagent that owns the area. This covers the edit tools and the shell: a
   command is lexed and matched against the programs that write files, so
   reaching for sed, a redirection or a patch is not a way around the rule.
B. A subagent whose own definition declares no skills may not act. The caller
   spawns a specialist that declares its skills instead.

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
session.
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

PATH_KEYS = ("file_path", "filePath", "path", "notebook_path", "notebookPath")

COMMAND_KEYS = ("command", "cmd", "script")

NON_SOURCE_SUFFIXES = {
    ".md",
    ".markdown",
    ".txt",
    ".json",
    ".jsonc",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
}

NON_SOURCE_NAMES = {
    ".env.example",
    ".gitignore",
    ".gitattributes",
    "license",
}

CODE_SUFFIXES = {
    ".py",
    ".pyi",
    ".ipynb",
    ".js",
    ".mjs",
    ".cjs",
    ".jsx",
    ".ts",
    ".tsx",
    ".mts",
    ".cts",
    ".vue",
    ".svelte",
    ".java",
    ".kt",
    ".kts",
    ".scala",
    ".groovy",
    ".gradle",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".fs",
    ".c",
    ".h",
    ".cc",
    ".hh",
    ".cpp",
    ".hpp",
    ".m",
    ".mm",
    ".swift",
    ".dart",
    ".lua",
    ".pl",
    ".r",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".psm1",
    ".psd1",
    ".tf",
    ".proto",
    ".graphql",
    ".gql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
}


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
    "PREFLIGHT: the main thread may not edit source files directly. Delegate this "
    "change to a subagent that owns the area, name the skills it must load, and let "
    "it make the edit. Blocked target: {target}"
)

RULE_B_REASON = (
    "PREFLIGHT: subagent '{agent}' declares no skills in its definition, so it is not "
    "a specialist. Spawn a subagent that declares the skills the task needs and "
    "delegate the work to it."
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


def _is_subagent(payload: Dict[str, Any], fmt: str, flag: bool) -> bool:
    if fmt in ("claude", "codex"):
        agent_id = payload.get("agent_id")
        return isinstance(agent_id, str) and bool(agent_id.strip())

    if flag:
        return True

    return payload.get("is_subagent") is True


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
_GIT_PATCH_SUBCOMMANDS = {"apply", "am"}
_GIT_CHECKOUT_VALUE_FLAGS = {"-b", "-B", "-s", "--source", "--conflict", "--pathspec-from-file"}
_GIT_PATCH_CHECK_FLAGS = {"--check", "--stat", "--numstat", "--summary", "--dry-run"}
_WILDCARD_PATHSPECS = {".", "./", "*", ":/", "*.*"}

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


def _sourced(candidates: List[str]) -> List[str]:
    return [candidate for candidate in candidates if _is_source(candidate)]


def _inplace_targets(name: str, tokens: List[str]) -> List[str]:
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

    return _sourced(operands)


def _inline_code(tokens: List[str]) -> str:
    for index, token in enumerate(tokens[1:], start=1):
        if token in _INLINE_CODE_FLAGS and index + 1 < len(tokens):
            return tokens[index + 1]

        for flag in _INLINE_CODE_FLAGS:
            if token.startswith(flag + "="):
                return token[len(flag) + 1 :]

    return ""


def _inline_code_targets(tokens: List[str]) -> List[str]:
    """Paths an inline -c or -e program opens for writing."""
    code = _inline_code(tokens)

    if not code:
        return []

    literals = _QUOTED_LITERAL_RE.findall(code)
    writes = bool(_INLINE_WRITE_RE.search(code)) or any(item in _WRITE_MODES for item in literals)

    if not writes:
        return []

    return _sourced(literals)


def _tee_targets(tokens: List[str]) -> List[str]:
    return _sourced(_operands(tokens[1:]))


def _copy_destinations(sources: List[str], destination: str) -> List[str]:
    if not destination:
        return []

    if destination.endswith(("/", "\\")) or destination in (".", ".."):
        return [PurePosixPath(source.replace("\\", "/")).name for source in sources]

    return [destination]


def _copy_targets(tokens: List[str]) -> List[str]:
    directory = ""

    for index, token in enumerate(tokens):
        if token in ("-t", "--target-directory") and index + 1 < len(tokens):
            directory = tokens[index + 1]
        elif token.startswith("--target-directory="):
            directory = token.split("=", 1)[1]

    operands = _operands(tokens[1:], _COPY_VALUE_FLAGS)

    if directory:
        return _sourced(_copy_destinations(operands, directory.rstrip("/\\") + "/"))

    if len(operands) < 2:
        return []

    return _sourced(_copy_destinations(operands[:-1], operands[-1]))


def _truncate_targets(tokens: List[str]) -> List[str]:
    return _sourced(_operands(tokens[1:], _TRUNCATE_VALUE_FLAGS))


def _dd_targets(tokens: List[str]) -> List[str]:
    return _sourced([token[3:] for token in tokens[1:] if token.startswith("of=")])


def _remove_targets(tokens: List[str]) -> List[str]:
    return _sourced(_operands(tokens[1:]))


def _patch_targets(tokens: List[str]) -> List[str]:
    """A patch writes whatever the diff says, so only a check run is allowed."""
    flags = tokens[1:]

    if any(flag in _PATCH_CHECK_FLAGS for flag in flags):
        return []

    named = _sourced(_operands(flags, _PATCH_VALUE_FLAGS))

    return named or [_basename(tokens[0])]


def _git_targets(tokens: List[str]) -> List[str]:
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

        operands = _operands(rest, _GIT_CHECKOUT_VALUE_FLAGS)
        wildcards = [operand for operand in operands if operand in _WILDCARD_PATHSPECS]

        return _sourced(operands) + ["git " + subcommand + " " + item for item in wildcards]

    return []


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


def _powershell_write_targets(tokens: List[str]) -> List[str]:
    paths, positional = _powershell_split(tokens)

    return _sourced(paths + positional)


def _powershell_copy_targets(tokens: List[str]) -> List[str]:
    paths, positional = _powershell_split(tokens)
    operands = paths + positional

    if len(operands) < 2:
        return _sourced(operands)

    return _sourced(_copy_destinations(operands[:-1], operands[-1]))


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


def _find_targets(tokens: List[str], depth: int) -> List[str]:
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
            targets += _segment_targets(expanded, depth + 1)

    return targets


def _segment_targets(tokens: List[str], depth: int) -> List[str]:
    rest = _strip_wrappers(tokens)

    if not rest or depth > _MAX_NESTING:
        return []

    name = _program_name(rest[0])
    nested = _nested_shell_code(name, rest)

    if nested is not None:
        return _command_targets(nested, depth + 1)

    if name == "find":
        return _find_targets(rest, depth)

    targets: List[str] = []

    if name in _INPLACE_TOOLS:
        targets += _inplace_targets(name, rest)

    if name in _INLINE_CODE_TOOLS:
        targets += _inline_code_targets(rest)

    handler = _WRITE_HANDLERS.get(name)

    if handler is not None:
        targets += handler(rest)

    return targets


def _command_targets(command: str, depth: int = 0) -> List[str]:
    """Every source path this command writes, as far as the text reveals it."""
    if depth > _MAX_NESTING:
        return []

    targets: List[str] = []

    for segment in _lex(command):
        targets += _sourced(list(segment.redirects))

        if segment.argv:
            targets += _segment_targets(list(segment.argv), depth)

    return targets


def _is_source(target: str) -> bool:
    if not target:
        return False

    path = PurePosixPath(target.replace("\\", "/"))
    name = path.name
    lowered = name.lower()

    if not name:
        return False

    if any(part == "docs" for part in path.parts[:-1]):
        return False

    if lowered in NON_SOURCE_NAMES or lowered.startswith("license."):
        return False

    if lowered.endswith(".env.example"):
        return False

    suffix = path.suffix.lower()

    if suffix in NON_SOURCE_SUFFIXES:
        return False

    return suffix in CODE_SUFFIXES


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
    subagent = _is_subagent(payload, fmt, subagent_flag)

    if subagent:
        agent_type = _agent_type(payload)
        definition = _read_agent_definition(agent_type)

        if definition is None:
            return None

        if _declares_skills(definition):
            return None

        return RULE_B_REASON.format(agent=agent_type)

    tool = _tool_name(payload)
    tool_input = _tool_input(payload)

    if tool in EDIT_TOOLS:
        target = _direct_target(tool_input)
        if _is_source(target):
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
            targets = _command_targets(command)
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
