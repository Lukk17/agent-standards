#!/usr/bin/env python3
"""Shared preflight gate for every agent surface.

Reads one hook payload as JSON on stdin and decides whether a tool call may
proceed. Three rules:

A. The main thread may not write any file. It delegates the change to a
   subagent that owns the area. This covers the edit tools and the shell: a
   command is lexed and matched against the programs that write files, so
   reaching for sed, a redirection or a patch is not a way around the rule.
   Deleting, moving or renaming a directory that contains the repository,
   or the repository root itself, is a write of the repository too. The
   inner command of a wrapper (cmd /c or /k, sh -c and its kin, powershell
   or pwsh -Command or -EncodedCommand) is read the same way, and inline
   Python or JavaScript is read for the path it actually writes.
B. A subagent whose own definition declares no skills may not act. The caller
   spawns a specialist that declares its skills instead.
C. The main thread may not run a web fetch or web search tool directly, on
   the formats where that tool is known by name (currently Claude Code only,
   see RESEARCH_TOOLS). It spawns a subagent to do the research and report
   back instead.
D. The main thread may not run a script or a module, because the gate cannot
   see what a script writes. That is an interpreter handed a file or a module
   (python x.py, python -m x, node x.js, bash x.sh, pwsh -File x.ps1 and
   their kin), a package or task runner handed any subcommand (npm, npx,
   pnpm, yarn, uv, pip and their kin), a git subcommand that runs a command
   of its own, and a program invoked by a relative path or a script file
   name. The one exception is a command that matches an entry of
   MAIN_THREAD_ALLOWLIST, or of the project's own ALLOWLIST_FILE, in full.
   Inline code (python -c, node -e) is not a script run: the inline-code
   reader below judges it under Rule A instead.

Every rule above denies only once the caller is positively identified as the
main thread. A format whose payload carries nothing that could identify the
caller (currently Copilot, and a runner envelope with no is_subagent, see
_caller_identity) is left ungated rather than guessed at: denying blind risks blocking a legitimate subagent as often as it
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
(_resolves_inside_repo, _path_exists_in_repo, _contains_repo): a path they
cannot resolve fails toward True, which denies rather than allows, because
the whole point of those helpers is to decide what Rule A protects. A write
the gate recognises but cannot place (nesting past _MAX_NESTING, code piped
from a program whose output it cannot read, an unreadable sourced file, a
process spawned from inline code) is treated the same way and denies.

Rule A protects a project, not the whole filesystem, and the boundary is
every root in _roots(): the process working directory, the project root the
payload names in its cwd field, and the gate's own on-disk location two
parents up. That last one counts only while it really is a project. The
user-level install in docs/GLOBAL_SETUP.md puts this script under the home
directory, where two parents up is the home directory itself, so it is
dropped there and only the project the session is in stays protected.

Rule A exempts exactly one path, TASK_LIST_NAME at the project root. The main
thread owns the task list, so it keeps writing that one file directly.

Arguments are scanned by hand rather than with argparse, because argparse
exits 2 on a usage error and 2 is the deny code in the plain format (see
docs/hooks-contract.md).
"""

import ast
import base64
import binascii
import fnmatch
import functools
import io
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import AbstractSet, Any, Callable, Dict, FrozenSet, List, NamedTuple, Optional, Set, TextIO, Tuple

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

# Every header apply_patch's own custom diff format and a standard unified or
# git diff use to name a file a patch adds, changes, deletes, or moves, on
# either side of the move. The exact key Codex's payload uses to carry the
# patch body is not confirmed (see AGENTS.md Defect 3), so every string value
# in the tool call is searched rather than one named key.
_APPLY_PATCH_FILE_RE = re.compile(
    r"^\*\*\* (?:Update|Add|Delete) File: (?P<named>.+?)\s*$"
    r"|^\*\*\* Move to: (?P<moved>.+?)\s*$"
    r"|^\+\+\+ b/(?P<unified>.+?)\s*$"
    r"|^--- a/(?P<source>.+?)\s*$"
    r"|^rename (?:from|to) (?P<renamed>.+?)\s*$",
    re.MULTILINE,
)

# Formats whose payload names a fetch or search tool the gate recognises.
# Claude Code's tools are confirmed as WebFetch and WebSearch. Codex has no
# confirmed equivalent name (see AGENTS.md), so it stays out of this set
# until one is verified; adding it here is the whole follow-up once it is.
RESEARCH_FORMATS = frozenset({"claude"})
RESEARCH_TOOLS = {"webfetch", "websearch"}

FORMATS = ("claude", "codex", "copilot", "plain")

# Runner envelope versions this gate understands (docs/hooks-contract.md). A
# plain envelope naming any other version is allowed unread.
CONTRACTS = frozenset({3})

# The one file Rule A never protects, at the project root only. The main
# thread keeps the task list itself, so .agents/hooks/task_list_sync.py and
# the model both write it without delegating.
TASK_LIST_NAME = "tasks.md"


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

RULE_D_REASON = (
    "PREFLIGHT: the main thread may not run a script or a module directly, because the "
    "gate cannot see what it writes. Delegate the run to a subagent that owns the area, "
    "or run one of the read-only checks in MAIN_THREAD_ALLOWLIST in "
    ".agents/hooks/preflight_gate.py or in the project's main-thread-allowlist.txt. "
    "Blocked command: {command}"
)

class AllowedCheck(NamedTuple):
    """A built-in read-only check: the words it starts with and the only options it may carry.

    Any option outside `switches` (no value) and `valued` (a value, attached
    or following) denies. `operands` says whether a bare word may follow,
    and `inside` requires every such word to name a path in the repository.
    """

    words: Tuple[str, ...]
    switches: AbstractSet[str] = frozenset()
    valued: AbstractSet[str] = frozenset()
    operands: bool = True
    inside: bool = False


# pytest options that only select, report to the terminal, or stop early.
# Everything that loads a plugin, a configuration file, a root directory or a
# conftest from elsewhere, sets the temporary base, writes a report, or
# imports a warning category (-W) is left out and so denies.
_PYTEST_SWITCHES = frozenset(
    {
        "-q",
        "--quiet",
        "-v",
        "--verbose",
        "-x",
        "--exitfirst",
        "-s",
        "-l",
        "--showlocals",
        "--lf",
        "--last-failed",
        "--ff",
        "--failed-first",
        "--nf",
        "--new-first",
        "--sw",
        "--stepwise",
        "--co",
        "--collect-only",
        "--no-header",
        "--no-summary",
        "--strict-markers",
        "--runxfail",
    }
)
_PYTEST_VALUED = frozenset({"-k", "-m", "-r", "--tb", "--maxfail", "--durations", "--capture", "--color", "--deselect", "--ignore"})

# Rule D's built-in allowlist: the read-only checks the main thread may run
# itself, each with the exact options it may carry. The first word is a
# program compared by name once interpreter spellings fold together, so
# python3, python3.13 and py are all python (see _PROGRAM_ALIASES). A program
# spelled with a path is a different program and matches no entry here. git
# has no entry: git is judged by what it writes, like any other command, and
# never counts as a script run except where it runs one of its own. An entry
# exempts a command from Rule D only: a redirect or a write inside it is
# still Rule A's to judge.
MAIN_THREAD_ALLOWLIST = (
    AllowedCheck(("python", "-m", "pytest"), _PYTEST_SWITCHES, _PYTEST_VALUED, inside=True),
    AllowedCheck(("node", "--check")),
    AllowedCheck(("bash", "-n")),
)

# A project extends the allowlist without touching this file, which an update
# overwrites: one entry per line in this file at the project root, split into
# words on whitespace, with blank lines and lines starting with # ignored. A
# word holding a slash is a path and matches the file it names from wherever
# the command stands, so a `cd` cannot make it name a different file, and the
# first word is compared that way too. A trailing ANY_ARGUMENTS accepts any
# further arguments, and without it the command has to end where the entry
# ends. It sits at
# the root rather than under .agents/, which consumers import whole, so an
# import neither ships one project's entries nor overwrites another's. The main
# thread cannot write it, because Rule A protects it like any project file.
ALLOWLIST_FILE = "main-thread-allowlist.txt"
ANY_ARGUMENTS = "..."


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

    # "plain": the runner envelope (docs/hooks-contract.md) sets is_subagent
    # only once it has positively placed the session, and leaves it out when
    # the lookup failed, so anything but a real boolean is unknown.
    subagent = payload.get("is_subagent")

    if subagent is True:
        return _SUBAGENT

    return _MAIN_THREAD if subagent is False else _UNKNOWN


def _agent_type(payload: Dict[str, Any]) -> str:
    for key in ("agent_type", "agentType", "subagent_type", "agent"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# The project root the payload named, or None while no payload has been read.
# Claude Code, Codex and the runner envelope all send the open project as cwd,
# and it is the only root that still names the project once the gate is
# installed under the user's home directory instead of inside a project. Set
# only through _decide, which clears it again once the call has been decided.
_PAYLOAD_ROOT: Optional[Path] = None


def _payload_root(payload: Dict[str, Any]) -> Optional[Path]:
    value = payload.get("cwd")

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return _native_path(value.strip())
    except (OSError, ValueError):
        return None


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
        next(value for value in match.groups() if value)
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

# Directories a `cd` inside the command moved to, or None while the command
# has not changed directory yet. Every relative path after that `cd` resolves
# against these instead of against the repository roots, so
# `cd C:/Users/me/notes && printf x >> MEMORY.md` writes outside the
# repository and is allowed, while `cd tools && printf x >> gen_subagents.py`
# still resolves inside and is denied. It is a tuple rather than one path
# because a relative destination is resolved against every root in _roots(),
# and a target counts as inside when any one of those landings places it
# inside. A subshell, meaning a parenthesised group or a single pipeline
# stage, gets the value put back when it ends, because the real shell's own
# directory is untouched by what the child did. Set only through
# _shell_targets, which clears it again once the command has been read.
_CD_BASE: Optional[Tuple[Path, ...]] = None

# The directories pushd and Push-Location left, newest last, for popd and
# Pop-Location to return to. Set only through _shell_targets, like _CD_BASE.
_CD_STACK: List[Optional[Tuple[Path, ...]]] = []

_QUOTED_LITERAL_RE = re.compile(r"""['"]([^'"]*)['"]""")
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*=")

# Environment variables that change which program, library, configuration,
# repository or directory a command uses: git's own configuration and
# repository location, the pagers and editors git starts, a preloaded library
# or interpreter option, a shell start-up file, the program search path, a
# test runner's own options, and the temporary directory a runner writes
# under. A command run with one of them set is not the command its words
# spell, so the gate cannot place it. Names compare without case, because
# Windows reads them that way.
_UNPLACEABLE_ENVIRONMENT = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_EXTERNAL_DIFF",
        "GIT_PAGER",
        "GIT_EDITOR",
        "GIT_SEQUENCE_EDITOR",
        "GIT_SSH",
        "GIT_SSH_COMMAND",
        "GIT_ASKPASS",
        "SSH_ASKPASS",
        "GIT_EXEC_PATH",
        "GIT_TEMPLATE_DIR",
        "GIT_PROXY_COMMAND",
        "PAGER",
        "MANPAGER",
        "LESSOPEN",
        "LESSCLOSE",
        "EDITOR",
        "VISUAL",
        "HOME",
        "USERPROFILE",
        "XDG_CONFIG_HOME",
        "NODE_OPTIONS",
        "NODE_PATH",
        "PYTHONPATH",
        "PYTHONHOME",
        "PYTHONSTARTUP",
        "PYTHONUSERBASE",
        "PYTHONEXECUTABLE",
        "PYTHONPLATLIBDIR",
        "PYTHONBREAKPOINT",
        "PYTHONPYCACHEPREFIX",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "PYTEST_DEBUG_TEMPROOT",
        "PERL5OPT",
        "PERL5LIB",
        "PERLLIB",
        "PERL5DB",
        "RUBYOPT",
        "RUBYLIB",
        "BASH_ENV",
        "ENV",
        "SHELLOPTS",
        "BASHOPTS",
        "PS4",
        "PROMPT_COMMAND",
        "JAVA_TOOL_OPTIONS",
        "_JAVA_OPTIONS",
        "JDK_JAVA_OPTIONS",
        "DOTNET_STARTUP_HOOKS",
        "DOTNET_ADDITIONAL_DEPS",
        "PATH",
        "PATHEXT",
        "COMSPEC",
        "TMPDIR",
        "TEMP",
        "TMP",
    }
)
_UNPLACEABLE_ENVIRONMENT_PREFIXES = ("GIT_CONFIG", "GIT_TRACE", "LD_", "DYLD_", "BASH_FUNC_", "COR_", "CORECLR_")
_UNPLACEABLE_ENVIRONMENT_TARGET = "environment variable (a setting that changes which program or file a command uses)"
# Builtins that set a shell variable for the rest of the shell and its children.
_POSIX_DECLARATIONS = {"export", "declare", "typeset", "readonly", "local"}
_PS_ENVIRONMENT_RE = re.compile(r"^env:[\\/]*(?P<name>[\w()]+)", re.IGNORECASE)
_PS_ENVIRONMENT_SETTERS = {"set-item", "new-item", "set-content", "add-content", "copy-item", "move-item", "rename-item"}
_VERSIONED_TOOL_RE = re.compile(r"^(python|node|php|ruby|perl|awk|gawk|lua|julia)[0-9.]*$")
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
    "lua",
    "luajit",
    "rscript",
    "r",
    "julia",
}
# -E is inline code only to these two. To python it means ignore the environment.
_UPPER_E_CODE_TOOLS = {"perl", "julia"}

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

_POSIX_SHELLS = {"sh", "bash", "zsh", "dash", "ash", "ksh"}
_POWERSHELL_SHELLS = {"pwsh", "powershell"}
_CMD_SHELLS = {"cmd"}

# `bash -c`, and any short-option cluster holding c such as `bash -lc`. The
# command string is the one argument after it, the rest become $0, $1 and on.
_POSIX_CODE_FLAG_RE = re.compile(r"^-[A-Za-z]*c[A-Za-z]*$")

# cmd runs everything after /c or /k as one command line.
_CMD_CODE_FLAGS = {"/c", "/k"}

# PowerShell parameter names are case-insensitive and take any unambiguous
# prefix. -Command takes every argument after it as the command, and
# -CommandWithArgs takes only the first one. -EncodedCommand carries the
# command as Base64 over UTF-16LE. See about_Pwsh.
_PS_COMMAND_FLAG = "-command"
_PS_COMMAND_ALIASES = {"-c", "--command", "/c"}
_PS_COMMAND_WITH_ARGS_FLAGS = {"-commandwithargs", "-cwa"}
_PS_ENCODED_FLAG = "-encodedcommand"
_PS_ENCODED_ALIASES = {"-e", "-ec"}
_PS_MIN_PREFIX = 4

_WRAPPER_TOOLS = {
    "busybox",
    "toybox",
    "setsid",
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
# Wrapper options that run the command in another directory.
_WRAPPER_CHDIR_FLAGS = {"env": ("-C", "--chdir"), "sudo": ("-D", "--chdir")}
_WRAPPER_VALUE_FLAGS = {"-u", "-g", "-p", "-C", "-n", "-k", "--signal", "-o", "-e", "-i"}
# xargs -i, -e and -l take their value attached or not at all, so only the
# flags below consume the next word.
_XARGS_VALUE_FLAGS = {
    "-n",
    "-P",
    "-I",
    "-a",
    "-d",
    "-E",
    "-L",
    "-s",
    "--max-args",
}

_FIND_EXEC_MARKERS = {"-exec", "-execdir", "-ok", "-okdir"}
_FIND_NAME_FLAGS = {"-name", "-iname"}
_FIND_PATH_FLAGS = {"-path", "-ipath", "-wholename", "-iwholename"}
_FIND_WRITE_FLAGS = {"-fprint", "-fprint0", "-fprintf", "-fls"}
_FIND_OPTIONS = {"-H", "-L", "-P", "-D"}

_TOUCH_VALUE_FLAGS = {"-d", "--date", "-t", "-r", "--reference"}
_MKDIR_VALUE_FLAGS = {"-m", "--mode", "--context"}

# curl's short options that take a value, the ones among them that name a
# file curl writes, and the long options that do. -O names its file after
# the URL instead of taking one.
_CURL_VALUE_SHORTS = set("AbcCdDeEFHKmoPQrtTuUwxXyYz")
_CURL_WRITE_SHORTS = set("ocD")
_CURL_WRITE_LONGS = {
    "--output",
    "--cookie-jar",
    "--dump-header",
    "--trace",
    "--trace-ascii",
    "--stderr",
    "--libcurl",
    "--etag-save",
    "--hsts",
    "--alt-svc",
}
_CURL_REMOTE_LONGS = {"--remote-name", "--remote-name-all"}
_WGET_VALUE_SHORTS = set("OoaPeiBtTwUQlARDIX")
_TAR_LONG_MODES = {"--extract": "x", "--get": "x", "--create": "c", "--append": "r", "--update": "u"}
_UNZIP_READ_FLAGS = {"-l", "-t", "-v", "-p", "-z", "-Z"}

_GIT_SWITCH_SUBCOMMANDS = {"checkout", "switch"}
_GIT_FORCE_FLAGS = {"-f", "--force", "--discard-changes"}
_GIT_WORKTREE_RESETS = {"--hard", "--keep", "--merge"}
_GIT_STASH_VALUE_FLAGS = {"-m", "--message", "--pathspec-from-file"}
_GIT_STASH_ACTIONS = {"push", "save", "pop", "apply", "branch", "drop", "clear", "list", "show", "create", "store"}
_GIT_STASH_WRITES = {"save", "pop", "apply", "branch"}

# Options that take a value, so the word after them is not a script operand.
_POSIX_SHELL_VALUE_FLAGS = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
_PYTHON_VALUE_FLAGS = {"-W", "-X", "-c", "-m"}
_INTERPRETER_VALUE_FLAGS = {"-r", "--require", "--import", "--loader", "-I", "-M", "-d", "-c", "-e", "-E"}
_PS_HOST_VALUE_FLAGS = {
    "-executionpolicy",
    "-ep",
    "-ex",
    "-workingdirectory",
    "-wd",
    "-configurationname",
    "-config",
    "-outputformat",
    "-of",
    "-o",
    "-inputformat",
    "-if",
    "-inp",
    "-windowstyle",
    "-w",
    "-version",
    "-v",
    "-psconsolefile",
    "-settingsfile",
    "-settings",
    "-custompipename",
}
_ECHO_FLAGS = {"-n", "-e", "-E", "-ne", "-en", "-nE", "-En"}

# A sourced or piped script larger than this is not read, and counts as code
# the gate cannot place.
_MAX_SCRIPT_BYTES = 1 << 20

# What a pipeline stage produces when the gate cannot tell. A NUL never
# reaches a command line, so it cannot collide with real output.
_UNKNOWN_INPUT = "\0"
_UNPLACEABLE_SHELL_TARGET = "shell code (a command the gate cannot read)"
_UNPLACEABLE_ARGUMENT = "xargs input (arguments the gate cannot read)"

# Commands that take their operand away from where it was: deleting it, or
# moving or renaming it. Their operand counts when it is inside the
# repository, and also when it contains the repository, because removing
# or moving a parent takes the repository with it. rmdir and rd are both a
# POSIX or cmd command and a PowerShell alias of Remove-Item, and del and
# erase are cmd commands as well as aliases.
_REMOVE_TOOLS = {"rm", "rmdir", "rd"}
_MOVE_TOOLS = {"mv", "move"}

# Commands that change the directory relative paths resolve against.
_DIRECTORY_CHANGERS = {"cd", "pushd", "chdir", "set-location", "sl", "push-location", "popd", "pop-location"}
_DIRECTORY_PUSHERS = {"pushd", "push-location"}
_DIRECTORY_POPPERS = {"popd", "pop-location"}


class _ShellParseError(Exception):
    """The command cannot be lexed with confidence, so the gate allows."""


class ShellSegment(NamedTuple):
    """One command in a lexed line, or a marker for a grouping token.

    A segment with a `control` of "(", ")" or "|" carries no argv: it records
    where a subshell begins and ends, which is what stops a `cd` inside one
    from moving the base for everything after it. `stdin` holds the heredoc
    and here-string bodies the command reads, and `literal` marks a segment
    that is one fully quoted word, which PowerShell writes to its output.
    `expression` marks a PowerShell statement whose first word is a quoted
    string not handed to the call operator, which PowerShell evaluates as a
    value and never runs as a program.
    """

    argv: Tuple[str, ...] = ()
    redirects: Tuple[str, ...] = ()
    control: str = ""
    stdin: Tuple[str, ...] = ()
    literal: bool = False
    expression: bool = False


# The three command-line grammars the gate reads. A POSIX shell escapes with
# a backslash, PowerShell with a backtick and leaves a backslash literal, and
# cmd escapes with a caret outside double quotes and has no escape inside
# them. Reading every dialect the POSIX way let `Remove-Item "D:\parent\"`
# fail to lex, and a lex failure allows.
_POSIX = "posix"
_POWERSHELL = "powershell"
_CMD = "cmd"

# An unquoted comma in a PowerShell argument builds an array, so `a,..` is two
# paths. The lexer marks it with a character no command line carries, and the
# cmdlet binder or _split_arrays turns it into separate values.
_ARRAY_SEPARATOR = "\x1f"

# What a PowerShell `(...)` or `$(...)` argument stands for: a value the gate
# cannot know, which resolves inside the repository and so denies wherever a
# path is expected.
_SUBEXPRESSION = "$(subexpression)"


# cmd's own commands, which read their arguments with cmd's quoting rather
# than the C runtime's, so a backslash before a quote stays a backslash.
_CMD_BUILTINS = frozenset(
    {
        "assoc", "break", "call", "cd", "chdir", "cls", "color", "copy", "date", "del", "dir", "echo", "endlocal",
        "erase", "exit", "for", "ftype", "goto", "if", "md", "mkdir", "mklink", "move", "path", "pause", "popd",
        "prompt", "pushd", "rd", "ren", "rename", "rmdir", "set", "setlocal", "shift", "start", "time", "title",
        "type", "ver", "verify", "vol",
    }
)

# Command substitutions a quoted word runs before its command does: the
# dialect of the code, and the code. _lex turns each into a child shell
# segment placed just before the command that holds it.
_Substitutions = List[Tuple[str, str]]

# PowerShell's tokenizer accepts the typographic quotes as well as the ASCII
# ones, so 'x’ is a complete string there.
_PS_SINGLE_QUOTES = "'\u2018\u2019\u201a\u201b"
_PS_DOUBLE_QUOTES = '"\u201c\u201d\u201e'

# Backtick escapes inside a PowerShell expandable string (about_Special_Characters).
_PS_ESCAPES = {"0": "\0", "a": "\a", "b": "\b", "e": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}

# Backslash escapes inside a bash $'...' string.
_ANSI_C_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "e": "\x1b",
    "E": "\x1b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "?": "?",
}


def _line_continuation(text: str, index: int) -> int:
    """How many characters an escaped line break at index spans, LF or CR LF, or 0."""
    if text.startswith("\r\n", index):
        return 2

    return 1 if index < len(text) and text[index] == "\n" else 0


def _read_balanced(text: str, index: int, dialect: str) -> Tuple[str, int]:
    """The code of a `$(...)` whose opening parenthesis sits at index, and where it ends."""
    depth = 0
    position = index

    while position < len(text):
        char = text[position]

        if dialect == _POSIX and char == "\\" or dialect == _POWERSHELL and char == "`":
            position += 2
            continue

        if dialect == _POSIX and char == "'" or dialect == _POWERSHELL and char in _PS_SINGLE_QUOTES:
            if dialect == _POWERSHELL:
                _, position = _read_ps_single_quoted(text, position)
            else:
                close = text.find("'", position + 1)

                if close < 0:
                    raise _ShellParseError("unterminated single quote")

                position = close + 1
            continue

        if char == '"' or dialect == _POWERSHELL and char in _PS_DOUBLE_QUOTES:
            reader = _read_ps_double_quoted if dialect == _POWERSHELL else _read_double_quoted
            _, position = reader(text, position)
            continue

        if dialect == _POSIX and char == "`":
            _, position = _read_backticks(text, position)
            continue

        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1

            if depth == 0:
                return text[index + 1 : position], position + 1

        position += 1

    raise _ShellParseError("unterminated command substitution")


def _read_backticks(text: str, index: int) -> Tuple[str, int]:
    """The code of a POSIX backquoted substitution opened at index, and where it ends."""
    out: List[str] = []
    position = index + 1

    while position < len(text):
        char = text[position]

        if char == "\\" and position + 1 < len(text) and text[position + 1] in '`\\$"':
            out.append(text[position + 1])
            position += 2
            continue

        if char == "`":
            return "".join(out), position + 1

        out.append(char)
        position += 1

    raise _ShellParseError("unterminated backquote")


def _read_double_quoted(text: str, index: int, found: Optional[_Substitutions] = None) -> Tuple[str, int]:
    """A POSIX double-quoted string, with every `$(...)` and backquote in it recorded in found."""
    index += 1
    out: List[str] = []

    while index < len(text):
        char = text[index]

        if char == '"':
            return "".join(out), index + 1

        if char == "\\" and index + 1 < len(text):
            joined = _line_continuation(text, index + 1)

            if joined:
                index += 1 + joined
                continue

            if text[index + 1] in '"\\$`':
                out.append(text[index + 1])
                index += 2
                continue

        if char == "$" and text.startswith("$(", index):
            code, index = _read_balanced(text, index + 1, _POSIX)

            out.append(_SUBEXPRESSION)

            if found is not None and not code.startswith("("):
                found.append((_POSIX, code))
            continue

        if char == "`":
            code, index = _read_backticks(text, index)
            out.append(_SUBEXPRESSION)

            if found is not None:
                found.append((_POSIX, code))
            continue

        out.append(char)
        index += 1

    raise _ShellParseError("unterminated double quote")


def _read_ansi_c_quoted(text: str, index: int) -> Tuple[str, int]:
    """A bash $'...' string opened at index (the `$`), with its escapes decoded."""
    index += 2
    out: List[str] = []

    while index < len(text):
        char = text[index]

        if char == "'":
            return "".join(out), index + 1

        if char != "\\" or index + 1 >= len(text):
            out.append(char)
            index += 1
            continue

        follower = text[index + 1]
        index += 2

        if follower in _ANSI_C_ESCAPES:
            out.append(_ANSI_C_ESCAPES[follower])
        elif follower in "xuU":
            size = {"x": 2, "u": 4, "U": 8}[follower]
            digits = re.match(r"[0-9A-Fa-f]{1,%d}" % size, text[index:])
            out.append(chr(int(digits.group(0), 16)) if digits else "\\" + follower)
            index += len(digits.group(0)) if digits else 0
        elif follower in "01234567":
            digits = re.match(r"[0-7]{0,2}", text[index:])
            out.append(chr(int(follower + (digits.group(0) if digits else ""), 8) & 0xFF))
            index += len(digits.group(0)) if digits else 0
        elif follower == "c" and index < len(text):
            out.append(chr(ord(text[index]) & 0x1F))
            index += 1
        else:
            out.append("\\" + follower)

    raise _ShellParseError("unterminated ANSI-C quote")


def _read_ps_single_quoted(text: str, index: int) -> Tuple[str, int]:
    """A PowerShell verbatim string, where a doubled quote is one quote."""
    index += 1
    out: List[str] = []

    while index < len(text):
        char = text[index]

        if char in _PS_SINGLE_QUOTES:
            if index + 1 < len(text) and text[index + 1] in _PS_SINGLE_QUOTES:
                out.append(char)
                index += 2
                continue
            return "".join(out), index + 1

        out.append(char)
        index += 1

    raise _ShellParseError("unterminated single quote")


def _read_ps_double_quoted(text: str, index: int, found: Optional[_Substitutions] = None) -> Tuple[str, int]:
    """A PowerShell expandable string: a backtick escapes, a backslash does not, `$(...)` runs."""
    index += 1
    out: List[str] = []

    while index < len(text):
        char = text[index]

        if char == "`" and index + 1 < len(text):
            joined = _line_continuation(text, index + 1)
            follower = text[index + 1]

            if joined:
                index += 1 + joined
                continue

            unicode = re.match(r"u\{([0-9A-Fa-f]{1,6})\}", text[index + 1 :])

            if unicode:
                out.append(chr(int(unicode.group(1), 16)))
                index += 1 + len(unicode.group(0))
                continue

            out.append(_PS_ESCAPES.get(follower, follower))
            index += 2
            continue

        if char in _PS_DOUBLE_QUOTES:
            if index + 1 < len(text) and text[index + 1] in _PS_DOUBLE_QUOTES:
                out.append(char)
                index += 2
                continue
            return "".join(out), index + 1

        if char == "$" and text.startswith("$(", index):
            code, index = _read_balanced(text, index + 1, _POWERSHELL)
            out.append(_SUBEXPRESSION)

            if found is not None:
                found.append((_POWERSHELL, code))
            continue

        out.append(char)
        index += 1

    raise _ShellParseError("unterminated double quote")


def _windows_argv(text: str) -> List[str]:
    """Split a native command line the way CommandLineToArgvW and the C runtime do.

    Backslashes are literal except before a double quote: 2n of them and a
    quote are n backslashes and a quote that toggles quoting, 2n+1 of them and
    a quote are n backslashes and a literal quote. Inside quotes a doubled
    quote is one literal quote.
    """
    args: List[str] = []
    current: List[str] = []
    quoted = False
    started = False
    index = 0

    while index < len(text):
        char = text[index]

        if char == "\\":
            run = len(text[index:]) - len(text[index:].lstrip("\\"))
            index += run
            started = True

            if index < len(text) and text[index] == '"':
                current.append("\\" * (run // 2))

                if run % 2:
                    current.append('"')
                    index += 1
            else:
                current.append("\\" * run)
            continue

        if char == '"':
            if quoted and text.startswith('""', index):
                current.append('"')
                index += 2
                continue

            quoted = not quoted
            started = True
            index += 1
            continue

        if char in " \t\r\n" and not quoted:
            if started:
                args.append("".join(current))
                current = []
                started = False
            index += 1
            continue

        current.append(char)
        started = True
        index += 1

    if started:
        args.append("".join(current))

    return args


def _read_ps_here_string(text: str, index: int) -> Optional[Tuple[str, int]]:
    """A PowerShell here-string opened at index, or None when none opens there."""
    quote = text[index + 1]
    line_end = text.find("\n", index + 2)

    if line_end < 0 or text[index + 2 : line_end].strip():
        return None

    close = text.find("\n" + quote + "@", line_end)

    if close < 0:
        raise _ShellParseError("unterminated here-string")

    return text[line_end + 1 : close], close + 3


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


class _Heredoc(NamedTuple):
    delimiter: str
    strip_tabs: bool
    body: List[str]


def _consume_heredocs(text: str, index: int, pending: List[_Heredoc]) -> int:
    """Read every pending heredoc body into the segment that declared it."""
    while pending:
        heredoc = pending.pop(0)

        while index < len(text):
            end = text.find("\n", index)
            line = text[index:] if end < 0 else text[index:end]
            index = len(text) if end < 0 else end + 1

            if heredoc.strip_tabs:
                line = line.lstrip("\t")

            if line.strip() == heredoc.delimiter:
                break

            heredoc.body.append(line + "\n")

    return index


def _literal_tilde(piece: str, started: bool) -> str:
    """A quoted piece, pinned relative when it would open a word with `~`.

    POSIX shells leave a quoted tilde literal, so `'~/x'` names `./~/x`.
    PowerShell's providers expand even a quoted one, and reading it as
    relative there resolves inside the repository, which errs toward a deny.
    """
    return "./" + piece if not started and piece.startswith("~") else piece


def _lex(command: str, dialect: str = _POSIX) -> List[ShellSegment]:
    """Split a command into segments of argv plus redirection targets."""
    posix = dialect == _POSIX
    powershell = dialect == _POWERSHELL
    cmd = dialect == _CMD
    escape = "\\" if posix else "`" if powershell else "^"

    segments: List[ShellSegment] = []
    owners: List[Tuple[int, List[List[str]]]] = []
    substitutions: _Substitutions = []
    argv: List[str] = []
    redirects: List[str] = []
    bodies: List[List[str]] = []
    heredocs: List[_Heredoc] = []
    token = ""
    started = False
    bare = False
    first_quoted = False
    opens_quoted = False
    first_opens_quoted = False
    called = False
    pending = ""
    cmd_quoted = False
    argv_quoted = False
    index = 0
    length = len(command)

    def flush() -> None:
        nonlocal token, started, bare, first_quoted, first_opens_quoted, pending

        if not started:
            return

        if pending == "redirect":
            redirects.append(token)
        elif pending == "dup":
            if not (token.isdigit() or token == "-"):
                redirects.append(token)
        elif pending == "herestring":
            bodies.append([token + "\n"])
        elif pending != "discard":
            if not argv:
                first_quoted = not bare
                first_opens_quoted = opens_quoted
            argv.append(token)

        token = ""
        started = False
        bare = False
        pending = ""

    def end_segment() -> None:
        nonlocal argv, redirects, bodies, argv_quoted, called

        flush()
        argv_quoted = False

        # A substitution runs before the command that holds it, in a child
        # shell, so it is judged as one placed just ahead of that command.
        for child, code in substitutions:
            shell = ("sh", "-c", code) if child == _POSIX else ("pwsh", "-Command", code)
            segments.extend((ShellSegment(control="("), ShellSegment(shell), ShellSegment(control=")")))

        substitutions.clear()

        if argv or redirects or bodies:
            literal = len(argv) == 1 and first_quoted
            expression = powershell and bool(argv) and first_opens_quoted and not called
            segments.append(ShellSegment(tuple(argv), tuple(redirects), literal=literal, expression=expression))

            if bodies:
                owners.append((len(segments) - 1, bodies))

        argv = []
        redirects = []
        bodies = []
        called = False

    def add(text: str, quoted: bool) -> None:
        nonlocal token, started, bare, opens_quoted

        opens_quoted = quoted if not started else opens_quoted
        token += text
        started = True
        bare = bare or not quoted

    def line_break() -> int:
        nonlocal cmd_quoted, argv_quoted

        end_segment()
        cmd_quoted = argv_quoted = False

        return _consume_heredocs(command, index + 1, heredocs) if posix else index + 1

    while index < length:
        char = command[index]

        # cmd reads quotes twice over. cmd itself toggles its quoting on every
        # double quote when it looks for & | < > ( ), and the program then
        # splits its own argv by the C runtime's rules (see _windows_argv), so
        # a backslash-escaped quote can end cmd's quoting while leaving the
        # argument quoted, and the reverse.
        if cmd and char == "\\" and argv and _basename(argv[0]) not in _CMD_BUILTINS:
            run = len(command[index:]) - len(command[index:].lstrip("\\"))

            if index + run < length and command[index + run] == '"':
                add("\\" * (run // 2), cmd_quoted)
                index += run

                if run % 2:
                    add('"', True)
                    index += 1
                    cmd_quoted = not cmd_quoted
                continue

            add("\\" * run, cmd_quoted)
            index += run
            continue

        if cmd and char == '"':
            if argv_quoted and command.startswith('""', index) and argv and _basename(argv[0]) not in _CMD_BUILTINS:
                add('"', True)
                index += 2
                continue

            cmd_quoted = not cmd_quoted
            argv_quoted = not argv_quoted
            add("", True)
            index += 1
            continue

        if cmd and char == "^" and command.startswith('^"', index) and not cmd_quoted:
            argv_quoted = not argv_quoted
            add("", True)
            index += 2
            continue

        if cmd and char not in "\r\n" and (cmd_quoted or argv_quoted and char in " \t"):
            add(char, True)
            index += 1
            continue

        if powershell and char == "@" and not started and command.startswith(("@'", '@"'), index):
            here = _read_ps_here_string(command, index)

            if here is not None:
                add(here[0], True)
                index = here[1]
                continue

        if posix and char == "$" and command.startswith("$'", index):
            piece, index = _read_ansi_c_quoted(command, index)
            add(piece, True)
            continue

        if posix and char == "`":
            code, index = _read_backticks(command, index)
            substitutions.append((_POSIX, code))
            add(_SUBEXPRESSION, False)
            continue

        if powershell and char == "-" and not started and command.startswith("--%", index):
            stop = index + 3

            if stop == length or command[stop] in " \t\r\n|":
                # The stop-parsing token hands the rest of the line to the
                # native program verbatim, up to a newline or a pipe.
                end = min((found for found in (command.find(mark, stop) for mark in "\r\n|") if found >= 0), default=length)
                flush()
                argv.extend(_windows_argv(command[stop:end]))
                index = end
                continue

        if char == "'" and not cmd or powershell and char in _PS_SINGLE_QUOTES:
            if powershell:
                piece, index = _read_ps_single_quoted(command, index)
            else:
                close = command.find("'", index + 1)
                if close < 0:
                    raise _ShellParseError("unterminated single quote")
                piece, index = command[index + 1 : close], close + 1
            add(_literal_tilde(piece, started), True)
            continue

        if char == '"' or powershell and char in _PS_DOUBLE_QUOTES:
            if powershell:
                piece, index = _read_ps_double_quoted(command, index, substitutions)
            else:
                piece, index = _read_double_quoted(command, index, substitutions)
            add(_literal_tilde(piece, started), True)
            continue

        if char == escape:
            follower = command[index + 1] if index + 1 < length else ""
            joined = _line_continuation(command, index + 1)

            if joined:
                index += 1 + joined
                continue

            if posix and not (follower and follower in _ESCAPABLE):
                add(char, False)
                index += 1
                continue

            add(follower, False)
            index += 2
            continue

        if char in " \t":
            flush()
            index += 1
            continue

        # A CR LF is one line break, and a lone CR is a line break of its own,
        # the way PowerShell reads it.
        if char == "\r" and command.startswith("\r\n", index):
            index += 1
            continue

        if char in "\r\n":
            index = line_break()
            continue

        if char == "#" and not started and not cmd:
            end = command.find("\n", index)
            index = length if end < 0 else end
            continue

        if char == ";":
            if cmd and argv and _basename(argv[0]) not in _CMD_BUILTINS:
                add(char, False)
            elif cmd:
                flush()
            else:
                end_segment()
            index += 1
            continue

        if char == "," and not posix:
            if cmd and argv and _basename(argv[0]) not in _CMD_BUILTINS:
                add(char, False)
            elif cmd:
                flush()
            else:
                add(_ARRAY_SEPARATOR, False)
            index += 1
            continue

        if powershell and char in "{}":
            if char == "{" and started and token.endswith("$"):
                close = command.find("}", index)
                if close < 0:
                    raise _ShellParseError("unterminated variable name")
                add(command[index : close + 1], False)
                index = close + 1
                continue

            end_segment()
            index += 1
            continue

        if char in "()":
            if char == "(" and powershell and (argv or started):
                flush()
                argv.append(_SUBEXPRESSION)

            end_segment()
            segments.append(ShellSegment(control=char))
            index += 1
            continue

        if char == "&":
            if posix and command.startswith("&>", index):
                flush()
                index += 3 if command.startswith("&>>", index) else 2
                pending = "redirect"
                continue

            end_segment()
            called = powershell and not command.startswith("&&", index)
            index += 2 if command.startswith("&&", index) else 1
            continue

        if char == "|":
            end_segment()

            if command.startswith("||", index):
                index += 2
                continue

            segments.append(ShellSegment(control="|"))
            index += 1
            continue

        if char == ">":
            if started and (token.isdigit() or (powershell and token == "*")):
                token = ""
                started = False
                bare = False

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
            if powershell:
                if not command.startswith("<#", index):
                    # PowerShell reserves `<` and refuses to run the line, but
                    # failing the lex here would allow the whole command, so
                    # the rest is still read as words.
                    add(char, False)
                    index += 1
                    continue

                close = command.find("#>", index + 2)
                index = length if close < 0 else close + 2
                continue

            if started and token.isdigit():
                token = ""
                started = False
                bare = False

            flush()

            if posix and command.startswith("<<<", index):
                index += 3
                pending = "herestring"
                continue

            if posix and command.startswith("<<", index):
                index += 2
                strip_tabs = index < length and command[index] == "-"

                if strip_tabs:
                    index += 1

                while index < length and command[index] in " \t":
                    index += 1

                delimiter, index = _read_word(command, index)

                if delimiter:
                    body: List[str] = []
                    heredocs.append(_Heredoc(delimiter, strip_tabs, body))
                    bodies.append(body)

                continue

            index += 1
            pending = "discard"
            continue

        add(char, False)
        index += 1

    end_segment()

    for position, owned in owners:
        stdin = tuple("".join(body) for body in owned)
        segments[position] = segments[position]._replace(stdin=stdin)

    return segments


def _split_array(token: str) -> List[str]:
    """The elements of a PowerShell comma array, or the token itself."""
    return [item for item in token.split(_ARRAY_SEPARATOR) if item]


def _split_arrays(tokens: List[str]) -> List[str]:
    """Every argument with its comma arrays spread into separate arguments.

    PowerShell hands each element of an array to a native program as its own
    argument, and a handler that reads plain operands needs the same view.
    """
    return [item for token in tokens for item in _split_array(token)]


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
    flags = _INLINE_CODE_FLAGS + (("-E",) if _program_name(tokens[0]) in _UPPER_E_CODE_TOOLS else ())

    for index, token in enumerate(tokens[1:], start=1):
        if token in flags and index + 1 < len(tokens):
            return tokens[index + 1]

        for flag in flags:
            if token.startswith(flag + "="):
                return token[len(flag) + 1 :]

    return ""


def _inline_code_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Paths an inline -c or -e program opens for writing."""
    code = _inline_code(tokens)

    if not code:
        return []

    return _program_code_targets(_program_name(tokens[0]), code, powershell)


def _program_code_targets(program: str, code: str, powershell: bool = False) -> List[str]:
    """Paths an interpreter's program writes, however the program reached it."""
    if program in _PYTHON_TOOLS:
        return _python_code_targets(code, powershell)

    if program in _JS_TOOLS:
        return _js_code_targets(code, powershell)

    language = _SCRIPT_LANGUAGES[program]
    literals = [_PERL_MODE_PREFIX_RE.sub("", item) for item in _QUOTED_LITERAL_RE.findall(code)]

    if language.spawns.search(code):
        return [_UNPLACEABLE_SCRIPT_TARGET]

    opens_for_writing = bool(language.opens.search(code)) and any(_is_write_mode_literal(item) for item in _QUOTED_LITERAL_RE.findall(code))

    if not (language.writes.search(code) or opens_for_writing):
        return []

    paths = [item for item in literals if item and not _is_option_literal(item)]

    return _sourced(paths, powershell) if paths else [_UNPLACEABLE_SCRIPT_TARGET]


def _is_write_mode_literal(literal: str) -> bool:
    return literal in _WRITE_MODES or bool(_PERL_WRITE_PREFIX_RE.match(literal))


def _is_option_literal(literal: str) -> bool:
    """True for a file mode or an encoding name, which is never the written path."""
    return literal in _WRITE_MODES or bool(_PERL_MODE_RE.match(literal)) or bool(_ENCODING_LITERAL_RE.match(literal))


# Inline Python is parsed rather than guessed at, since the standard library
# ships the parser. Each entry names the argument positions a call writes to
# and the ones it takes away, which also get the containing-directory check.
class _PythonWrite(NamedTuple):
    written: Tuple[int, ...] = ()
    removed: Tuple[int, ...] = ()


_PYTHON_TOOLS = {"python", "py"}
_PYTHON_OPEN_CALLS = {
    "open",
    "io.open",
    "codecs.open",
    "builtins.open",
    "gzip.open",
    "gzip.GzipFile",
    "bz2.open",
    "bz2.BZ2File",
    "lzma.open",
    "lzma.LZMAFile",
    "tarfile.open",
    "tarfile.TarFile",
    "zipfile.ZipFile",
}
_PYTHON_PATH_TYPES = {"Path", "PurePath", "PosixPath", "WindowsPath"}
_PYTHON_WRITE_CALLS = {
    "os.remove": _PythonWrite(removed=(0,)),
    "os.unlink": _PythonWrite(removed=(0,)),
    "os.rmdir": _PythonWrite(removed=(0,)),
    "os.removedirs": _PythonWrite(removed=(0,)),
    "os.rename": _PythonWrite(written=(1,), removed=(0,)),
    "os.renames": _PythonWrite(written=(1,), removed=(0,)),
    "os.replace": _PythonWrite(written=(1,), removed=(0,)),
    "os.truncate": _PythonWrite(written=(0,)),
    "os.mkdir": _PythonWrite(written=(0,)),
    "os.makedirs": _PythonWrite(written=(0,)),
    "os.symlink": _PythonWrite(written=(1,)),
    "os.link": _PythonWrite(written=(0, 1)),
    "os.mkfifo": _PythonWrite(written=(0,)),
    "os.mknod": _PythonWrite(written=(0,)),
    "shutil.rmtree": _PythonWrite(removed=(0,)),
    "shutil.move": _PythonWrite(written=(1,), removed=(0,)),
    "shutil.copy": _PythonWrite(written=(1,)),
    "shutil.copy2": _PythonWrite(written=(1,)),
    "shutil.copyfile": _PythonWrite(written=(1,)),
    "shutil.copytree": _PythonWrite(written=(1,)),
    "shutil.make_archive": _PythonWrite(written=(0,)),
    "shutil.unpack_archive": _PythonWrite(written=(1,)),
    "urllib.request.urlretrieve": _PythonWrite(written=(1,)),
    "sqlite3.connect": _PythonWrite(written=(0,)),
    "shelve.open": _PythonWrite(written=(0,)),
    "dbm.open": _PythonWrite(written=(0,)),
    "logging.FileHandler": _PythonWrite(written=(0,)),
    "logging.handlers.RotatingFileHandler": _PythonWrite(written=(0,)),
    "logging.handlers.TimedRotatingFileHandler": _PythonWrite(written=(0,)),
    "logging.handlers.WatchedFileHandler": _PythonWrite(written=(0,)),
}
# Calls whose only write lands in a keyword argument: the log file
# basicConfig opens, the directory a temporary file is created in, and the
# files fileinput rewrites in place.
_PYTHON_KEYWORD_WRITES = {
    "logging.basicConfig": ("filename", ()),
    "tempfile.mkstemp": ("dir", ()),
    "tempfile.mkdtemp": ("dir", ()),
    "tempfile.NamedTemporaryFile": ("dir", ()),
    "tempfile.TemporaryFile": ("dir", ()),
    "tempfile.TemporaryDirectory": ("dir", ()),
    "tempfile.SpooledTemporaryFile": ("dir", ()),
    "fileinput.input": ("inplace", (0, "files")),
    "fileinput.FileInput": ("inplace", (0, "files")),
}
# Database names that are not files.
_PYTHON_NO_FILE_NAMES = {":memory:", ""}
# Calls that load and run code from a file or a module the program names, or a
# native library. What that code does is outside the syntax tree.
_PYTHON_LOADER_CALLS = {
    "runpy.run_path",
    "runpy.run_module",
    "imp.load_source",
    "imp.load_module",
    "importlib.reload",
    "importlib.util.spec_from_file_location",
    "importlib.machinery.SourceFileLoader",
    "importlib.machinery.SourcelessFileLoader",
    "importlib.machinery.ExtensionFileLoader",
    "zipimport.zipimporter",
    "site.addsitedir",
    "ctypes.CDLL",
    "ctypes.PyDLL",
    "ctypes.WinDLL",
    "ctypes.OleDLL",
    "ctypes.cdll.LoadLibrary",
    "ctypes.windll.LoadLibrary",
}
# Calls that start another program. What that program does is outside the
# syntax tree, so each one is a write the gate cannot place.
_PYTHON_SPAWN_CALLS = {"os.system", "os.popen", "os.startfile", "pty.spawn", "platform.popen"}
_PYTHON_SPAWN_PREFIXES = ("subprocess.", "os.exec", "os.spawn", "os.posix_spawn", "asyncio.create_subprocess_")
# Calls that run a string as Python. A literal string is read like the rest of
# the program, anything else is code the gate cannot see.
_PYTHON_CODE_CALLS = {"exec", "eval", "compile", "builtins.exec", "builtins.eval", "builtins.compile"}
_PYTHON_IMPORT_CALLS = {"__import__", "builtins.__import__", "importlib.import_module"}
# Modules whose attributes, looked up by a computed name, may be any of the
# calls above. A getattr on one of them with a name the gate cannot read is a
# write it cannot place.
_PYTHON_WATCHED_MODULES = {"os", "shutil", "subprocess", "pathlib", "io", "codecs", "builtins", "pty", "posix", "nt"}
_PYTHON_MAX_EXEC_DEPTH = 3
# The name segment standing for a module or attribute chosen at run time.
_COMPUTED = "?"
# Path methods by what they do to the path they are called on. The first
# set has no namesake on str, so it counts on any receiver. The others share
# a name with a str or file method, so they count only on a known Path.
_PYTHON_PATH_ONLY_WRITES = {"write_text", "write_bytes", "symlink_to", "hardlink_to", "link_to"}
# Path methods that link two names to one file: a write through either name
# lands in the other, so the argument is written as well as the receiver.
_PYTHON_PATH_HARD_LINKS = {"hardlink_to", "link_to"}
_PYTHON_PATH_WRITES = {"touch", "mkdir"}
_PYTHON_PATH_REMOVES = {"unlink", "rmdir"}
_PYTHON_PATH_MOVES = {"rename", "replace"}
_PYTHON_OS_OPEN_WRITE_RE = re.compile(r"O_(?:WRONLY|RDWR|CREAT|TRUNC|APPEND)")
_UNPLACEABLE_PYTHON_TARGET = "python -c (a write whose path the gate cannot place)"
# A Perl open mode, alone ('>', '+<', '>>:utf8') or leading a two-argument
# path ('>out.txt'), where the rest is the file.
_PERL_MODE_RE = re.compile(r"^\+?(?:<|>>?|\|)(?::\S*)?$")
_PERL_WRITE_PREFIX_RE = re.compile(r"^\s*(?:\+?>|\+<)")
_PERL_MODE_PREFIX_RE = re.compile(r"^\s*\+?(?:>>?|<)\s*(?=[^\s:])")
_UNPLACEABLE_SCRIPT_TARGET = "inline code (a write or a process the gate cannot place)"


class _ScriptLanguage(NamedTuple):
    """How to read a one-line program in a language the gate does not parse.

    writes: a call that writes, renames or deletes a file.
    opens: an open call that writes only when handed a write mode.
    spawns: a call that runs a process or evaluates code, which the gate cannot place.
    """

    writes: "re.Pattern[str]"
    opens: "re.Pattern[str]"
    spawns: "re.Pattern[str]"


_PERL_LANGUAGE = _ScriptLanguage(
    re.compile(
        r"\b(?:unlink|rename|mkdir|rmdir|link|symlink|truncate|utime|chmod|chown|sysopen|copy|move|make_path|"
        r"mkpath|remove_tree|rmtree)\b|File::(?:Copy|Path)"
    ),
    re.compile(r"\bopen\s*(?:\(|my\b|\$|[A-Z_]+\s*,)"),
    re.compile(r"\b(?:system|exec|qx|eval|fork|syscall)\b|`|\bopen\s*\(?[^;]*['\"]\s*\||\|\s*['\"]|-\|"),
)
_RUBY_LANGUAGE = _ScriptLanguage(
    re.compile(
        r"\bFile\s*\.\s*(?:write|binwrite|delete|unlink|rename|symlink|link|truncate|chmod|chown)\b"
        r"|\bIO\s*\.\s*(?:write|binwrite)\b|\bFileUtils\b|\bDir\s*\.\s*(?:mkdir|rmdir|delete|unlink)\b"
    ),
    re.compile(r"\b(?:File|IO)\s*\.\s*(?:open|new)\b|\bopen\s*\("),
    re.compile(r"\b(?:system|exec|spawn|fork|eval|instance_eval|class_eval)\b|`|%x|\bIO\s*\.\s*popen\b|\bOpen3\b|\bopen\s*\(\s*['\"]\|"),
)
_PHP_LANGUAGE = _ScriptLanguage(
    re.compile(
        r"\b(?:file_put_contents|unlink|rename|copy|mkdir|rmdir|touch|tempnam|symlink|link|chmod|chown|ftruncate|"
        r"move_uploaded_file)\s*\("
    ),
    re.compile(r"\b(?:fopen|SplFileObject|gzopen)\s*\("),
    re.compile(r"\b(?:system|exec|shell_exec|passthru|popen|proc_open|pcntl_exec|eval|assert|create_function|call_user_func\w*)\s*\(|`"),
)
_LUA_LANGUAGE = _ScriptLanguage(
    re.compile(r"\bio\s*\.\s*output\s*\(|\bos\s*\.\s*(?:remove|rename|tmpname)\s*\("),
    re.compile(r"\bio\s*\.\s*open\s*\("),
    re.compile(r"\bos\s*\.\s*execute\b|\bio\s*\.\s*popen\b|\bload(?:string)?\s*\(|\bpackage\s*\.\s*loadlib\b"),
)
_R_LANGUAGE = _ScriptLanguage(
    re.compile(
        r"\b(?:writeLines|sink|file\.create|file\.remove|file\.rename|file\.copy|file\.append|file\.symlink|"
        r"file\.link|unlink|dir\.create|saveRDS|save|save\.image|write\.csv2?|write\.table|writeBin|writeChar|"
        r"download\.file|zip|unzip|untar|tar)\s*\(|\bfile\s*="
    ),
    re.compile(r"\b(?:file|gzfile|bzfile|xzfile)\s*\("),
    re.compile(r"\b(?:system2?|shell|shell\.exec|pipe|eval|evalq|parse|do\.call|match\.fun)\s*\("),
)
_JULIA_LANGUAGE = _ScriptLanguage(
    re.compile(r"\b(?:rm|mv|cp|touch|mkdir|mkpath|symlink|hardlink|chmod|chown|download|writedlm|truncate)\s*\("),
    re.compile(r"\bopen\s*\("),
    re.compile(r"\b(?:run|pipeline|eval|include_string|ccall)\b|Meta\s*\.\s*parse|@eval|`"),
)
_SCRIPT_LANGUAGES = {
    "perl": _PERL_LANGUAGE,
    "ruby": _RUBY_LANGUAGE,
    "php": _PHP_LANGUAGE,
    "lua": _LUA_LANGUAGE,
    "luajit": _LUA_LANGUAGE,
    "r": _R_LANGUAGE,
    "rscript": _R_LANGUAGE,
    "julia": _JULIA_LANGUAGE,
}

_ENCODING_LITERAL_RE = re.compile(
    r"^(?:utf-?(?:8|16|32)(?:-?(?:le|be|sig))?|ascii|latin-?1|ucs-?2|binary|base64|hex)$",
    re.IGNORECASE,
)


def _is_path_type(name: str) -> bool:
    return name.rsplit(".", 1)[-1] in _PYTHON_PATH_TYPES


def _is_known_python_call(name: str) -> bool:
    return (
        name in _PYTHON_WRITE_CALLS
        or name in _PYTHON_OPEN_CALLS
        or name in _PYTHON_SPAWN_CALLS
        or name.startswith(_PYTHON_SPAWN_PREFIXES)
    )


class _PythonNames:
    """The dotted module path every imported or rebound name stands for.

    `import os as o`, `from shutil import rmtree`, `from os import *`, and
    `o = __import__('os')` all bind a local name to a module or a function,
    and a call through that name is judged as a call through the full path.
    """

    def __init__(self, tree: ast.AST) -> None:
        self.aliases: Dict[str, str] = {}
        self.stars: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        self.aliases[alias.asname] = alias.name
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    if alias.name == "*":
                        self.stars.append(node.module)
                    else:
                        self.aliases[alias.asname or alias.name] = node.module + "." + alias.name

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                module = self.imported(node.value)

                if module:
                    self.aliases[node.targets[0].id] = module

    def qualified(self, node: ast.AST) -> str:
        """The dotted name an expression refers to, or "" when it is not a name."""
        if isinstance(node, ast.Name):
            if node.id in self.aliases:
                return self.aliases[node.id]

            starred = [module + "." + node.id for module in self.stars]

            return next((name for name in starred if _is_known_python_call(name)), node.id)

        if isinstance(node, ast.Attribute):
            owner = self.qualified(node.value)
            return owner + "." + node.attr if owner else ""

        if isinstance(node, ast.Call):
            return self.imported(node) or self._looked_up(node)

        return ""

    def imported(self, node: ast.AST) -> str:
        """The module an __import__ or import_module call loads, if it is one."""
        if not isinstance(node, ast.Call) or not node.args:
            return ""

        if self.qualified(node.func) not in _PYTHON_IMPORT_CALLS:
            return ""

        module = node.args[0]

        if isinstance(module, ast.Constant) and isinstance(module.value, str):
            return module.value

        return _COMPUTED

    def _looked_up(self, call: ast.Call) -> str:
        """The attribute a getattr call reads, spelled as a dotted name."""
        if self.qualified(call.func) not in ("getattr", "builtins.getattr") or len(call.args) < 2:
            return ""

        owner = self.qualified(call.args[0])
        attribute = call.args[1]

        if not owner:
            return ""

        if isinstance(attribute, ast.Constant) and isinstance(attribute.value, str):
            return owner + "." + attribute.value

        return owner + "." + _COMPUTED


def _is_computed_call(name: str) -> bool:
    """True for a call through a module or attribute chosen at run time."""
    parts = name.split(".")

    if _COMPUTED not in parts:
        return False

    return parts[0] == _COMPUTED or parts[0] in _PYTHON_WATCHED_MODULES


class _PythonScope:
    """What each name was last assigned, as far as a literal reveals it."""

    def __init__(self, tree: ast.AST, names: _PythonNames) -> None:
        self.names = names
        self.values: Dict[str, Optional[str]] = {}
        self.paths: Set[str] = set()

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue

            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.values[target.id] = self.value(node.value)

                    if self.is_path(node.value):
                        self.paths.add(target.id)

    def value(self, node: ast.AST) -> Optional[str]:
        """The string a path expression evaluates to, or None when unknown."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value

        if isinstance(node, ast.Name):
            return self.values.get(node.id)

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._joined([node.left, node.right])

        if isinstance(node, ast.Call) and _is_path_type(self.names.qualified(node.func)):
            return self._joined(node.args) if node.args else "."

        return None

    def is_path(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id in self.paths

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.is_path(node.left)

        return isinstance(node, ast.Call) and _is_path_type(self.names.qualified(node.func))

    def _joined(self, parts: List[ast.AST]) -> Optional[str]:
        values = [self.value(part) for part in parts]

        if any(value is None for value in values):
            return None

        return "/".join(value for value in values if value is not None)


def _argument(call: ast.Call, position: int, keyword: str = "") -> Optional[ast.AST]:
    if position < len(call.args):
        return call.args[position]

    return next((item.value for item in call.keywords if keyword and item.arg == keyword), None)


def _opens_for_writing(call: ast.Call, name: str) -> bool:
    if name == "os.open":
        flags = _argument(call, 1, "flags")
        return flags is not None and bool(_PYTHON_OS_OPEN_WRITE_RE.search(ast.unparse(flags)))

    return _is_write_mode(_argument(call, 1, "mode"))


def _is_write_mode(mode: Optional[ast.AST]) -> bool:
    """True for a mode that writes, and for one the gate cannot read."""
    if mode is None:
        return False

    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(char in mode.value for char in "wax+")

    return True


def _python_executed(call: ast.Call, depth: int) -> Tuple[List[Optional[str]], List[Optional[str]]]:
    """What a string handed to exec, eval, or compile writes when it runs."""
    source = _argument(call, 0, "source")

    if not (isinstance(source, ast.Constant) and isinstance(source.value, str)):
        return [None], []

    if depth >= _PYTHON_MAX_EXEC_DEPTH:
        return [None], []

    try:
        tree = ast.parse(source.value)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return [], []

    return _python_writes(tree, depth + 1)


def _loads_unread_code(module: str) -> bool:
    """True when importing a module may run code outside the standard library.

    That is any module the standard library does not ship, a relative import,
    and a standard module shadowed by a file of the same name in the directory
    the program runs in, which `python -c` searches first.
    """
    top = module.split(".", 1)[0]

    if not top:
        return True

    if top in sys.builtin_module_names:
        return False

    if top not in getattr(sys, "stdlib_module_names", frozenset()):
        return True

    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())
    shadows = (top + ".py", top + ".pyc", top + ".pyd", top + ".so", top + "/__init__.py")

    for base in bases:
        try:
            if any((base / shadow).exists() for shadow in shadows):
                return True
        except (OSError, ValueError):
            return True

    return False


def _imports_unread_code(call: ast.Call) -> bool:
    """True for an __import__ or import_module call whose module is computed or loads code the gate cannot read."""
    module = _argument(call, 0, "name")

    if not (isinstance(module, ast.Constant) and isinstance(module.value, str)):
        return True

    return _loads_unread_code(module.value)


def _keyword_writes(call: ast.Call, name: str, scope: "_PythonScope") -> List[Optional[str]]:
    """What a call in _PYTHON_KEYWORD_WRITES writes, going by the keyword that turns the write on."""
    keyword, files = _PYTHON_KEYWORD_WRITES[name]
    value = next((item.value for item in call.keywords if item.arg == keyword), None)

    if value is None or (isinstance(value, ast.Constant) and not value.value):
        return []

    if not files:
        return [scope.value(value)]

    argument = _argument(call, files[0], files[1])

    return [scope.value(argument) if argument is not None else None]


def _python_writes(tree: ast.AST, depth: int = 0) -> Tuple[List[Optional[str]], List[Optional[str]]]:
    """Every path the program writes and every path it takes away.

    A None entry is a write the gate cannot place.
    """
    names = _PythonNames(tree)
    scope = _PythonScope(tree, names)
    written: List[Optional[str]] = []
    removed: List[Optional[str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            written += [None for alias in node.names if _loads_unread_code(alias.name)]
            continue

        if isinstance(node, ast.ImportFrom):
            if node.level or _loads_unread_code(node.module or ""):
                written.append(None)
            continue

        if not isinstance(node, ast.Call):
            continue

        name = names.qualified(node.func)

        if name in _PYTHON_SPAWN_CALLS or name.startswith(_PYTHON_SPAWN_PREFIXES) or _is_computed_call(name):
            written.append(None)
            continue

        if name in _PYTHON_LOADER_CALLS or (name in _PYTHON_IMPORT_CALLS and _imports_unread_code(node)):
            written.append(None)
            continue

        if name in _PYTHON_KEYWORD_WRITES:
            written += _keyword_writes(node, name, scope)
            continue

        if name in _PYTHON_CODE_CALLS:
            executed_written, executed_removed = _python_executed(node, depth)
            written += executed_written
            removed += executed_removed
            continue

        if name in _PYTHON_OPEN_CALLS or name == "os.open":
            if _opens_for_writing(node, name):
                path = _argument(node, 0, "file" if name != "os.open" else "path")
                written.append(scope.value(path) if path is not None else None)
            continue

        if name in _PYTHON_WRITE_CALLS:
            spec = _PYTHON_WRITE_CALLS[name]
            for bucket, positions in ((written, spec.written), (removed, spec.removed)):
                for position in positions:
                    argument = _argument(node, position)
                    value = scope.value(argument) if argument is not None else None
                    bucket += [] if value in _PYTHON_NO_FILE_NAMES else [value]
            continue

        if not isinstance(node.func, ast.Attribute):
            continue

        method = node.func.attr
        receiver = node.func.value
        known_path = scope.is_path(receiver)

        if method in _PYTHON_PATH_ONLY_WRITES or (known_path and method in _PYTHON_PATH_WRITES):
            written.append(scope.value(receiver))

            if method in _PYTHON_PATH_HARD_LINKS:
                source = _argument(node, 0, "target")
                written.append(scope.value(source) if source is not None else None)
        elif method in ("extractall", "extract"):
            destination = _argument(node, 0 if method == "extractall" else 1, "path")
            written.append(scope.value(destination) if destination is not None else ".")
        elif known_path and method in _PYTHON_PATH_REMOVES:
            removed.append(scope.value(receiver))
        elif known_path and method in _PYTHON_PATH_MOVES:
            removed.append(scope.value(receiver))
            destination = _argument(node, 0, "target")
            written.append(scope.value(destination) if destination is not None else None)
        elif known_path and method == "open" and _is_write_mode(_argument(node, 0, "mode")):
            written.append(scope.value(receiver))

    return written, removed


def _python_code_targets(code: str, powershell: bool = False) -> List[str]:
    """Paths an inline Python program writes, read from its syntax tree.

    Code that does not parse is allowed, because Python refuses to run it. A
    write whose path is not a literal the gate can follow is a path it cannot
    place, which denies, the same as the boundary helpers. So is a call that
    starts another process, a module or attribute picked at run time, and a
    string run through exec or eval that is not itself a literal.
    """
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        return []

    written, removed = _python_writes(tree)
    targets = _sourced([path for path in written if path is not None], powershell)
    targets += _removal_sourced([path for path in removed if path is not None], powershell)

    if None in written or None in removed:
        targets.append(_UNPLACEABLE_PYTHON_TARGET)

    return targets


# Inline JavaScript has no parser in the standard library, so the gate reads
# the file-system calls it knows by name and takes their path arguments only
# when each one is a plain string literal. Anything else in a path position
# is a path it cannot place, which denies.
_JS_TOOLS = {"node", "nodejs", "bun", "deno"}
_JS_WRITE_CALLS = {
    "writeFile": _PythonWrite(written=(0,)),
    "appendFile": _PythonWrite(written=(0,)),
    "createWriteStream": _PythonWrite(written=(0,)),
    "truncate": _PythonWrite(written=(0,)),
    "mkdir": _PythonWrite(written=(0,)),
    "rm": _PythonWrite(removed=(0,)),
    "rmdir": _PythonWrite(removed=(0,)),
    "unlink": _PythonWrite(removed=(0,)),
    "rename": _PythonWrite(written=(1,), removed=(0,)),
    "copyFile": _PythonWrite(written=(1,)),
    "cp": _PythonWrite(written=(1,)),
    "symlink": _PythonWrite(written=(1,)),
    "link": _PythonWrite(written=(0, 1)),
    "DatabaseSync": _PythonWrite(written=(0,)),
    "Database": _PythonWrite(written=(0,)),
    "Bun.write": _PythonWrite(written=(0,)),
    "Deno.writeTextFile": _PythonWrite(written=(0,)),
    "Deno.writeFile": _PythonWrite(written=(0,)),
    "Deno.create": _PythonWrite(written=(0,)),
    "Deno.mkdir": _PythonWrite(written=(0,)),
    "Deno.truncate": _PythonWrite(written=(0,)),
    "Deno.remove": _PythonWrite(removed=(0,)),
    "Deno.rename": _PythonWrite(written=(1,), removed=(0,)),
    "Deno.copyFile": _PythonWrite(written=(1,)),
    "Deno.symlink": _PythonWrite(written=(1,)),
    "Deno.link": _PythonWrite(written=(0, 1)),
}
_JS_IDENTIFIER = r"[A-Za-z_$][\w$]*"
_JS_CALL_RE = re.compile(r"(?<![\w$])(?:(?P<owner>Bun|Deno)\s*\.\s*)?(?P<ident>" + _JS_IDENTIFIER + r")\s*\(")
# Starting a process, or running a string as code. What either one does is
# outside the text the gate reads, so each is a write it cannot place. A
# require or import of a name that is not a literal may load any module.
_JS_OPAQUE_RE = re.compile(
    r"child_process|\bBun\s*\.\s*(?:spawn|spawnSync|\$)|\bDeno\s*\.\s*(?:Command|run)\b"
    r"|(?<![\w$.])eval\s*\(|(?<![\w$.])(?:new\s+)?Function\s*\(|\bvm\s*\.\s*run"
    r"|\b(?:require|import)\s*\(\s*[^\s'\"`]"
    r"|\bprocess\s*\.\s*(?:dlopen|binding)\b|\bcreateRequire\b|\bnew\s+Worker\s*\(",
)
# A module specifier handed to require, import() or an import statement.
_JS_SPECIFIER_RE = re.compile(
    r"\b(?:require|import)\s*\(\s*(?P<quote>['\"`])(?P<call>[^'\"`]*)(?P=quote)"
    r"|\b(?:from|import)\s*(?P<squote>['\"])(?P<static>[^'\"]*)(?P=squote)"
)
# Node's built-in modules. Any other specifier loads a file of the project,
# a package installed into it, or code from a URL.
_JS_BUILTIN_MODULES = {
    "assert",
    "async_hooks",
    "buffer",
    "child_process",
    "cluster",
    "console",
    "constants",
    "crypto",
    "dgram",
    "diagnostics_channel",
    "dns",
    "events",
    "fs",
    "http",
    "http2",
    "https",
    "inspector",
    "module",
    "net",
    "os",
    "path",
    "perf_hooks",
    "process",
    "punycode",
    "querystring",
    "readline",
    "repl",
    "stream",
    "string_decoder",
    "timers",
    "tls",
    "trace_events",
    "tty",
    "url",
    "util",
    "v8",
    "vm",
    "wasi",
    "worker_threads",
    "zlib",
}
# A name bound to a whole module, whose members a computed lookup can reach.
_JS_MODULE_BINDING_RE = re.compile(
    r"\b(?:const|let|var)\s+(" + _JS_IDENTIFIER + r")\s*=\s*(?:await\s+)?(?:require|import)\s*\("
    r"|\bimport\s+(?:\*\s+as\s+)?(" + _JS_IDENTIFIER + r")\s+from\b"
)
# Renames that give a file-system call a new local name.
_JS_DESTRUCTURE_RE = re.compile(
    r"\{([^{}]*)\}\s*=\s*(?:await\s+)?(?:require|import)\s*\(|\bimport\s*\{([^{}]*)\}\s*from\b"
)
_JS_RENAME_RE = re.compile(r"^\s*(" + _JS_IDENTIFIER + r")\s*(?::|\s+as\s+)\s*(" + _JS_IDENTIFIER + r")\s*$")
_JS_MEMBER_ALIAS_RE = re.compile(
    r"\b(?:const|let|var)\s+(" + _JS_IDENTIFIER + r")\s*=\s*" + _JS_IDENTIFIER + r"(?:\s*\([^()]*\))?"
    + r"(?:\s*\.\s*" + _JS_IDENTIFIER + r")*\s*\.\s*(" + _JS_IDENTIFIER + r")\s*(?=[;,\n]|$)"
)
_JS_MODULE_OWNERS = ("fs", "fsp", "Bun", "Deno")
# The fs.open flags that write, see the Node.js file system flags reference.
_JS_WRITE_FLAGS = {"w", "wx", "w+", "wx+", "a", "ax", "a+", "ax+", "as", "as+", "r+", "rs+"}
_UNPLACEABLE_JS_TARGET = "inline JavaScript (a write whose path the gate cannot place)"


def _js_aliases(code: str) -> Dict[str, str]:
    """Every local name the code gives to a member of another object."""
    aliases: Dict[str, str] = {}

    for match in _JS_DESTRUCTURE_RE.finditer(code):
        for item in (match.group(1) or match.group(2)).split(","):
            renamed = _JS_RENAME_RE.match(item)

            if renamed:
                aliases[renamed.group(2)] = renamed.group(1)

    for match in _JS_MEMBER_ALIAS_RE.finditer(code):
        aliases[match.group(1)] = match.group(2)

    return aliases


def _js_loads_unread_code(code: str) -> bool:
    """True when the code loads a module that is not built into the runtime."""
    for match in _JS_SPECIFIER_RE.finditer(code):
        specifier = match.group("call") if match.group("call") is not None else match.group("static")
        name = specifier[len("node:") :] if specifier.startswith("node:") else specifier

        if specifier.startswith(("node:", "bun:")) or name.split("/", 1)[0] in _JS_BUILTIN_MODULES:
            continue

        return True

    return False


def _js_is_opaque(code: str) -> bool:
    """True when the code spawns, evaluates, loads a module file, or reaches a module member by a computed name."""
    if _JS_OPAQUE_RE.search(code) or _js_loads_unread_code(code):
        return True

    owners = set(_JS_MODULE_OWNERS)
    owners.update(name for match in _JS_MODULE_BINDING_RE.finditer(code) for name in match.groups() if name)
    owner = "(?<![\\w$.])(?:" + "|".join(re.escape(name) for name in sorted(owners)) + ")"
    module = r"\b(?:require|import)\s*\([^()]*\)"
    member = r"(?:\s*(?:\?\.|\.)\s*" + _JS_IDENTIFIER + r")*"
    computed = re.compile("(?:" + owner + "|" + module + ")" + member + r"\s*(?:\?\.\s*)?\[")

    return bool(computed.search(code))


def _js_literal(code: str, index: int) -> Tuple[Optional[str], int]:
    """A plain JavaScript string literal at index, and where it ends.

    Anything else, an escape or an interpolation included, is not a literal,
    and the index stays put so the caller skips the argument as code.
    """
    quote = code[index]

    if quote not in "'\"`":
        return None, index

    close = code.find(quote, index + 1)
    text = code[index + 1 : close] if close > 0 else ""

    if close > 0 and "\\" not in text and not (quote == "`" and "${" in text):
        return text, close + 1

    return None, index


def _js_arguments(
    code: str,
    start: int,
    count: int,
    read_literal: Callable[[str, int], Tuple[Optional[str], int]] = _js_literal,
) -> List[Optional[str]]:
    """The first count arguments after an opening parenthesis.

    A plain string literal comes back as its text, and anything else as None.
    """
    arguments: List[Optional[str]] = []
    index = start

    while len(arguments) < count and index < len(code):
        while index < len(code) and code[index] in " \t\r\n":
            index += 1

        if index >= len(code) or code[index] == ")":
            break

        literal, index = read_literal(code, index)
        depth = 0

        while index < len(code):
            char = code[index]

            if char in "([{":
                depth += 1
            elif char in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif char == "," and depth == 0:
                break
            elif char in "'\"`":
                close = code.find(char, index + 1)
                index = close if close > 0 else len(code)

            if literal is not None and not code[index].isspace():
                literal = None

            index += 1

        arguments.append(literal)

        if index < len(code) and code[index] == ",":
            index += 1
        else:
            break

    return arguments


def _js_code_targets(code: str, powershell: bool = False) -> List[str]:
    written: List[Optional[str]] = []
    removed: List[Optional[str]] = []
    aliases = _js_aliases(code)

    if _js_is_opaque(code):
        written.append(None)

    for match in _JS_CALL_RE.finditer(code):
        owner = match.group("owner")
        ident = aliases.get(match.group("ident"), match.group("ident"))
        base = ident[:-4] if ident.endswith("Sync") and len(ident) > 4 else ident
        name = owner + "." + base if owner else base

        if name == "open":
            mode = _js_arguments(code, match.end(), 2)

            if len(mode) == 2 and (mode[1] is None or mode[1] in _JS_WRITE_FLAGS):
                written.append(mode[0])
            continue

        spec = _JS_WRITE_CALLS.get(name)

        if spec is None:
            continue

        arguments = _js_arguments(code, match.end(), 1 + max(spec.written + spec.removed))

        for bucket, positions in ((written, spec.written), (removed, spec.removed)):
            for position in positions:
                bucket.append(arguments[position] if position < len(arguments) else None)

    written = [path for path in written if path not in _PYTHON_NO_FILE_NAMES]
    targets = _sourced([path for path in written if path is not None], powershell)
    targets += _removal_sourced([path for path in removed if path is not None], powershell)

    if None in written or None in removed:
        targets.append(_UNPLACEABLE_JS_TARGET)

    return targets


def _tee_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:]), powershell)


def _joined(directory: str, name: str) -> str:
    """name placed inside directory, spelled with a forward slash."""
    return directory.rstrip("/\\") + "/" + name


def _under(directory: str, path: str) -> str:
    """path as seen from directory, unless it is absolute or there is no directory."""
    if not directory or _as_path(path).is_absolute():
        return path

    return _joined(directory, path)


def _is_existing_directory(target: str) -> bool:
    """True when target names a directory on disk, from any base."""
    if _has_glob(target):
        return False

    path = _as_path(target)
    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())

    for base in bases:
        try:
            if (path if path.is_absolute() else base / path).is_dir():
                return True
        except (OSError, ValueError):
            continue

    return False


def _copy_destinations(sources: List[str], destination: str) -> List[str]:
    """Where each source lands: inside destination when it is a directory."""
    if not destination:
        return []

    if destination.endswith(("/", "\\")) or destination in (".", "..") or _is_existing_directory(destination):
        names = [PurePosixPath(source.replace("\\", "/")).name for source in sources]
        return [_joined(destination, name) for name in names if name] or [destination]

    return [destination]


def _links_hard(name: str, flags: List[str]) -> bool:
    """True when ln makes a hard link, which it does unless told -s, or cp is told -l."""
    short = [flag for flag in flags if flag.startswith("-") and not flag.startswith("--")]

    if name == "ln":
        return "--symbolic" not in flags and not any("s" in flag[1:] for flag in short)

    return name == "cp" and ("--link" in flags or any("l" in flag[1:] for flag in short))


def _copy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Where a copy, a move or a link lands, plus a hard link's own source.

    A hard link shares the file itself, so a link made outside the project,
    or at the task list, to a project file is a way to write that file later.
    rsync --link-dest hard-links every unchanged file out of that directory.
    """
    targets = _copy_landings(tokens, powershell)
    operands = _operands(tokens[1:], _COPY_VALUE_FLAGS)
    name = _basename(tokens[0])

    if name == "rsync":
        return targets + _sourced([value for _flag, value in _long_or_short_values(tokens, "--link-dest", "--link-dest")], powershell)

    if not _links_hard(name, tokens[1:]):
        return targets

    has_directory = any(token in ("-t", "--target-directory") or token.startswith("--target-directory=") for token in tokens)
    sources = operands if has_directory or len(operands) < 2 else operands[:-1]

    return targets + _sourced(sources, powershell)


def _copy_landings(tokens: List[str], powershell: bool = False) -> List[str]:
    directory = ""

    for index, token in enumerate(tokens):
        if token in ("-t", "--target-directory") and index + 1 < len(tokens):
            directory = tokens[index + 1]
        elif token.startswith("--target-directory="):
            directory = token.split("=", 1)[1]

    operands = _operands(tokens[1:], _COPY_VALUE_FLAGS)

    if _basename(tokens[0]) == "install" and any(_is_install_directory_flag(flag) for flag in tokens[1:]):
        return _sourced(operands, powershell)

    if directory:
        return _sourced(_copy_destinations(operands, directory.rstrip("/\\") + "/"), powershell)

    if len(operands) < 2:
        return []

    return _sourced(_copy_destinations(operands[:-1], operands[-1]), powershell)


def _is_install_directory_flag(flag: str) -> bool:
    """install -d creates every operand as a directory instead of copying."""
    return flag == "--directory" or (flag.startswith("-") and not flag.startswith("--") and "d" in flag[1:])


_FSUTIL_FILE_WRITES = {"createnew", "seteof", "setzerodata", "setvaliddata", "setshortname", "setcasesensitiveinfo"}


def _fsutil_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """fsutil hardlink create <new> <existing>, where both name the same file, and fsutil file writers."""
    words = [token.lower() for token in tokens[1:3]]

    if words == ["hardlink", "create"]:
        return _sourced(tokens[3:5], powershell)

    if len(tokens) > 3 and words[:1] == ["file"] and words[1:2] and words[1] in _FSUTIL_FILE_WRITES:
        return _sourced(tokens[3:4], powershell)

    return []


# A Windows tool's switch: /x, /x:value, or //x as Git Bash spells it so MSYS
# leaves it alone. A POSIX path such as /tmp also fits, which errs toward
# reading a destination as a switch and so toward the current directory.
_WINDOWS_SWITCH_RE = re.compile(r"^//?[A-Za-z?][\w:+\-.*]*$")


def _is_windows_switch(token: str) -> bool:
    return bool(_WINDOWS_SWITCH_RE.match(token)) or token.startswith("-") and len(token) > 1


def _switches(tokens: List[str]) -> List[str]:
    return [token.lstrip("/-").lower() for token in tokens[1:] if _is_windows_switch(token)]


def _windows_operands(tokens: List[str], value_switches: AbstractSet[str] = frozenset()) -> List[str]:
    operands: List[str] = []
    skip = False

    for token in tokens[1:]:
        if skip:
            skip = False
        elif _is_windows_switch(token):
            skip = token.lstrip("/-").lower() in value_switches
        else:
            operands.append(token)

    return operands


def _xcopy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """xcopy and replace write into their second operand, or the current directory."""
    operands = _windows_operands(tokens)

    return _sourced(operands[1:2] or ["."], powershell) if operands else []


def _robocopy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """robocopy writes and purges the destination, and /MOV or /MOVE takes the source away."""
    operands = _windows_operands(tokens)

    if len(operands) < 2:
        return []

    moved = _removal_sourced(operands[:1], powershell) if {"mov", "move"} & set(_switches(tokens)) else []

    return _sourced(operands[1:2], powershell) + moved


def _expand_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """expand.exe writes its last operand, or the current directory when it names one file."""
    operands = _windows_operands(tokens)

    return _sourced(operands[-1:] if len(operands) > 1 else ["."], powershell) if operands else []


def _esentutl_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """esentutl /y copies to /d, and every other mode rewrites the database it names."""
    switches = _switches(tokens)

    if "y" in switches:
        return _sourced(_switch_values(tokens, "d"), powershell)

    return _sourced(_windows_operands(tokens, {"d", "l", "s", "t", "f", "o", "i"}), powershell)


def _switch_values(tokens: List[str], switch: str) -> List[str]:
    """Every value a /switch takes, as the next word or after a colon."""
    values: List[str] = []

    for index, token in enumerate(tokens[1:], start=1):
        if not _is_windows_switch(token):
            continue

        name, _colon, attached = token.lstrip("/-").partition(":")

        if name.lower() != switch:
            continue

        if attached:
            values.append(attached)
        elif index + 1 < len(tokens):
            values.append(tokens[index + 1])

    return values


_CERTUTIL_CODECS = {"decode", "decodehex", "encode", "encodehex"}


def _certutil_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """certutil -decode and its kin write their second file, -urlcache -f its download."""
    switches = set(_switches(tokens))
    operands = _windows_operands(tokens)

    if switches & _CERTUTIL_CODECS:
        return _sourced(operands[1:2], powershell)

    if "urlcache" in switches and "f" in switches and operands:
        return _sourced(operands[1:2] or [_url_name(operands[0]) or _UNPLACEABLE_ARGUMENT], powershell)

    return []


def _bitsadmin_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """bitsadmin downloads into each local file it names, and can be told to run a program."""
    switches = set(_switches(tokens))

    if "setnotifycmdline" in switches:
        return [_UNPLACEABLE_SHELL_TARGET]

    operands = _windows_operands(tokens, {"priority", "dynamic"})

    if "transfer" in switches and "upload" not in switches:
        return _sourced(operands[2::2], powershell)

    if "addfile" in switches:
        return _sourced(operands[2:3], powershell)

    return []


def _mklink_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """mklink writes the link, and /H makes a hard link whose target is the same file."""
    operands = _windows_operands(tokens)
    linked = operands[1:2] if "h" in _switches(tokens) else []

    return _sourced(operands[:1] + linked, powershell)


def _truncate_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:], _TRUNCATE_VALUE_FLAGS), powershell)


def _dd_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced([token[3:] for token in tokens[1:] if token.startswith("of=")], powershell)


def _touch_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:], _TOUCH_VALUE_FLAGS), powershell)


def _mkdir_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _sourced(_operands(tokens[1:], _MKDIR_VALUE_FLAGS), powershell)


def _url_name(url: str) -> str:
    """The file name a download keeps from its URL, or "" when there is none."""
    location = url.split("?", 1)[0].split("#", 1)[0].split("://", 1)[-1]

    return location.rsplit("/", 1)[-1] if "/" in location else ""


def _short_option_value(tokens: List[str], index: int, position: int) -> Tuple[str, int]:
    """The value of a short option at a position in a cluster, and the tokens it used."""
    token = tokens[index]
    attached = token[position + 1 :]

    if attached:
        return attached, 1

    return (tokens[index + 1], 2) if index + 1 < len(tokens) else ("", 1)


def _curl_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Files curl writes: -o and its kin, and -O named after the URL."""
    written: List[str] = []
    urls: List[str] = []
    directory = ""
    remote = False
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token.startswith("--"):
            flag, equals, inline = token.partition("=")
            value = inline if equals else (tokens[index + 1] if index + 1 < len(tokens) else "")

            if flag in _CURL_REMOTE_LONGS:
                remote = True
            elif flag == "--output-dir":
                directory = value
            elif flag in _CURL_WRITE_LONGS:
                written.append(value)
            else:
                index += 1
                continue

            index += 1 if equals or flag in _CURL_REMOTE_LONGS else 2
            continue

        if token.startswith("-") and len(token) > 1:
            used = 1

            for position, char in enumerate(token[1:], start=1):
                if char == "O":
                    remote = True
                    continue

                if char in _CURL_VALUE_SHORTS:
                    value, used = _short_option_value(tokens, index, position)

                    if char in _CURL_WRITE_SHORTS:
                        written.append(value)
                    break

            index += used
            continue

        urls.append(token)
        index += 1

    if remote:
        written += [name for name in (_url_name(url) for url in urls) if name]

    written = [_under(directory, path) for path in written if path and path != "-"]

    return _sourced(written, powershell)


def _wget_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Files wget writes: the document, its logs, and by default the URL's file name."""
    written: List[str] = []
    urls: List[str] = []
    document: Optional[str] = None
    prefix = ""
    spider = False
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token.startswith("--"):
            flag, equals, inline = token.partition("=")
            value = inline if equals else (tokens[index + 1] if index + 1 < len(tokens) else "")
            used = 1 if equals else 2

            if flag == "--spider":
                spider = True
                used = 1
            elif flag == "--output-document":
                document = value
            elif flag in ("--output-file", "--append-output"):
                written.append(value)
            elif flag == "--directory-prefix":
                prefix = value
            else:
                used = 1

            index += used
            continue

        if token.startswith("-") and len(token) > 1:
            used = 1

            for position, char in enumerate(token[1:], start=1):
                if char in _WGET_VALUE_SHORTS:
                    value, used = _short_option_value(tokens, index, position)

                    if char == "O":
                        document = value
                    elif char in "oa":
                        written.append(value)
                    elif char == "P":
                        prefix = value
                    break

            index += used
            continue

        urls.append(token)
        index += 1

    if document is not None:
        written.append(document)
    elif not spider:
        written += [_under(prefix, _url_name(url) or "index.html") for url in urls]

    return _sourced([path for path in written if path and path != "-"], powershell)


def _tar_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Where tar extracts to, or the archive it creates, appends to, or updates."""
    rest = tokens[1:]
    letters = ""
    archive = ""
    directory = "."

    if rest and not rest[0].startswith("-"):
        letters = rest[0]
        rest = rest[1:]

        if "f" in letters and rest:
            archive = rest[0]
            rest = rest[1:]

    index = 0

    while index < len(rest):
        token = rest[index]

        if token.startswith("--"):
            flag, equals, inline = token.partition("=")
            value = inline if equals else (rest[index + 1] if index + 1 < len(rest) else "")

            if flag in ("--directory", "--file"):
                directory, archive = (value, archive) if flag == "--directory" else (directory, value)
                index += 1 if equals else 2
                continue

            letters += _TAR_LONG_MODES.get(flag, "")
            index += 1
            continue

        if token.startswith("-") and len(token) > 1:
            used = 1

            for position, char in enumerate(token[1:], start=1):
                if char in "fC":
                    value, used = _short_option_value(rest, index, position)
                    directory, archive = (value, archive) if char == "C" else (directory, value)
                    break

                letters += char

            index += used
            continue

        index += 1

    if "x" in letters:
        return _sourced([directory], powershell)

    if any(mode in letters for mode in "cru") and archive and archive != "-":
        return _sourced([archive], powershell)

    return []


def _unzip_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Where unzip extracts to, which is the working directory unless -d names one."""
    flags = tokens[1:]

    if any(flag in _UNZIP_READ_FLAGS for flag in flags):
        return []

    directory = next(
        (flags[index + 1] for index, flag in enumerate(flags[:-1]) if flag == "-d"),
        next((flag[2:] for flag in flags if flag.startswith("-d") and len(flag) > 2), "."),
    )

    return _sourced([directory], powershell)


def _removal_sourced(candidates: List[str], powershell: bool = False) -> List[str]:
    """Candidates a removal or a move would take away from the repository."""
    return [candidate for candidate in candidates if _is_removal_target(candidate, powershell)]


def _remove_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _removal_sourced(_operands(tokens[1:]), powershell)


def _move_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """What mv writes to, plus every source it would take out of place.

    With -t every operand is a source, otherwise the last one is the
    destination and everything before it is a source.
    """
    operands = _operands(tokens[1:], _COPY_VALUE_FLAGS)
    targeted = any(
        token in ("-t", "--target-directory") or token.startswith("--target-directory=")
        for token in tokens
    )
    sources = operands if targeted else operands[:-1]

    return _copy_targets(tokens, powershell) + _removal_sourced(sources, powershell)


def _patch_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """A patch writes whatever the diff says, so only a check run is allowed."""
    flags = tokens[1:]

    if any(flag in _PATCH_CHECK_FLAGS for flag in flags):
        return []

    named = _sourced(_operands(flags, _PATCH_VALUE_FLAGS), powershell)

    return named or [_basename(tokens[0])]


def _git_dry_run(flags: List[str]) -> bool:
    return any(
        flag == "--dry-run" or (flag.startswith("-") and not flag.startswith("--") and "n" in flag[1:])
        for flag in flags
    )


def _git_stash_paths(rest: List[str]) -> List[str]:
    """The working-tree paths a git stash invocation rewrites."""
    operands = _operands(rest, _GIT_STASH_VALUE_FLAGS)

    if operands and operands[0].lower() in _GIT_STASH_ACTIONS:
        action, pathspecs = operands[0].lower(), operands[1:]
    else:
        action, pathspecs = "push", operands

    if action == "push":
        return pathspecs or ["."]

    return ["."] if action in _GIT_STASH_WRITES else []


_GIT_COMMAND_KEYS = {
    "core.pager",
    "core.editor",
    "core.sshcommand",
    "core.fsmonitor",
    "core.hookspath",
    "core.askpass",
    "core.gitproxy",
    "sequence.editor",
    "diff.external",
    "gpg.program",
    "credential.helper",
    "uploadpack.packobjectshook",
}


def _git_config_runs_a_program(setting: str) -> bool:
    """True for a setting that makes git run a program, or read more settings, the gate cannot place."""
    key, _equals, value = setting.partition("=")
    key = key.lower()

    if key.startswith("alias."):
        return value.startswith("!") or not value

    return (
        key in _GIT_COMMAND_KEYS
        or key.startswith(("pager.", "filter.", "include.", "includeif."))
        or key.endswith((".textconv", ".command", ".driver", ".cmd"))
    )


# Options naming a file git writes its output to, on diff, log, show,
# format-patch, archive and the rest of the diff family. Git also takes any
# unambiguous prefix of a long option, so --out=x is --output=x.
_GIT_OUTPUT_OPTIONS = ("--output", "--output-directory")
_GIT_OUTPUT_PREFIX_MIN = len("--out")
_GIT_OUTPUT_SHORTS = {"format-patch": "-o", "archive": "-o"}
# Subcommands that start a program of the user's choosing, or a server.
_GIT_PROGRAM_SUBCOMMANDS = {"difftool", "mergetool", "instaweb", "web--browse"}
_GIT_CONFIG_VALUE_FLAGS = {"-f", "--file", "--blob", "--type", "--default", "--comment", "--value", "--url"}
_GIT_CONFIG_READ_FLAGS = {"--get", "--get-all", "--get-regexp", "--get-urlmatch", "-l", "--list", "--get-color", "--get-colorbool"}
_GIT_CONFIG_WRITE_FLAGS = {"--unset", "--unset-all", "--add", "--replace-all", "--rename-section", "--remove-section"}
_GIT_CONFIG_ACTIONS = {"get", "list", "set", "unset", "rename-section", "remove-section", "edit"}
_GIT_CONFIG_OUTSIDE_SCOPES = {"--global", "--system"}


def _git_output_option(token: str) -> Optional[str]:
    """The long output option a word spells, abbreviated or not, or None."""
    name = token.split("=", 1)[0]

    if name in _GIT_OUTPUT_OPTIONS:
        return name

    if len(name) >= _GIT_OUTPUT_PREFIX_MIN and "--output".startswith(name):
        return "--output"

    return None


def _git_output_files(subcommand: str, rest: List[str]) -> List[str]:
    """Every file or directory a git subcommand writes its output into."""
    files: List[str] = []
    short = _GIT_OUTPUT_SHORTS.get(subcommand)

    for index, token in enumerate(rest):
        following = rest[index + 1] if index + 1 < len(rest) else ""

        if token == "--":
            break

        if _git_output_option(token):
            files.append(token.split("=", 1)[1] if "=" in token else following)
        elif short and token == short:
            files.append(following)
        elif short and token.startswith(short) and len(token) > len(short):
            files.append(token[len(short) :])

    if subcommand == "format-patch" and not files and "--stdout" not in rest:
        files.append(".")

    if subcommand == "bundle":
        operands = _operands(rest)
        files += operands[1:2] if operands[:1] == ["create"] else []

    return [path for path in files if path]


def _git_config_targets(rest: List[str]) -> List[str]:
    """The configuration file a git config call writes, _UNPLACEABLE_SHELL_TARGET for a setting that runs a program."""
    flags = [token.split("=", 1)[0] for token in rest if token.startswith("-")]
    operands = _operands(rest, _GIT_CONFIG_VALUE_FLAGS)
    action = operands[0] if operands and operands[0] in _GIT_CONFIG_ACTIONS else ""
    arguments = operands[1:] if action else operands

    if action in ("get", "list") or any(flag in _GIT_CONFIG_READ_FLAGS for flag in flags):
        return []

    edits = action == "edit" or "-e" in flags or "--edit" in flags
    writes = edits or bool(action) or any(flag in _GIT_CONFIG_WRITE_FLAGS for flag in flags) or len(arguments) >= 2

    if not writes:
        return []

    setting = arguments[0] + "=" + (arguments[1] if len(arguments) > 1 else "") if arguments else ""

    if edits or (setting and _git_config_runs_a_program(setting)):
        return [_UNPLACEABLE_SHELL_TARGET]

    named = _option_value(["config"] + rest, ("-f", "--file"))

    if named:
        return [named]

    return [] if any(flag in _GIT_CONFIG_OUTSIDE_SCOPES for flag in flags) else [".git/config"]


def _git_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    index = 1
    directory = ""

    while index < len(tokens):
        token = tokens[index]

        if token == "-c" and index + 1 < len(tokens) and _git_config_runs_a_program(tokens[index + 1]):
            return [_UNPLACEABLE_SHELL_TARGET]

        if token.startswith("--config-env=") and _git_config_runs_a_program(token.split("=", 1)[1].rsplit("=", 1)[0] + "="):
            return [_UNPLACEABLE_SHELL_TARGET]

        if token in ("-C", "--work-tree") and index + 1 < len(tokens):
            directory = _under(directory, tokens[index + 1])
            index += 2
            continue

        if token.startswith("--work-tree="):
            directory = _under(directory, token.split("=", 1)[1])
            index += 1
            continue

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

    if subcommand in _GIT_PROGRAM_SUBCOMMANDS:
        return [_UNPLACEABLE_SHELL_TARGET]

    if subcommand == "grep" and any(token.startswith(("-O", "--open-files-in-pager")) for token in rest):
        return [_UNPLACEABLE_SHELL_TARGET]

    if subcommand == "config":
        written = _git_config_targets(rest)

        if written[:1] == [_UNPLACEABLE_SHELL_TARGET]:
            return written

        return _sourced([_under(directory, path) for path in written], powershell)

    outputs = _sourced([_under(directory, path) for path in _git_output_files(subcommand, rest)], powershell)

    return outputs + _git_subcommand_targets(subcommand, rest, directory, powershell)


def _git_subcommand_targets(subcommand: str, rest: List[str], directory: str, powershell: bool) -> List[str]:
    """The working-tree paths a git subcommand rewrites, read from `directory` when git -C named one."""

    def placed(paths: List[str]) -> List[str]:
        return _sourced([_under(directory, path) for path in paths], powershell)

    if subcommand in _GIT_PATCH_SUBCOMMANDS:
        if any(flag in _GIT_PATCH_CHECK_FLAGS for flag in rest):
            return []

        return _sourced([directory], powershell) if directory else ["git " + subcommand]

    if subcommand in _GIT_SWITCH_SUBCOMMANDS and any(flag in _GIT_FORCE_FLAGS for flag in rest):
        return placed(["."])

    if subcommand in _GIT_TREE_SUBCOMMANDS:
        if "--staged" in rest and "--worktree" not in rest and "-W" not in rest:
            return []

        if subcommand in _GIT_AMBIGUOUS_SUBCOMMANDS:
            return _checkout_targets(rest, powershell, directory)

        return placed(_operands(rest, _GIT_CHECKOUT_VALUE_FLAGS))

    if subcommand == "clean":
        return [] if _git_dry_run(rest) else placed(_operands(rest, {"-e", "--exclude"}) or ["."])

    if subcommand == "rm":
        if _git_dry_run(rest) or "--cached" in rest:
            return []

        return placed(_operands(rest, {"--pathspec-from-file"}) or ["."])

    if subcommand == "mv":
        return [] if _git_dry_run(rest) else placed(_operands(rest))

    if subcommand == "reset":
        return placed(["."]) if any(flag in _GIT_WORKTREE_RESETS for flag in rest) else []

    if subcommand == "stash":
        return placed(_git_stash_paths(rest))

    return []


def _checkout_targets(rest: List[str], powershell: bool = False, directory: str = "") -> List[str]:
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
    is rather than a file write. Every path is read from `directory` when a
    `git -C` named one.
    """
    if "--" in rest:
        split = rest.index("--")
        candidates = _operands(rest[:split], _GIT_CHECKOUT_VALUE_FLAGS)
        pathspecs = list(rest[split + 1 :])
    else:
        candidates = _operands(rest, _GIT_CHECKOUT_VALUE_FLAGS)
        pathspecs = []

    if not pathspecs and len(candidates) >= 2:
        return _sourced([_under(directory, path) for path in candidates[1:]], powershell)

    ambiguous = [
        candidate
        for candidate in candidates
        if candidate in _WILDCARD_PATHSPECS or _path_exists_in_repo(_under(directory, candidate))
    ]

    return _sourced([_under(directory, path) for path in pathspecs + ambiguous], powershell)


# PowerShell binds each argument to a named parameter, by name, by any
# unambiguous prefix of the name, by `-Name:value`, or by position, and it
# splits an unquoted comma list into an array. _ps_bind reproduces that for
# the cmdlets the gate judges, so `Copy-Item -Destination src/x -Path /tmp/a`
# and `Remove-Item a,..` place every path where PowerShell would.
class _Cmdlet(NamedTuple):
    positional: Tuple[str, ...]
    parameters: AbstractSet[str]
    aliases: Dict[str, str] = {}


_PS_UNBOUND = "*"
_PS_COMMON_VALUE_PARAMS = frozenset(
    {
        "-erroraction",
        "-ea",
        "-warningaction",
        "-wa",
        "-informationaction",
        "-infa",
        "-errorvariable",
        "-ev",
        "-warningvariable",
        "-wv",
        "-informationvariable",
        "-iv",
        "-outvariable",
        "-ov",
        "-outbuffer",
        "-ob",
        "-pipelinevariable",
        "-pv",
        "-progressaction",
        "-proga",
    }
)
_PS_PARAMETER_ALIASES = {"-lp": "-literalpath", "-pspath": "-literalpath"}
_PS_ITEM_FILTERS = frozenset({"-filter", "-include", "-exclude", "-credential"})
_PS_PATHS = frozenset({"-path", "-literalpath"})
_PS_CONTENT = _PS_PATHS | _PS_ITEM_FILTERS | {"-value", "-encoding", "-stream", "-delimiter"}
_PS_WEB = frozenset(
    {
        "-uri",
        "-outfile",
        "-method",
        "-body",
        "-headers",
        "-infile",
        "-contenttype",
        "-useragent",
        "-credential",
        "-sessionvariable",
        "-websession",
        "-timeoutsec",
        "-maximumredirection",
        "-proxy",
        "-form",
    }
)
_PS_CMDLETS = {
    "remove-item": _Cmdlet(("-path",), _PS_PATHS | _PS_ITEM_FILTERS | {"-stream"}),
    "set-content": _Cmdlet(("-path", "-value"), _PS_CONTENT),
    "add-content": _Cmdlet(("-path", "-value"), _PS_CONTENT),
    "clear-content": _Cmdlet(("-path",), _PS_PATHS | _PS_ITEM_FILTERS | {"-stream"}),
    "set-item": _Cmdlet(("-path", "-value"), _PS_PATHS | _PS_ITEM_FILTERS | {"-value"}),
    "out-file": _Cmdlet(
        ("-filepath", "-encoding"),
        frozenset({"-filepath", "-literalpath", "-encoding", "-inputobject", "-width"}),
        {"-path": "-filepath"},
    ),
    "tee-object": _Cmdlet(
        ("-filepath",),
        frozenset({"-filepath", "-literalpath", "-variable", "-inputobject", "-encoding"}),
        {"-path": "-filepath"},
    ),
    "export-csv": _Cmdlet(("-path",), _PS_PATHS | {"-delimiter", "-encoding", "-inputobject", "-usequotes"}),
    "export-clixml": _Cmdlet(("-path",), _PS_PATHS | {"-depth", "-encoding", "-inputobject"}),
    "new-item": _Cmdlet(
        ("-path",),
        frozenset({"-path", "-name", "-itemtype", "-value", "-credential"}),
        {"-target": "-value", "-type": "-itemtype"},
    ),
    "copy-item": _Cmdlet(("-path", "-destination"), _PS_PATHS | _PS_ITEM_FILTERS | {"-destination", "-tosession", "-fromsession"}),
    "move-item": _Cmdlet(("-path", "-destination"), _PS_PATHS | _PS_ITEM_FILTERS | {"-destination"}),
    "rename-item": _Cmdlet(("-path", "-newname"), _PS_PATHS | {"-newname", "-credential"}),
    "expand-archive": _Cmdlet(("-path", "-destinationpath"), _PS_PATHS | {"-destinationpath"}),
    "compress-archive": _Cmdlet(("-path", "-destinationpath"), _PS_PATHS | {"-destinationpath", "-compressionlevel"}),
    "invoke-webrequest": _Cmdlet(("-uri",), _PS_WEB),
    "invoke-restmethod": _Cmdlet(("-uri",), _PS_WEB),
    "invoke-expression": _Cmdlet(("-command",), frozenset({"-command"})),
    "start-transcript": _Cmdlet(("-path",), _PS_PATHS | {"-outputdirectory"}),
    "set-itemproperty": _Cmdlet(("-path", "-name", "-value"), _PS_PATHS | _PS_ITEM_FILTERS | {"-name", "-value", "-type"}),
    "start-process": _Cmdlet(
        ("-filepath", "-argumentlist"),
        frozenset(
            {
                "-filepath",
                "-argumentlist",
                "-workingdirectory",
                "-redirectstandardoutput",
                "-redirectstandarderror",
                "-redirectstandardinput",
                "-verb",
                "-windowstyle",
                "-credential",
                "-environment",
            }
        ),
        {"-args": "-argumentlist", "-path": "-filepath", "-rso": "-redirectstandardoutput", "-rse": "-redirectstandarderror"},
    ),
    "get-content": _Cmdlet(
        ("-path",),
        _PS_PATHS | _PS_ITEM_FILTERS | {"-encoding", "-totalcount", "-tail", "-readcount", "-delimiter", "-stream"},
    ),
}
# PowerShell's own aliases, honoured only where PowerShell reads the line,
# since several of them are real programs in a POSIX shell or in cmd.
_PS_ALIASES = {
    "ri": "remove-item",
    "rm": "remove-item",
    "rmdir": "remove-item",
    "rd": "remove-item",
    "del": "remove-item",
    "erase": "remove-item",
    "sc": "set-content",
    "ac": "add-content",
    "clc": "clear-content",
    "si": "set-item",
    "tee": "tee-object",
    "epcsv": "export-csv",
    "ni": "new-item",
    "md": "new-item",
    "mkdir": "new-item",
    "cpi": "copy-item",
    "cp": "copy-item",
    "copy": "copy-item",
    "mi": "move-item",
    "mv": "move-item",
    "move": "move-item",
    "rni": "rename-item",
    "ren": "rename-item",
    "epal": "export-alias",
    "epsn": "export-pssession",
    "sp": "set-itemproperty",
    "saps": "start-process",
    "start": "start-process",
    "iwr": "invoke-webrequest",
    "irm": "invoke-restmethod",
    "iex": "invoke-expression",
    "gc": "get-content",
    "cat": "get-content",
    "type": "get-content",
    "echo": "write-output",
    "write": "write-output",
}
# The aliases that name no program anywhere else, so they are safe to read
# as the cmdlet from any shell, as the gate always has.
_PS_PORTABLE_ALIASES = {"ri", "del", "erase", "ac", "clc", "ni", "cpi", "mi", "rni", "ren"}


def _is_number(token: str) -> bool:
    return token[1:].replace(".", "", 1).isdigit()


def _ps_parameter(name: str, cmdlet: _Cmdlet) -> str:
    """The value-taking parameter a -Name token selects, or "" for a switch."""
    name = cmdlet.aliases.get(name, _PS_PARAMETER_ALIASES.get(name, name))
    known = cmdlet.parameters | _PS_COMMON_VALUE_PARAMS

    if name in known:
        return name

    matches = [parameter for parameter in known if parameter.startswith(name)]

    return matches[0] if len(matches) == 1 else ""


def _ps_bind(tokens: List[str], cmdlet: _Cmdlet) -> Dict[str, List[str]]:
    """Every value a cmdlet call binds, keyed by lowercase parameter name.

    Values PowerShell would bind to no parameter the gate knows land under
    _PS_UNBOUND, so a caller can still judge them.
    """
    bound: Dict[str, List[str]] = {}
    positional: List[str] = []
    literal = False
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if not literal and token == "--":
            literal = True
            index += 1
            continue

        if not literal and token.startswith("-") and len(token) > 1 and not _is_number(token):
            name, colon, inline = token.partition(":")
            parameter = _ps_parameter(name.lower(), cmdlet)

            if not parameter:
                index += 1
                continue

            if colon:
                value = inline
                index += 1
            elif index + 1 < len(tokens):
                value = tokens[index + 1]
                index += 2
            else:
                break

            bound.setdefault(parameter, []).extend(_split_array(value))
            continue

        positional.append(token)
        index += 1

    free = [parameter for parameter in cmdlet.positional if parameter not in bound]

    for parameter, value in zip(free, positional, strict=False):
        bound.setdefault(parameter, []).extend(_split_array(value))

    bound[_PS_UNBOUND] = [item for value in positional[len(free) :] for item in _split_array(value)]

    return bound


def _ps_values(bound: Dict[str, List[str]], *parameters: str) -> List[str]:
    return [value for parameter in parameters for value in bound.get(parameter, [])]


def _ps_remove_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    bound = _ps_bind(tokens, _PS_CMDLETS["remove-item"])

    return _removal_sourced(_ps_values(bound, "-path", "-literalpath", _PS_UNBOUND), powershell)


def _ps_content_writer(cmdlet: str, *parameters: str) -> Callable[[List[str], bool], List[str]]:
    """A handler for a cmdlet that writes the item its path parameters name."""

    def targets(tokens: List[str], powershell: bool = False) -> List[str]:
        bound = _ps_bind(tokens, _PS_CMDLETS[cmdlet])

        return _sourced(_ps_values(bound, *parameters, _PS_UNBOUND), powershell)

    return targets


def _ps_new_item_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """New-Item writes -Name inside each -Path, or each -Path itself."""
    bound = _ps_bind(tokens, _PS_CMDLETS["new-item"])
    paths = _ps_values(bound, "-path")
    names = _ps_values(bound, "-name")

    if names:
        paths = [_under(path, name) for path in (paths or ["."]) for name in names]

    linked = []

    if any(kind.lower() == "hardlink" for kind in _ps_values(bound, "-itemtype")):
        linked = _ps_values(bound, "-value")

    return _sourced(paths + bound[_PS_UNBOUND] + linked, powershell)


def _ps_copy_bound(bound: Dict[str, List[str]], powershell: bool) -> List[str]:
    sources = _ps_values(bound, "-path", "-literalpath")
    destination = (_ps_values(bound, "-destination") or ["."])[0]

    return _sourced(_copy_destinations(sources, destination) + bound[_PS_UNBOUND], powershell)


def _ps_copy_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    return _ps_copy_bound(_ps_bind(tokens, _PS_CMDLETS["copy-item"]), powershell)


def _ps_move_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    bound = _ps_bind(tokens, _PS_CMDLETS["move-item"])
    moved = _removal_sourced(_ps_values(bound, "-path", "-literalpath"), powershell)

    return _ps_copy_bound(bound, powershell) + moved


def _ps_rename_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Rename-Item takes each path away and writes the new name beside it."""
    bound = _ps_bind(tokens, _PS_CMDLETS["rename-item"])
    paths = _ps_values(bound, "-path", "-literalpath")
    renamed = [
        _under(str(PurePosixPath(path.replace("\\", "/")).parent), name)
        for path in paths
        for name in _ps_values(bound, "-newname")
    ]

    return _removal_sourced(paths + bound[_PS_UNBOUND], powershell) + _sourced(renamed, powershell)


def _ps_expand_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Expand-Archive writes into -DestinationPath, or the current location."""
    bound = _ps_bind(tokens, _PS_CMDLETS["expand-archive"])

    return _sourced(_ps_values(bound, "-destinationpath") or ["."], powershell)


def _ps_transcript_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    bound = _ps_bind(tokens, _PS_CMDLETS["start-transcript"])

    return _sourced(_ps_values(bound, "-path", "-literalpath", "-outputdirectory", _PS_UNBOUND), powershell)


# The file parameters of the Export cmdlets. Export-ModuleMember writes no file.
_PS_EXPORT = _Cmdlet(
    ("-path",),
    _PS_PATHS | {"-filepath", "-outputmodule", "-destinationpath", "-destinationimagepath", "-outputdirectory"},
    {"-output": "-outputmodule"},
)


def _ps_export_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """Any Export-* cmdlet writes the file its path parameters, or its first word, name."""
    bound = _ps_bind(tokens, _PS_EXPORT)
    paths = _ps_values(bound, *sorted(_PS_EXPORT.parameters), _PS_UNBOUND)

    return _sourced(paths, powershell)


def _ps_process_redirects(tokens: List[str], powershell: bool = False) -> List[str]:
    bound = _ps_bind(tokens, _PS_CMDLETS["start-process"])

    return _sourced(_ps_values(bound, "-redirectstandardoutput", "-redirectstandarderror"), powershell)


def _ps_web_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    bound = _ps_bind(tokens, _PS_CMDLETS["invoke-webrequest"])

    return _sourced(_ps_values(bound, "-outfile"), powershell)


def _ps_download_targets(native: Callable[[List[str], bool], List[str]]) -> Callable[[List[str], bool], List[str]]:
    """curl or wget read in PowerShell, which is the web cmdlet in Windows
    PowerShell and the native program in PowerShell 7, so both readings count."""

    def targets(tokens: List[str], powershell: bool = False) -> List[str]:
        return _ps_web_targets(tokens, powershell) + native(_split_arrays(tokens), powershell)

    return targets


# Cmdlets whose path parameter also takes pipeline input, so
# `Get-ChildItem .. | Remove-Item -Recurse` names its path through the pipe.
_PS_PIPED_PATH_CMDLETS = {
    "remove-item",
    "set-content",
    "add-content",
    "clear-content",
    "set-item",
    "copy-item",
    "move-item",
    "rename-item",
    "new-item",
    "expand-archive",
    "set-itemproperty",
}
_PS_PIPED_REMOVALS = {"remove-item", "move-item", "rename-item"}
_UNPLACEABLE_PIPED_PATH = "PowerShell pipeline input (a path the gate cannot read)"


def _ps_piped_targets(name: str, tokens: List[str], feed: Callable[[], Optional[str]], powershell: bool) -> List[str]:
    """The paths a cmdlet with no path argument takes from the pipeline feeding it."""
    canonical = _PS_ALIASES.get(name, name)

    if canonical not in _PS_PIPED_PATH_CMDLETS:
        return []

    if _ps_values(_ps_bind(tokens, _PS_CMDLETS[canonical]), "-path", "-literalpath"):
        return []

    fed = feed()

    if fed is None:
        return []

    if fed == _UNKNOWN_INPUT:
        return [_UNPLACEABLE_PIPED_PATH]

    paths = [line.strip() for line in fed.splitlines() if line.strip()]

    return (_removal_sourced if canonical in _PS_PIPED_REMOVALS else _sourced)(paths, powershell)


_CMDLET_HANDLERS: Dict[str, Callable[[List[str], bool], List[str]]] = {
    "remove-item": _ps_remove_targets,
    "set-content": _ps_content_writer("set-content", "-path", "-literalpath"),
    "add-content": _ps_content_writer("add-content", "-path", "-literalpath"),
    "clear-content": _ps_content_writer("clear-content", "-path", "-literalpath"),
    "set-item": _ps_content_writer("set-item", "-path", "-literalpath"),
    "out-file": _ps_content_writer("out-file", "-filepath", "-literalpath"),
    "tee-object": _ps_content_writer("tee-object", "-filepath", "-literalpath"),
    "export-csv": _ps_content_writer("export-csv", "-path", "-literalpath"),
    "export-clixml": _ps_content_writer("export-clixml", "-path", "-literalpath"),
    "new-item": _ps_new_item_targets,
    "copy-item": _ps_copy_targets,
    "move-item": _ps_move_targets,
    "rename-item": _ps_rename_targets,
    "expand-archive": _ps_expand_targets,
    "compress-archive": _ps_content_writer("compress-archive", "-destinationpath"),
    "invoke-webrequest": _ps_web_targets,
    "invoke-restmethod": _ps_web_targets,
    "start-transcript": _ps_transcript_targets,
    "set-itemproperty": _ps_content_writer("set-itemproperty", "-path", "-literalpath"),
    "start-process": _ps_process_redirects,
}
_PS_DOWNLOADERS = {"curl": _ps_download_targets(_curl_targets), "wget": _ps_download_targets(_wget_targets)}

_WRITE_HANDLERS: Dict[str, Callable[[List[str], bool], List[str]]] = {
    "tee": _tee_targets,
    "truncate": _truncate_targets,
    "dd": _dd_targets,
    "git": _git_targets,
    "patch": _patch_targets,
    "gpatch": _patch_targets,
    "touch": _touch_targets,
    "mkdir": _mkdir_targets,
    "md": _mkdir_targets,
    "curl": _curl_targets,
    "wget": _wget_targets,
    "tar": _tar_targets,
    "bsdtar": _tar_targets,
    "unzip": _unzip_targets,
    "fsutil": _fsutil_targets,
    "xcopy": _xcopy_targets,
    "robocopy": _robocopy_targets,
    "esentutl": _esentutl_targets,
    "certutil": _certutil_targets,
    "bitsadmin": _bitsadmin_targets,
    "mklink": _mklink_targets,
}
# Programs whose names mean something else to a POSIX shell: coreutils expand
# converts tabs to standard output there.
_WINDOWS_ONLY_HANDLERS: Dict[str, Callable[[List[str], bool], List[str]]] = {
    "replace": _xcopy_targets,
    "expand": _expand_targets,
}
_WRITE_HANDLERS.update({name: _copy_targets for name in _COPY_TOOLS - _MOVE_TOOLS})
_WRITE_HANDLERS.update({name: _remove_targets for name in _REMOVE_TOOLS})
_WRITE_HANDLERS.update({name: _move_targets for name in _MOVE_TOOLS})
_WRITE_HANDLERS.update(_CMDLET_HANDLERS)
_WRITE_HANDLERS.update({name: _CMDLET_HANDLERS[_PS_ALIASES[name]] for name in _PS_PORTABLE_ALIASES})


def _handler_for(name: str, dialect: str) -> Tuple[Optional[Callable[[List[str], bool], List[str]]], bool]:
    """The write handler for a program, and whether it binds PowerShell arrays itself."""
    if dialect == _POWERSHELL:
        if name in _PS_DOWNLOADERS:
            return _PS_DOWNLOADERS[name], True

        canonical = _PS_ALIASES.get(name, name)

        if canonical in _PS_CMDLETS:
            return _CMDLET_HANDLERS.get(canonical), True

        if canonical.startswith("export-") and canonical not in _PS_CMDLETS and canonical != "export-modulemember":
            return _ps_export_targets, True

    handler = _WRITE_HANDLERS.get(name)

    if handler is None and dialect != _POSIX:
        handler = _WINDOWS_ONLY_HANDLERS.get(name)

    return handler, handler in _CMDLET_HANDLERS.values()


# .NET file-system calls PowerShell can make directly, as
# [System.IO.File]::WriteAllText(...) or [IO.Directory]::Delete(...). Their
# arguments sit in a parenthesised list the command lexer does not keep
# together, so the raw PowerShell text is searched for them instead.
_DOTNET_IO_RE = re.compile(
    r"\[\s*(?:System\s*\.\s*)?IO\s*\.\s*(?P<type>File|Directory|StreamWriter|FileStream)\s*\]"
    r"\s*::\s*(?P<method>\w+)\s*\(",
    re.IGNORECASE,
)
_DOTNET_IO_CALLS = {
    ("file", "writealltext"): _PythonWrite(written=(0,)),
    ("file", "writealllines"): _PythonWrite(written=(0,)),
    ("file", "writeallbytes"): _PythonWrite(written=(0,)),
    ("file", "writealltextasync"): _PythonWrite(written=(0,)),
    ("file", "writealllinesasync"): _PythonWrite(written=(0,)),
    ("file", "writeallbytesasync"): _PythonWrite(written=(0,)),
    ("file", "appendalltext"): _PythonWrite(written=(0,)),
    ("file", "appendalllines"): _PythonWrite(written=(0,)),
    ("file", "appendallbytes"): _PythonWrite(written=(0,)),
    ("file", "appendalltextasync"): _PythonWrite(written=(0,)),
    ("file", "appendalllinesasync"): _PythonWrite(written=(0,)),
    ("file", "appendallbytesasync"): _PythonWrite(written=(0,)),
    ("file", "appendtext"): _PythonWrite(written=(0,)),
    ("file", "create"): _PythonWrite(written=(0,)),
    ("file", "createtext"): _PythonWrite(written=(0,)),
    ("file", "createsymboliclink"): _PythonWrite(written=(0,)),
    ("file", "open"): _PythonWrite(written=(0,)),
    ("file", "openhandle"): _PythonWrite(written=(0,)),
    ("file", "openwrite"): _PythonWrite(written=(0,)),
    ("file", "encrypt"): _PythonWrite(written=(0,)),
    ("file", "decrypt"): _PythonWrite(written=(0,)),
    ("file", "setattributes"): _PythonWrite(written=(0,)),
    ("file", "setcreationtime"): _PythonWrite(written=(0,)),
    ("file", "setcreationtimeutc"): _PythonWrite(written=(0,)),
    ("file", "setlastaccesstime"): _PythonWrite(written=(0,)),
    ("file", "setlastaccesstimeutc"): _PythonWrite(written=(0,)),
    ("file", "setlastwritetime"): _PythonWrite(written=(0,)),
    ("file", "setlastwritetimeutc"): _PythonWrite(written=(0,)),
    ("file", "setunixfilemode"): _PythonWrite(written=(0,)),
    ("file", "delete"): _PythonWrite(removed=(0,)),
    ("file", "move"): _PythonWrite(written=(1,), removed=(0,)),
    ("file", "copy"): _PythonWrite(written=(1,)),
    ("file", "replace"): _PythonWrite(written=(1,), removed=(0,)),
    ("directory", "delete"): _PythonWrite(removed=(0,)),
    ("directory", "move"): _PythonWrite(written=(1,), removed=(0,)),
    ("directory", "createdirectory"): _PythonWrite(written=(0,)),
    ("directory", "createsymboliclink"): _PythonWrite(written=(0,)),
    ("directory", "setcreationtime"): _PythonWrite(written=(0,)),
    ("directory", "setcreationtimeutc"): _PythonWrite(written=(0,)),
    ("directory", "setlastaccesstime"): _PythonWrite(written=(0,)),
    ("directory", "setlastaccesstimeutc"): _PythonWrite(written=(0,)),
    ("directory", "setlastwritetime"): _PythonWrite(written=(0,)),
    ("directory", "setlastwritetimeutc"): _PythonWrite(written=(0,)),
    ("streamwriter", "new"): _PythonWrite(written=(0,)),
    ("filestream", "new"): _PythonWrite(written=(0,)),
}
_UNPLACEABLE_DOTNET_TARGET = ".NET file call (a write whose path the gate cannot place)"

# Any other use of a System.IO type the table above does not read: a static
# call, a constructor, New-Object, and the FileSystemInfo instance methods
# that write. Reading and pure path arithmetic are left alone.
_DOTNET_ANY_IO_RE = re.compile(
    r"\[\s*(?:System\s*\.\s*)?IO\s*\.\s*(?P<type>[\w.]+)\s*\]\s*::\s*(?P<method>\w+)"
    r"|New-Object\s+(?:-TypeName\s+)?(?:System\s*\.\s*)?IO\s*\.\s*(?P<created>[\w.]+)",
    re.IGNORECASE,
)
_DOTNET_INSTANCE_WRITE_RE = re.compile(
    r"\.\s*(?:MoveTo|CopyTo|Delete|CreateSubdirectory|AppendText|CreateText|OpenWrite|Encrypt|Decrypt|SetAccessControl)"
    r"\s*\(",
    re.IGNORECASE,
)
# PowerShell that reaches a type, compiled code, a module, a WMI method or the
# process environment in a way no table above can follow: a System.IO type
# held as a value rather than called, a namespace or module imported by
# `using`, a type looked up from a string, reflection, C# compiled by
# Add-Type, and WMI or CIM method calls such as Win32_Process.Create. A WMI
# or CIM query that only reads stays allowed.
_POWERSHELL_OPAQUE_RE = re.compile(
    r"\[\s*(?:System\s*\.\s*)?IO\s*\.\s*(?!Path\s*\])[\w.]+\s*\](?!\s*::)"
    r"|^\s*using\s+(?:namespace|module|assembly)\b"
    r"|\[\s*(?:System\s*\.\s*)?(?:Type|Activator|AppDomain)\s*\]"
    r"|\bGetType\s*\(\s*['\"$]"
    r"|\bReflection\s*\.\s*(?:Assembly|Emit)\b"
    r"|\bAdd-Type\b(?![^;|\n]*\s-(?:AssemblyName|an)\b)"
    r"|\bAdd-Type\b[^;|\n]*\s-(?:TypeDefinition|MemberDefinition|Path|LiteralPath)\b"
    r"|\[\s*wmi(?:class)?\s*\]"
    r"|\b(?:Invoke-WmiMethod|Invoke-CimMethod|iwmi)\b"
    r"|\.\s*InvokeMethod\s*\("
    r"|(?:\bGet-WmiObject\b|\bgwmi\b|\[\s*wmisearcher\s*\])[\s\S]*\.\s*(?:Create|Change|StartService)\s*\("
    r"|\bWin32_(?:Process|ScheduledJob)\b[\s\S]*\bCreate\b|\bCreate\b[\s\S]*\bWin32_(?:Process|ScheduledJob)\b",
    re.IGNORECASE | re.MULTILINE,
)
_SET_ENVIRONMENT_RE = re.compile(r"\bSetEnvironmentVariable\s*\(\s*(?:(?P<quote>['\"])(?P<name>\w+)(?P=quote))?", re.IGNORECASE)
_SYSTEM_IO_MENTION_RE = re.compile(
    r"\bSystem\s*\.\s*IO\b|\[\s*IO\s*\.|\bNew-Object\s+(?:-TypeName\s+)?(?:System\s*\.\s*)?IO\s*\.",
    re.IGNORECASE,
)
_DOTNET_READ_TYPES = {"path"}
_DOTNET_READ_METHOD_RE = re.compile(r"^(?:Read|Get|Exists|Enumerate|OpenRead|OpenText|Is|Has|Combine|Join)", re.IGNORECASE)


def _sets_environment_unread(command: str) -> bool:
    """True when [Environment]::SetEnvironmentVariable sets a variable in _UNPLACEABLE_ENVIRONMENT, or one it cannot name."""
    for match in _SET_ENVIRONMENT_RE.finditer(command):
        if not match.group("name") or _changes_the_program(match.group("name")):
            return True

    return False


def _dotnet_unread(command: str) -> bool:
    """True when the command reaches System.IO, or runs code, in a way the tables above do not place."""
    if _POWERSHELL_OPAQUE_RE.search(command) or _sets_environment_unread(command):
        return True

    for match in _DOTNET_ANY_IO_RE.finditer(command):
        if match.group("created"):
            return True

        kind, method = match.group("type").lower(), match.group("method").lower()

        if (kind, method) in _DOTNET_IO_CALLS or kind in _DOTNET_READ_TYPES or _DOTNET_READ_METHOD_RE.match(method):
            continue

        return True

    return bool(_DOTNET_INSTANCE_WRITE_RE.search(command))


def _ps_literal(code: str, index: int) -> Tuple[Optional[str], int]:
    """A PowerShell string literal at index, and where it ends.

    An expandable string holding a variable is not a literal. Either way the
    index moves past the string, so what follows it is still read.
    """
    if code[index] not in _PS_SINGLE_QUOTES + _PS_DOUBLE_QUOTES:
        return None, index

    expandable = code[index] in _PS_DOUBLE_QUOTES
    reader = _read_ps_double_quoted if expandable else _read_ps_single_quoted

    try:
        text, end = reader(code, index)
    except _ShellParseError:
        return None, index

    return (None if expandable and "$" in code[index:end] else text), end


def _reaches_dotnet(command: str) -> bool:
    """True when the text names System.IO, whatever shell the tool name claims.

    Codex on Windows names its shell tool Bash and runs the command in
    PowerShell, so the tool name alone cannot decide whether the .NET scan runs.
    """
    return bool(_SYSTEM_IO_MENTION_RE.search(command))


def _dotnet_targets(command: str, powershell: bool = True) -> List[str]:
    written: List[Optional[str]] = []
    removed: List[Optional[str]] = []

    for match in _DOTNET_IO_RE.finditer(command):
        spec = _DOTNET_IO_CALLS.get((match.group("type").lower(), match.group("method").lower()))

        if spec is None:
            continue

        arguments = _js_arguments(command, match.end(), 1 + max(spec.written + spec.removed), _ps_literal)

        for bucket, positions in ((written, spec.written), (removed, spec.removed)):
            for position in positions:
                bucket.append(arguments[position] if position < len(arguments) else None)

    targets = _sourced([path for path in written if path is not None], powershell)
    targets += _removal_sourced([path for path in removed if path is not None], powershell)

    if None in written or None in removed or _dotnet_unread(command):
        targets.append(_UNPLACEABLE_DOTNET_TARGET)

    return targets


class _Stripped(NamedTuple):
    """A command with its wrappers peeled off, and what xargs, if present, adds."""

    argv: List[str]
    xargs: bool = False
    replace: str = ""
    directories: Tuple[str, ...] = ()


# Reserved words that lead a POSIX command without being it, as in
# `if true; then rm -rf ..; fi` or `{ rm -rf ..; }`, and their cmd kin.
_POSIX_KEYWORDS = {"{", "}", "!", "if", "then", "elif", "else", "while", "until", "do"}
_CMD_KEYWORDS = {"do", "else"}
_CMD_CONDITIONS = {"exist", "errorlevel", "defined", "cmdextversion"}
_CMD_COMPARISONS = {"equ", "neq", "lss", "leq", "gtr", "geq", "=="}
_MAX_WRAPPERS = 2 * _MAX_NESTING + 2


def _peels(word: str, dialect: str) -> bool:
    """True when word leads a command without being the command."""
    name = _basename(word)

    if name in _WRAPPER_TOOLS or name in _DURATION_WRAPPERS or name == "xargs":
        return True

    if dialect == _POSIX:
        return name in _POSIX_KEYWORDS

    return dialect == _CMD and (name in _CMD_KEYWORDS or name == "if" or (word.startswith("@") and len(word) > 1))


def _after_cmd_condition(rest: List[str]) -> List[str]:
    """What a cmd `if` runs once its condition is read off the front."""
    index = 1

    while index < len(rest) and rest[index].lower() in ("/i", "not"):
        index += 1

    if index < len(rest) and rest[index].lower() in _CMD_CONDITIONS:
        return rest[index + 2 :]

    if index + 1 < len(rest) and rest[index + 1].lower() in _CMD_COMPARISONS:
        return rest[index + 3 :]

    return rest[index + 1 :] if index < len(rest) and "==" in rest[index] else rest[index:]


def _xargs_replacement(flag: str, rest: List[str]) -> str:
    """The replace-string an xargs flag sets, or "" when it sets none."""
    if flag == "-I":
        return rest[0] if rest else ""

    if flag in ("-i", "--replace"):
        return "{}"

    for prefix in ("-I", "-i", "--replace="):
        if flag.startswith(prefix):
            return flag[len(prefix) :]

    return ""


def _changes_the_program(name: str) -> bool:
    """True for an environment variable that changes which program or file a command uses."""
    upper = name.upper()

    return upper in _UNPLACEABLE_ENVIRONMENT or upper.startswith(_UNPLACEABLE_ENVIRONMENT_PREFIXES)


def _assigns_unplaceable_environment(word: str) -> bool:
    return bool(_ASSIGNMENT_RE.match(word)) and _changes_the_program(word.split("=", 1)[0])


def _strip_wrappers(tokens: List[str], dialect: str = _POSIX) -> Optional[_Stripped]:
    """Drop leading assignments, keywords, and wrappers such as sudo, env, timeout, xargs.

    Returns None when more wrappers are stacked than the gate follows, or when
    a leading assignment, the command's own or one handed to env, sets a
    variable in _UNPLACEABLE_ENVIRONMENT. The caller treats either as a
    command it cannot place.
    """
    rest = list(tokens)
    xargs = False
    replace = ""
    directories: List[str] = []
    peeled = 0

    while True:
        while rest and _ASSIGNMENT_RE.match(rest[0]):
            if _assigns_unplaceable_environment(rest.pop(0)):
                return None

        if not rest or not _peels(rest[0], dialect):
            return _Stripped(rest, xargs, replace, tuple(directories))

        if peeled == _MAX_WRAPPERS:
            return None

        peeled += 1
        name = _basename(rest[0])

        if dialect == _CMD and rest[0].startswith("@"):
            rest[0] = rest[0][1:]
            continue

        if dialect == _CMD and name == "if":
            rest = _after_cmd_condition(rest)
            continue

        if name in _POSIX_KEYWORDS or name in _CMD_KEYWORDS:
            rest.pop(0)
            continue

        value_flags = _XARGS_VALUE_FLAGS if name == "xargs" else _WRAPPER_VALUE_FLAGS
        rest.pop(0)

        while rest and rest[0].startswith("-") and len(rest[0]) > 1:
            flag = rest.pop(0)

            if name == "xargs":
                replace = _xargs_replacement(flag, rest) or replace

            changes = _WRAPPER_CHDIR_FLAGS.get(name, ())

            if flag in changes and rest:
                directories.append(rest.pop(0))
            elif any(flag.startswith(change + "=") for change in changes if change.startswith("--")):
                directories.append(flag.split("=", 1)[1])
            elif name == "env" and flag.startswith("-C") and len(flag) > 2:
                directories.append(flag[2:])
            elif name == "env" and flag in ("-S", "--split-string") and rest:
                rest = rest[0].split() + rest[1:]
            elif flag in value_flags and rest:
                rest.pop(0)

        if name in _DURATION_WRAPPERS and rest:
            rest.pop(0)

        xargs = xargs or name == "xargs"


def _sets_unplaceable_environment(tokens: List[str], dialect: str) -> bool:
    """True when a builtin or cmdlet sets a variable in _UNPLACEABLE_ENVIRONMENT for the commands after it."""
    first = tokens[0]
    name = _program_name(first)

    if dialect == _POWERSHELL:
        lowered = first.lower()

        if lowered.startswith(("$env:", "${env:")):
            assigns = "=" in first or (len(tokens) > 1 and tokens[1].endswith("="))
            variable = first.split(":", 1)[1].split("=", 1)[0].rstrip("+}")

            return assigns and _changes_the_program(variable)

        if _PS_ALIASES.get(name, name) in _PS_ENVIRONMENT_SETTERS:
            matches = [_PS_ENVIRONMENT_RE.match(token) for token in tokens[1:]]

            return any(match is not None and _changes_the_program(match.group("name")) for match in matches)

    if name == "setx":
        operands = [token for token in tokens[1:] if not _is_windows_switch(token)]

        return bool(operands) and _changes_the_program(operands[0])

    if dialect == _CMD and name == "set":
        return any(_assigns_unplaceable_environment(token) for token in tokens[1:] if not _is_windows_switch(token))

    return dialect == _POSIX and name in _POSIX_DECLARATIONS and any(_assigns_unplaceable_environment(token) for token in tokens[1:])


def _rejoined(tokens: List[str]) -> str:
    """Put a split command line back together, requoting any spaced word."""
    if len(tokens) == 1:
        return tokens[0]

    return " ".join('"' + token + '"' if re.search(r"\s", token) else token for token in tokens)


def _is_prefix_of(flag: str, name: str) -> bool:
    return len(flag) >= _PS_MIN_PREFIX and name.startswith(flag)


def _decoded_command(value: str) -> Optional[str]:
    """The text of a -EncodedCommand value, or None when it does not decode.

    PowerShell refuses a value that is not Base64 over UTF-16LE and runs
    nothing, so an undecodable value is an unlexable command, which allows.
    """
    try:
        return base64.b64decode(value, validate=True).decode("utf-16-le")
    except (binascii.Error, ValueError):
        return None


def _powershell_code(tokens: List[str]) -> Optional[str]:
    for index, token in enumerate(tokens[1:], start=1):
        flag = token.lower()
        rest = tokens[index + 1 :]

        if not rest:
            return None

        if flag in _PS_COMMAND_ALIASES or _is_prefix_of(flag, _PS_COMMAND_FLAG):
            return _rejoined(rest)

        if flag in _PS_COMMAND_WITH_ARGS_FLAGS:
            return rest[0]

        if flag in _PS_ENCODED_ALIASES or _is_prefix_of(flag, _PS_ENCODED_FLAG):
            return _decoded_command(rest[0])

    return None


def _powershell_directory(tokens: List[str]) -> str:
    """The -WorkingDirectory a pwsh or powershell host starts in, or "" when it names none."""
    for index, token in enumerate(tokens[1:-1], start=1):
        flag = token.lower()

        if _is_powershell_code_flag(flag) or flag in ("-f", "-file") or _is_prefix_of(flag, "-file"):
            return ""

        if flag in ("-wd", "-workingdirectory") or _is_prefix_of(flag, "-workingdirectory"):
            return tokens[index + 1]

    return ""


def _nested_shell_code(name: str, tokens: List[str]) -> Optional[str]:
    """The command a shell wrapper runs, or None when it runs none inline."""
    if name in _POWERSHELL_SHELLS:
        return _powershell_code(tokens)

    for index, token in enumerate(tokens[1:], start=1):
        rest = tokens[index + 1 :]
        lowered = token.lower()

        if name in _CMD_SHELLS and lowered[:2] in _CMD_CODE_FLAGS and len(token) > 2:
            return _rejoined([token[2:]] + rest)

        if not rest:
            return None

        if name in _CMD_SHELLS and lowered in _CMD_CODE_FLAGS:
            return _rejoined(rest)

        if name in _POSIX_SHELLS and (token == "--command" or _POSIX_CODE_FLAG_RE.match(token)):
            return rest[0]

    return None


def _shell_dialect(name: str) -> str:
    if name in _POWERSHELL_SHELLS:
        return _POWERSHELL

    return _CMD if name in _CMD_SHELLS else _POSIX


def _reads_program_from_stdin(name: str, tokens: List[str]) -> bool:
    """True when a shell or interpreter takes its program from standard input."""
    flags = tokens[1:]

    if name in _POSIX_SHELLS:
        if any(flag.startswith("-") and not flag.startswith("--") and "s" in flag[1:] for flag in flags):
            return True

        operands = _operands(flags, _POSIX_SHELL_VALUE_FLAGS)
        return not operands or operands[0] == "-"

    if name in _CMD_SHELLS:
        return True

    if name in _POWERSHELL_SHELLS:
        return _powershell_reads_stdin(flags)

    if name in _PYTHON_TOOLS:
        if any(flag.startswith("-m") for flag in flags):
            return False

        operands = _operands(flags, _PYTHON_VALUE_FLAGS)
        return not operands or operands[0] == "-"

    if name in _INLINE_CODE_TOOLS:
        operands = _operands(flags, _INTERPRETER_VALUE_FLAGS)
        return not operands or operands[0] == "-" or operands[:2] == ["run", "-"]

    return False


def _powershell_reads_stdin(flags: List[str]) -> bool:
    """pwsh reads commands from standard input unless it is handed a script."""
    index = 0

    while index < len(flags):
        lowered = flags[index].lower()

        if lowered in ("-f", "-file") or _is_prefix_of(lowered, "-file"):
            return index + 1 < len(flags) and flags[index + 1] == "-"

        if lowered in _PS_HOST_VALUE_FLAGS:
            index += 2
            continue

        if lowered.startswith("-") and len(lowered) > 1:
            index += 1
            continue

        return False

    return True


def _read_script(target: str) -> Optional[str]:
    """The text of a file the command runs as code, or None when it cannot be read."""
    if not target or _has_glob(target):
        return None

    path = _as_path(target)
    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())

    for base in bases:
        candidate = path if path.is_absolute() else base / path

        try:
            if candidate.is_file() and candidate.stat().st_size <= _MAX_SCRIPT_BYTES:
                return candidate.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue

    return None


def _printf_text(template: str) -> str:
    return template.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")


def _stage_output(segment: ShellSegment, dialect: str) -> str:
    """What a pipeline stage writes to the next one, or _UNKNOWN_INPUT."""
    if segment.literal and dialect == _POWERSHELL:
        return segment.argv[0] + "\n"

    stripped = _strip_wrappers(list(segment.argv), dialect)

    if stripped is None or not stripped.argv or stripped.xargs:
        return _UNKNOWN_INPUT

    name = _program_name(stripped.argv[0])
    canonical = _PS_ALIASES.get(name, name) if dialect == _POWERSHELL else name
    argv = _split_arrays(stripped.argv)

    if canonical in ("echo", "write-output"):
        words = argv[1:]

        while dialect == _POSIX and words and words[0] in _ECHO_FLAGS:
            words = words[1:]

        return " ".join(words) + "\n"

    if canonical == "printf" and len(argv) > 1 and "%" not in argv[1]:
        return _printf_text(argv[1])

    if canonical == "cat" or canonical == "get-content" or (canonical == "type" and dialect == _CMD):
        if canonical == "get-content":
            files = _ps_values(_ps_bind(stripped.argv, _PS_CMDLETS["get-content"]), "-path", "-literalpath", _PS_UNBOUND)
        else:
            files = _operands(argv[1:])

        if not files:
            return "".join(segment.stdin) if segment.stdin else _UNKNOWN_INPUT

        texts = [_read_script(path) for path in files]

        return _UNKNOWN_INPUT if any(text is None for text in texts) else "".join(text or "" for text in texts)

    return _UNKNOWN_INPUT


def _stdin_of(segments: List[ShellSegment], position: int, dialect: str) -> Optional[str]:
    """What a segment reads on standard input: a heredoc, a piped stage, or nothing."""
    segment = segments[position]

    if segment.stdin:
        return "".join(segment.stdin)

    if position < 2 or segments[position - 1].control != "|":
        return None

    producer = segments[position - 2]

    if producer.control or not producer.argv:
        return _UNKNOWN_INPUT

    return _stage_output(producer, dialect)


def _no_input() -> Optional[str]:
    return None


def _xargs_arguments(rest: List[str], replace: str, feed: Optional[str]) -> List[str]:
    """The command xargs runs, with the words it reads put where xargs puts them."""
    if feed is None:
        return rest

    words = [_UNPLACEABLE_ARGUMENT] if feed == _UNKNOWN_INPUT else feed.split()

    if not replace:
        return rest + words

    expanded: List[str] = []

    for token in rest:
        expanded += [token.replace(replace, word) for word in words] if replace in token else [token]

    return expanded


def _child_shell_targets(code: str, depth: int, dialect: str, directory: str = "") -> List[str]:
    """What a child shell writes. Its `cd` dies with it, so the base is put back.

    A child that cannot be lexed is one the gate cannot place, which denies:
    only a command that fails to lex as a whole is allowed unread.
    """
    global _CD_BASE, _CD_STACK
    saved = _CD_BASE, list(_CD_STACK)

    try:
        if directory:
            _enter_directory([directory])

        return _command_targets(code, depth + 1, dialect)
    except _ShellParseError:
        return [_UNPLACEABLE_SHELL_TARGET]
    finally:
        _CD_BASE, _CD_STACK = saved


def _runs_a_computed_program(code: str, dialect: str) -> bool:
    """True when evaluated code runs a command whose name is a variable or a subexpression."""
    for segment in _lex(code, dialect):
        stripped = _strip_wrappers(list(segment.argv), dialect) if segment.argv else None
        word = stripped.argv[0] if stripped and stripped.argv else ""

        if word.startswith(("$", "`")) or word == _SUBEXPRESSION:
            return True

    return False


def _evaluated_targets(code: str, depth: int, dialect: str) -> List[str]:
    """What eval or Invoke-Expression writes, running code in the current shell."""
    try:
        targets = _command_targets(code, depth + 1, dialect)

        if _runs_a_computed_program(code, dialect):
            targets.append(_UNPLACEABLE_SHELL_TARGET)
    except _ShellParseError:
        return [_UNPLACEABLE_SHELL_TARGET]

    return targets


def _sourced_script_targets(path: str, depth: int, dialect: str) -> List[str]:
    """What a sourced or dot-sourced file writes, read as shell code."""
    text = _read_script(path)

    if text is None:
        return [_UNPLACEABLE_SHELL_TARGET]

    try:
        return _command_targets(text, depth + 1, dialect)
    except _ShellParseError:
        return [_UNPLACEABLE_SHELL_TARGET]


def _fed_targets(feed: Optional[str], depth: int, dialect: str, program: str = "", powershell: bool = False) -> List[str]:
    """What a program reading its code from standard input writes."""
    if feed is None:
        return []

    if feed == _UNKNOWN_INPUT:
        return [_UNPLACEABLE_SHELL_TARGET]

    if program:
        return _program_code_targets(program, feed, powershell)

    return _child_shell_targets(feed, depth, dialect)


def _code_runner_targets(
    name: str, rest: List[str], depth: int, dialect: str, feed: Callable[[], Optional[str]]
) -> Optional[List[str]]:
    """What a command that runs further code writes, or None when it runs none.

    That is eval and Invoke-Expression, source and dot-sourcing, a shell with
    an inline command or a program on standard input, and an interpreter
    reading its program from standard input.
    """
    powershell = dialect != _POSIX

    if dialect == _POSIX and name == "eval":
        return _evaluated_targets(" ".join(rest[1:]), depth, dialect)

    if dialect == _POWERSHELL and _PS_ALIASES.get(name, name) == "invoke-expression":
        bound = _ps_bind(rest, _PS_CMDLETS["invoke-expression"])
        code = " ".join(_ps_values(bound, "-command", _PS_UNBOUND))

        return _evaluated_targets(code, depth, dialect) if code else _fed_targets(feed(), depth, dialect)

    if name in ("source", ".") and dialect != _CMD and len(rest) > 1:
        return _sourced_script_targets(rest[1], depth, dialect)

    if name in _POSIX_SHELLS or name in _POWERSHELL_SHELLS or name in _CMD_SHELLS:
        child = _shell_dialect(name)
        code = _nested_shell_code(name, rest)

        if code is not None and code != "-":
            return _child_shell_targets(code, depth, child, _powershell_directory(rest) if child == _POWERSHELL else "")

        if code == "-" or _reads_program_from_stdin(name, rest):
            return _fed_targets(feed(), depth, child)

        script = _shell_script(name, rest)

        return _sourced_script_targets(script, depth, child) if script else []

    if name in _INLINE_CODE_TOOLS and not _inline_code(rest) and _reads_program_from_stdin(name, rest):
        return _fed_targets(feed(), depth, dialect, name, powershell)

    if name in ("su", "runuser"):
        code = _option_value(rest, ("-c", "--command"))

        return _child_shell_targets(code, depth, _POSIX) if code else []

    runner = _COMMAND_RUNNERS.get(name)

    return runner(rest, depth, dialect) if runner else None


def _shell_script(name: str, tokens: List[str]) -> str:
    """The script file a shell runs, or "" when it runs none or only checks its syntax."""
    flags = tokens[1:]

    if name in _POSIX_SHELLS:
        toggles = [flag[0] for flag in flags if flag[:1] in ("-", "+") and flag[1:2] != "-" and "n" in flag[1:]]

        if toggles and toggles[-1] == "-":
            return ""

        operands = _operands([flag for flag in flags if not (flag.startswith("+") and len(flag) > 1)], _POSIX_SHELL_VALUE_FLAGS)

        return operands[0] if operands else ""

    if name not in _POWERSHELL_SHELLS or not _powershell_runs_script(tokens):
        return ""

    index = 0

    while index < len(flags):
        lowered = flags[index].lower()

        if lowered in ("-f", "-file") or _is_prefix_of(lowered, "-file"):
            return flags[index + 1] if index + 1 < len(flags) else ""

        if lowered in _PS_HOST_VALUE_FLAGS:
            index += 2
            continue

        if lowered.startswith("-") and len(lowered) > 1:
            index += 1
            continue

        return flags[index]

    return ""


def _option_value(tokens: List[str], names: Tuple[str, ...]) -> str:
    """The value of the first of these options, spelled -c VALUE or --command=VALUE, or ""."""
    for index, token in enumerate(tokens[1:], start=1):
        if token in names and index + 1 < len(tokens):
            return tokens[index + 1]

        for name in names:
            if name.startswith("--") and token.startswith(name + "="):
                return token.split("=", 1)[1]

    return ""


_FLOCK_VALUE_FLAGS = {"-w", "--wait", "--timeout", "-E", "--conflict-exit-code"}


def _flock_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """flock creates its lock file and runs the command after it, or its -c shell code."""
    index = 1

    while index < len(tokens) and tokens[index].startswith("-") and len(tokens[index]) > 1:
        index += 2 if tokens[index] in _FLOCK_VALUE_FLAGS else 1

    if index >= len(tokens):
        return []

    lock, rest = tokens[index], tokens[index + 1 :]
    targets = [] if lock.isdigit() else _sourced([lock], dialect != _POSIX)

    if rest[:1] and rest[0] in ("-c", "--command"):
        return targets + (_child_shell_targets(rest[1], depth, _POSIX) if len(rest) > 1 else [])

    return targets + (_segment_targets(rest, depth + 1, dialect) if rest else [])


_WATCH_VALUE_FLAGS = {"-n", "--interval", "-q", "--equexit"}


def _watch_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """watch runs its words through sh -c, or directly with -x."""
    index = 1
    direct = False

    while index < len(tokens) and tokens[index].startswith("-") and len(tokens[index]) > 1:
        direct = direct or tokens[index] in ("-x", "--exec")
        index += 2 if tokens[index] in _WATCH_VALUE_FLAGS else 1

    rest = tokens[index:]

    if not rest:
        return []

    return _segment_targets(rest, depth + 1, dialect) if direct else _child_shell_targets(" ".join(rest), depth, _POSIX)


_SCRIPT_VALUE_FLAGS = {"-c", "--command", "-E", "--echo", "-I", "--log-in", "-O", "--log-out", "-B", "--log-io", "-T", "--log-timing", "-m", "--logging-format"}
_SCRIPT_LOG_FLAGS = {"-I", "--log-in", "-O", "--log-out", "-B", "--log-io", "-T", "--log-timing"}


def _script_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """script writes its typescript file and logs, and runs its -c shell code."""
    logs: List[str] = []
    operands: List[str] = []
    code = ""
    index = 1

    while index < len(tokens):
        token = tokens[index]
        name, equals, attached = token.partition("=")

        if token.startswith("-") and name in _SCRIPT_VALUE_FLAGS:
            value = attached if equals else (tokens[index + 1] if index + 1 < len(tokens) else "")
            index += 1 if equals else 2
            code = value if name in ("-c", "--command") else code
            logs += [value] if name in _SCRIPT_LOG_FLAGS else []
            continue

        if not (token.startswith("-") and len(token) > 1):
            operands.append(token)

        index += 1

    targets = _sourced(operands[:1] or ([] if logs else ["typescript"]), dialect != _POSIX) + _sourced(logs, dialect != _POSIX)

    return targets + (_child_shell_targets(code, depth, _POSIX) if code else [])


_WSL_VALUE_FLAGS = {"-d", "--distribution", "-u", "--user", "--shell-type", "--distribution-id"}
_WSL_ARCHIVES = {"--export": 2, "--import": 2}


def _wsl_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """What wsl runs inside the distribution, read with its /mnt/<drive> paths as Windows drives."""
    global _WSL_DEPTH
    index = 1
    directory = ""

    while index < len(tokens):
        flag = tokens[index].lower()

        if flag in ("-e", "--exec", "--"):
            index += 1
            break

        if flag in _WSL_ARCHIVES:
            return _sourced(tokens[index + _WSL_ARCHIVES[flag] : index + _WSL_ARCHIVES[flag] + 1], True)

        if flag == "--cd" and index + 1 < len(tokens):
            directory = tokens[index + 1]
            index += 2
            continue

        if flag in _WSL_VALUE_FLAGS:
            index += 2
            continue

        if flag.startswith("-"):
            return []

        break

    rest = tokens[index:]

    if not rest:
        return []

    _WSL_DEPTH += 1

    try:
        return _child_shell_targets(_rejoined(rest), depth, _POSIX, directory)
    finally:
        _WSL_DEPTH -= 1


_UNPLACEABLE_RUNNER_TARGET = "a command that runs code elsewhere (remote, scheduled, containerised or WMI)"
_SSH_VALUE_LETTERS = set("BbcDEeFIiJLlmOoPpQRSWw")
_SSH_LOCAL_COMMAND_RE = re.compile(r"^\s*(?:ProxyCommand|LocalCommand|PermitLocalCommand|KnownHostsCommand|Match)\b", re.IGNORECASE)
_PLINK_VALUE_FLAGS = {"-P", "-l", "-pw", "-i", "-m", "-hostkey", "-L", "-R", "-D", "-sercfg", "-sshlog", "-sshrawlog", "-loghost"}


def _names_this_machine(destination: str) -> bool:
    """True when an ssh-style destination, user@host:port or ssh://host, is this machine or cannot be read."""
    if _has_expansion(destination) or _has_expansion(destination, powershell=True):
        return True

    host = destination.split("://", 1)[-1].rsplit("@", 1)[-1]
    host = host[1:].split("]", 1)[0] if host.startswith("[") else host.split(":", 1)[0].split("/", 1)[0]

    return bool(host) and _is_this_machine(host)


def _ssh_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """ssh or plink to this machine, or with a local command option, runs code the gate cannot see."""
    plink = _program_name(tokens[0]) == "plink"
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token == "--":
            index += 1
            break

        if not token.startswith("-") or len(token) == 1:
            break

        if plink:
            if token.lower() == "-proxycmd":
                return [_UNPLACEABLE_RUNNER_TARGET]

            index += 2 if token in _PLINK_VALUE_FLAGS else 1
            continue

        letter, attached = token[1], token[2:]
        value = attached or (tokens[index + 1] if index + 1 < len(tokens) else "")

        if letter == "F" or (letter == "o" and _SSH_LOCAL_COMMAND_RE.match(value)):
            return [_UNPLACEABLE_RUNNER_TARGET]

        index += 1 if attached or letter not in _SSH_VALUE_LETTERS else 2

    destination = tokens[index] if index < len(tokens) else ""

    return [_UNPLACEABLE_RUNNER_TARGET] if destination and _names_this_machine(destination) else []


def _winrs_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """winrs runs on this machine unless -r names another host."""
    for token in tokens[1:]:
        lowered = token.lower()

        if lowered.startswith(("-r:", "/r:", "-remote:", "/remote:")):
            return [_UNPLACEABLE_RUNNER_TARGET] if _names_this_machine(token.split(":", 1)[1]) else []

    return [_UNPLACEABLE_RUNNER_TARGET]


def _always_unplaceable(tokens: List[str], depth: int, dialect: str) -> List[str]:
    return [_UNPLACEABLE_RUNNER_TARGET]


_PS_REMOTE_HOSTS = ("-computername", "-cn", "-hostname")
_PS_REMOTE_OPAQUE = ("-session", "-connectionuri", "-uri", "-vmname", "-vmid", "-containerid", "-filepath", "-sshconnection")


def _is_ps_parameter(word: str, names: Tuple[str, ...]) -> bool:
    return any(word == name or (len(word) >= _PS_MIN_PREFIX and name.startswith(word)) for name in names)


def _ps_remote_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """Invoke-Command and PowerShell sessions aimed at this machine, a session, a VM, a container or a script file."""
    index = 1

    while index < len(tokens):
        word = tokens[index].lower().split(":", 1)[0]
        following = tokens[index + 1] if index + 1 < len(tokens) else ""

        if not word.startswith("-"):
            hosts = [host for part in _split_array(tokens[index]) for host in part.split(",") if host]

            if any(_names_this_machine(host) for host in hosts):
                return [_UNPLACEABLE_RUNNER_TARGET]

            index += 1
            continue

        if _is_ps_parameter(word, _PS_REMOTE_OPAQUE):
            return [_UNPLACEABLE_RUNNER_TARGET]

        if _is_ps_parameter(word, _PS_REMOTE_HOSTS):
            hosts = [host for part in _split_array(following) for host in part.split(",") if host]

            if not hosts or any(_names_this_machine(host) for host in hosts):
                return [_UNPLACEABLE_RUNNER_TARGET]

            index += 2
            continue

        index += 1

    return []


_CONTAINER_TOOLS = {"docker", "podman", "nerdctl"}
_CONTAINER_GLOBAL_VALUE_FLAGS = {"-H", "--host", "-c", "--context", "--config", "-l", "--log-level", "--tlscacert", "--tlscert", "--tlskey"}
_CONTAINER_MOUNTS = {"-v", "--volume", "--mount"}
_CONTAINER_GROUPS = {"container", "image", "builder"}
# Subcommands that run code in a container that may already have the
# repository mounted, or that build from a file which may mount it.
_CONTAINER_OPAQUE = {"exec", "start", "restart", "unpause", "attach", "build", "runlabel"}
_CONTAINER_OPAQUE_PAIRS = {
    ("buildx", "build"),
    ("buildx", "b"),
    ("buildx", "bake"),
    ("buildx", "debug"),
    ("kube", "play"),
    ("play", "kube"),
    ("machine", "ssh"),
    ("stack", "deploy"),
    ("service", "create"),
    ("service", "update"),
}
_CONTAINER_OPAQUE_PAIR_VALUE_FLAGS = {"--builder"}
_CONTAINER_ARCHIVE_WRITERS = {"save", "export"}
_CONTAINER_OUTPUT_FLAGS = {"-o", "--output"}
_COMPOSE_RUNS = {"up", "run", "create", "start", "restart", "unpause", "exec", "attach", "watch", "build", "scale"}
_COMPOSE_VALUE_FLAGS = {
    "-f",
    "--file",
    "-p",
    "--project-name",
    "--profile",
    "--env-file",
    "--project-directory",
    "--ansi",
    "--progress",
    "--parallel",
    "-H",
    "--host",
    "-c",
    "--context",
}
_WINDOWS_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:[\\/]")
_CONTAINER_PATH = re.compile(r"^[\w.-]+:")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


def _mount_source(flag: str, value: str) -> str:
    """The host path a -v or --mount value binds, or "" for a named or anonymous volume."""
    if flag == "--mount":
        fields = dict(item.split("=", 1) for item in value.split(",") if "=" in item)

        if fields.get("type", "volume").lower() != "bind":
            return ""

        return fields.get("source", fields.get("src", ""))

    split = value.find(":", 2 if _WINDOWS_DRIVE_PREFIX.match(value) else 0)

    if split < 0:
        return ""

    source = value[:split]

    return source if re.search(r"[/\\.~$%]", source) else ""


def _is_container_path(operand: str) -> bool:
    return bool(_CONTAINER_PATH.match(operand)) and not _WINDOWS_DRIVE.match(operand)


def _copy_destination_targets(operands: List[str], powershell: bool) -> List[str]:
    """What docker cp writes: a host path is placed, a path inside a container may be a repository mount."""
    destination = operands[-1] if len(operands) >= 2 else ""

    if not destination:
        return []

    return [_UNPLACEABLE_RUNNER_TARGET] if _is_container_path(destination) else _sourced([destination], powershell)


def _archive_output_targets(tokens: List[str], powershell: bool) -> List[str]:
    """The file docker save or docker export writes with -o or --output."""
    outputs: List[str] = []

    for position, token in enumerate(tokens):
        flag, equals, attached = token.partition("=")

        if token in _CONTAINER_OUTPUT_FLAGS and position + 1 < len(tokens):
            outputs.append(tokens[position + 1])
        elif equals and flag in _CONTAINER_OUTPUT_FLAGS:
            outputs.append(attached)
        elif token.startswith("-o") and len(token) > 2:
            outputs.append(token[2:])

    return _sourced(outputs, powershell)


def _compose_targets(tokens: List[str], powershell: bool) -> List[str]:
    """Compose subcommands that start or build services deny. Listing, logs, config and teardown stay allowed."""
    operands = _operands(tokens, _COMPOSE_VALUE_FLAGS)
    subcommand = operands[0] if operands else ""

    if subcommand in _COMPOSE_RUNS:
        return [_UNPLACEABLE_RUNNER_TARGET]

    if subcommand == "cp":
        return _copy_destination_targets(operands[1:], powershell)

    if subcommand == "export":
        return _archive_output_targets(tokens, powershell)

    return []


def _container_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """What a container run binds from the host and what docker cp writes. Running code in an existing container denies."""
    powershell = dialect != _POSIX

    if _program_name(tokens[0]).endswith("-compose"):
        return _compose_targets(tokens[1:], powershell)

    index = 1

    while index < len(tokens) and tokens[index].startswith("-"):
        index += 2 if tokens[index] in _CONTAINER_GLOBAL_VALUE_FLAGS else 1

    rest = tokens[index:]

    if rest[:1] and rest[0] in _CONTAINER_GROUPS:
        rest = rest[1:]

    subcommand = rest[0] if rest else ""

    if subcommand == "compose":
        return _compose_targets(rest[1:], powershell)

    leading_pair = tuple(_operands(rest, _CONTAINER_OPAQUE_PAIR_VALUE_FLAGS)[:2])

    if subcommand in _CONTAINER_OPAQUE or leading_pair in _CONTAINER_OPAQUE_PAIRS:
        return [_UNPLACEABLE_RUNNER_TARGET]

    if subcommand == "cp":
        return _copy_destination_targets(_operands(rest[1:]), powershell)

    if subcommand in _CONTAINER_ARCHIVE_WRITERS:
        return _archive_output_targets(rest[1:], powershell)

    if subcommand not in ("run", "create"):
        return []

    sources: List[str] = []

    for position, token in enumerate(rest[1:], start=1):
        following = rest[position + 1] if position + 1 < len(rest) else ""
        flag, equals, attached = token.partition("=")

        if token in _CONTAINER_MOUNTS:
            sources.append(_mount_source(token, following))
        elif equals and flag in _CONTAINER_MOUNTS:
            sources.append(_mount_source(flag, attached))
        elif token.startswith("-v") and len(token) > 2 and not token.startswith("--"):
            sources.append(_mount_source("-v", token[2:]))

    return _removal_sourced([source for source in sources if source], powershell)


_SCHEDULE_READS = {
    "at": ("-l", "-c", "-d", "-r", "-v"),
    "crontab": ("-l", "-r", "-i"),
}
_SCHTASKS_WRITES = ("/create", "-create", "/change", "-change", "/run", "-run")


def _scheduler_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """A job handed to a scheduler runs later, where the gate cannot see it. Listing and removing jobs stay allowed."""
    name = _program_name(tokens[0])
    flags = [token.lower() for token in tokens[1:]]

    if name == "schtasks":
        reads = not any(flag in _SCHTASKS_WRITES for flag in flags)
    elif name == "crontab":
        kept = [flag for position, flag in enumerate(flags) if flag != "-u" and (position == 0 or flags[position - 1] != "-u")]
        reads = bool(kept) and all(flag in _SCHEDULE_READS[name] for flag in kept)
    else:
        reads = bool(flags) and flags[0] in _SCHEDULE_READS[name]

    return [] if reads else [_UNPLACEABLE_RUNNER_TARGET]


def _wmic_targets(tokens: List[str], depth: int, dialect: str) -> List[str]:
    """wmic ... call create starts a process or a job the gate cannot see."""
    words = [token.lower() for token in tokens[1:]]

    return [_UNPLACEABLE_RUNNER_TARGET] if "call" in words and "create" in words else []


_COMMAND_RUNNERS: Dict[str, Callable[[List[str], int, str], List[str]]] = {
    "flock": _flock_targets,
    "watch": _watch_targets,
    "script": _script_targets,
    "wsl": _wsl_targets,
    "ssh": _ssh_targets,
    "slogin": _ssh_targets,
    "plink": _ssh_targets,
    "winrs": _winrs_targets,
    "psexec": _always_unplaceable,
    "psexec64": _always_unplaceable,
    "paexec": _always_unplaceable,
    "systemd-run": _always_unplaceable,
    "batch": _always_unplaceable,
    "register-scheduledtask": _always_unplaceable,
    "register-scheduledjob": _always_unplaceable,
    "set-scheduledtask": _always_unplaceable,
    "start-scheduledtask": _always_unplaceable,
    "invoke-command": _ps_remote_targets,
    "icm": _ps_remote_targets,
    "enter-pssession": _ps_remote_targets,
    "etsn": _ps_remote_targets,
    "new-pssession": _ps_remote_targets,
    "nsn": _ps_remote_targets,
    "schtasks": _scheduler_targets,
    "at": _scheduler_targets,
    "crontab": _scheduler_targets,
    "wmic": _wmic_targets,
    "docker-compose": _container_targets,
    "podman-compose": _container_targets,
}
_COMMAND_RUNNERS.update({name: _container_targets for name in _CONTAINER_TOOLS})


def _find_matches(starts: List[str], expression: List[str]) -> List[str]:
    """Glob patterns covering every entry a find expression can reach."""
    paths = [expression[index + 1] for index, token in enumerate(expression[:-1]) if token in _FIND_PATH_FLAGS]

    if paths:
        return paths

    leaves = [expression[index + 1] for index, token in enumerate(expression[:-1]) if token in _FIND_NAME_FLAGS]
    leaf = "**/" + leaves[-1] if leaves else "**"

    return [_joined(start, leaf) for start in starts]


def _find_targets(tokens: List[str], depth: int, dialect: str = _POSIX) -> List[str]:
    """What find deletes, writes with -fprint, or hands to -exec in place of {}."""
    powershell = dialect != _POSIX
    index = 1

    while index < len(tokens) and (tokens[index] in _FIND_OPTIONS or tokens[index].startswith("-O")):
        index += 2 if tokens[index] == "-D" else 1

    starts: List[str] = []

    while index < len(tokens) and not (tokens[index].startswith("-") or tokens[index] in ("(", "!", ",")):
        starts.append(tokens[index])
        index += 1

    expression = tokens[index:]
    found = _find_matches(starts or ["."], expression)
    targets: List[str] = []

    if "-delete" in expression:
        targets += _removal_sourced(found, powershell)

    for position, token in enumerate(expression):
        if token in _FIND_WRITE_FLAGS and position + 1 < len(expression):
            targets += _sourced([expression[position + 1]], powershell)

        if token not in _FIND_EXEC_MARKERS:
            continue

        command: List[str] = []

        for item in expression[position + 1 :]:
            if item in (";", "+"):
                break
            command.append(item)

        if not command:
            continue

        for entry in found:
            targets += _segment_targets([item.replace("{}", entry) for item in command], depth + 1, dialect)

    return targets


class _Rewriter(NamedTuple):
    """A program that rewrites the files it is handed.

    triggers: flags that turn the rewrite on, none meaning always.
    checks: flags that make it a dry run.
    subcommand: the subcommand that rewrites, "" when there is none.
    default: what it rewrites when handed no file.
    skip_first: the first operand is an expression rather than a file.
    """

    triggers: AbstractSet[str] = frozenset()
    checks: AbstractSet[str] = frozenset()
    subcommand: str = ""
    default: str = ""
    skip_first: bool = False
    value_flags: AbstractSet[str] = frozenset()


_EDITOR = (_Rewriter(value_flags={"-c", "-S", "-u", "-U", "-i", "-T", "-w", "-W", "-t", "-q", "--cmd"}),)
_REWRITERS: Dict[str, Tuple[_Rewriter, ...]] = {
    "ex": _EDITOR,
    "vi": _EDITOR,
    "vim": _EDITOR,
    "nvim": _EDITOR,
    "gvim": _EDITOR,
    "ed": _EDITOR,
    "red": _EDITOR,
    "dos2unix": _EDITOR,
    "unix2dos": _EDITOR,
    "mac2unix": _EDITOR,
    "unix2mac": _EDITOR,
    "sponge": _EDITOR,
    "black": (_Rewriter(checks={"--check", "--diff"}),),
    "isort": (_Rewriter(checks={"--check", "--check-only", "-c", "--diff"}),),
    "autopep8": (_Rewriter(triggers={"-i", "--in-place"}),),
    "ruff": (
        _Rewriter(subcommand="format", checks={"--check", "--diff"}, default="."),
        _Rewriter(subcommand="check", triggers={"--fix", "--unsafe-fixes"}, default="."),
    ),
    "gofmt": (_Rewriter(triggers={"-w"}),),
    "goimports": (_Rewriter(triggers={"-w"}),),
    "rustfmt": (_Rewriter(checks={"--check"}),),
    "cargo": (
        _Rewriter(subcommand="fmt", checks={"--check"}, default="."),
        _Rewriter(subcommand="fix", default="."),
        _Rewriter(subcommand="clippy", triggers={"--fix"}, default="."),
    ),
    "clang-format": (_Rewriter(triggers={"-i"}),),
    "prettier": (_Rewriter(triggers={"--write", "-w"}),),
    "eslint": (_Rewriter(triggers={"--fix"}, default="."),),
    "shfmt": (_Rewriter(triggers={"-w", "--write"}),),
    "terraform": (_Rewriter(subcommand="fmt", checks={"-check"}, default="."),),
    "dotnet": (_Rewriter(subcommand="format", checks={"--verify-no-changes"}, default="."),),
    "stylua": (_Rewriter(checks={"--check"}),),
    "perltidy": (_Rewriter(triggers={"-b", "--backup-and-modify-in-place"}),),
    "google-java-format": (_Rewriter(triggers={"-i", "--replace"}),),
    "ktlint": (_Rewriter(triggers={"-F", "--format"}, default="."),),
    "biome": (
        _Rewriter(subcommand="format", triggers={"--write"}, default="."),
        _Rewriter(subcommand="check", triggers={"--write", "--apply", "--fix"}, default="."),
        _Rewriter(subcommand="lint", triggers={"--write", "--apply", "--fix"}, default="."),
    ),
    "yq": (_Rewriter(triggers={"-i", "--inplace"}, skip_first=True),),
}
_YQ_SUBCOMMANDS = {"e", "eval", "ea", "eval-all"}


def _rewriter_rule_targets(rule: _Rewriter, name: str, words: List[str], powershell: bool) -> List[str]:
    if rule.subcommand:
        operands = _operands(words)

        if not operands or operands[0] != rule.subcommand:
            return []

        words = words[words.index(operands[0]) + 1 :]

    flags = {word.split("=", 1)[0] for word in words if word.startswith("-")}

    if rule.checks & flags or rule.triggers and not rule.triggers & flags:
        return []

    operands = [operand for operand in _operands(words, rule.value_flags) if not operand.startswith("+")]

    if name == "yq" and operands[:1] and operands[0] in _YQ_SUBCOMMANDS:
        operands = operands[1:]

    if rule.skip_first:
        operands = operands[1:]

    return _sourced(operands or ([rule.default] if rule.default else []), powershell)


def _rewriter_targets(name: str, tokens: List[str], powershell: bool = False) -> List[str]:
    """Files an editor, a line-ending converter or a formatter rewrites in place, and sort -o or uniq's output."""
    targets: List[str] = []

    for rule in _REWRITERS.get(name, ()):
        targets += _rewriter_rule_targets(rule, name, tokens[1:], powershell)

    if name == "sort":
        outputs = [value for flag, value in _long_or_short_values(tokens, "-o", "--output")]
        targets += _sourced(outputs, powershell)

    if name == "uniq":
        targets += _sourced(_operands(tokens[1:], {"-f", "-s", "-w", "--skip-fields", "--skip-chars", "--check-chars"})[1:2], powershell)

    return targets


def _long_or_short_values(tokens: List[str], short: str, long: str) -> List[Tuple[str, str]]:
    """Every value of an option spelled -o VALUE, -oVALUE, --output VALUE or --output=VALUE."""
    values: List[Tuple[str, str]] = []

    for index, token in enumerate(tokens[1:], start=1):
        following = tokens[index + 1] if index + 1 < len(tokens) else ""

        if token in (short, long) and following:
            values.append((token, following))
        elif token.startswith(long + "="):
            values.append((long, token.split("=", 1)[1]))
        elif token.startswith(short) and not token.startswith("--") and len(token) > len(short):
            values.append((short, token[len(short) :]))

    return values


_UNPLACEABLE_PROGRAM_TARGET = "awk or sed program (a write or a process the gate cannot place)"
_AWK_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')


def _awk_program_targets(code: str) -> List[str]:
    """Files an awk program's print and printf redirect into, and whether it runs a process."""
    masked = _AWK_STRING_RE.sub(lambda match: "S" * len(match.group(0)), code)

    if re.search(r"\bsystem\s*\(|\|\s*getline|\|&", masked):
        return [_UNPLACEABLE_PROGRAM_TARGET]

    targets: List[str] = []

    for statement in re.finditer(r"\bprintf?\b", masked):
        depth = 0
        position = statement.end()

        while position < len(masked) and not (depth == 0 and masked[position] in ";}\n"):
            char = masked[position]
            depth += char == "("
            depth -= char == ")"

            if depth == 0 and char in ">|":
                if char == "|":
                    return [_UNPLACEABLE_PROGRAM_TARGET]

                start = position + (2 if masked.startswith(">>", position) else 1)
                literal = _AWK_STRING_RE.match(code[start:].lstrip())

                if not literal:
                    return [_UNPLACEABLE_PROGRAM_TARGET]

                targets.append(literal.group(0)[1:-1])
                break

            position += 1

    return targets


def _sed_script_targets(script: str) -> List[str]:
    """Files a sed script writes with w, W or the s///w flag, and whether it runs a command with e."""
    targets: List[str] = []
    index = 0

    while index < len(script):
        char = script[index]

        if char in " \t\n;{}!" or char.isdigit() or char in "$,~+":
            index += 1
            continue

        if char == "/" or char == "\\" and index + 1 < len(script):
            custom = char == "\\"
            close = _sed_delimited_end(script, index + (2 if custom else 1), script[index + 1] if custom else "/")
            index = close + 1
            continue

        if char in "wW":
            end = script.find("\n", index)
            targets.append(script[index + 1 : len(script) if end < 0 else end].strip())
            index = len(script) if end < 0 else end
            continue

        if char in "sy" and index + 1 < len(script):
            delimiter = script[index + 1]
            middle = _sed_delimited_end(script, index + 2, delimiter)
            end = _sed_delimited_end(script, middle + 1, delimiter)
            flags_end = end + 1

            while flags_end < len(script) and script[flags_end] not in ";\n}":
                flags_end += 1

            flags = script[end + 1 : flags_end]

            if char == "s" and "e" in flags.split("w", 1)[0]:
                return [_UNPLACEABLE_PROGRAM_TARGET]

            if char == "s" and "w" in flags:
                line_end = script.find("\n", end)
                targets.append(script[end + 1 : len(script) if line_end < 0 else line_end].split("w", 1)[1].strip())
                index = len(script) if line_end < 0 else line_end
                continue

            index = flags_end
            continue

        if char == "e":
            return [_UNPLACEABLE_PROGRAM_TARGET]

        end = min((found for found in (script.find(mark, index) for mark in ";\n") if found >= 0), default=len(script))
        index = end + 1 if char in "aicrRbtTvlqQL:#" else index + 1

    return [target for target in targets if target and target not in ("/dev/stdout", "/dev/stderr")]


def _sed_delimited_end(script: str, index: int, delimiter: str) -> int:
    """Where the next unescaped delimiter sits, or the end of the script."""
    while index < len(script):
        if script[index] == "\\":
            index += 2
            continue

        if script[index] == delimiter:
            return index

        index += 1

    return len(script)


def _program_texts(name: str, tokens: List[str]) -> Optional[List[str]]:
    """The sed script or awk program a command runs, or None when a program file cannot be read."""
    flags = tokens[1:]
    expressions = [value for _flag, value in _long_or_short_values(tokens, "-e", "--expression")] if name in _SED_TOOLS else []
    files = [value for _flag, value in _long_or_short_values(tokens, "-f", "--file")]
    texts = list(expressions)

    for path in files:
        text = _read_script(path)

        if text is None:
            return None

        texts.append(text)

    if texts:
        return texts

    operands = _operands(flags, _SED_VALUE_FLAGS if name in _SED_TOOLS else _AWK_VALUE_FLAGS)

    return operands[:1]


_SQLITE_VALUE_FLAGS = {"-cmd", "-init", "-separator", "-newline", "-nullvalue", "-vfs", "-maxsize", "-mmap", "-pagecache", "-lookaside", "-heap", "-escape"}
_SQLITE_WRITE_RE = re.compile(
    r"(?:^|[\s;])\.(?:output|once|backup|save|clone|excel|shell|system|log|open|import|trace)\b|\battach\b|\bvacuum\s+into\b",
    re.IGNORECASE,
)


def _sqlite_targets(tokens: List[str], powershell: bool = False) -> List[str]:
    """sqlite3 writes its database unless opened read-only, and some dot commands write elsewhere."""
    operands = _operands(tokens[1:], _SQLITE_VALUE_FLAGS)
    readonly = any(token in ("-readonly", "--readonly") for token in tokens[1:])
    commands = [tokens[index + 1] for index, token in enumerate(tokens[:-1]) if token == "-cmd"]
    targets = [] if readonly or not operands or operands[0] == ":memory:" else _sourced(operands[:1], powershell)

    if _SQLITE_WRITE_RE.search(" ".join(operands[1:] + commands)):
        targets.append(_UNPLACEABLE_SCRIPT_TARGET)

    return targets


def _script_program_targets(name: str, tokens: List[str], powershell: bool = False) -> List[str]:
    """Writes made from inside a sed script or an awk program, and by sqlite3."""
    if name == "sqlite3":
        return _sqlite_targets(tokens, powershell)

    if name not in _SED_TOOLS and name not in _AWK_TOOLS:
        return []

    texts = _program_texts(name, tokens)

    if texts is None:
        return [_UNPLACEABLE_PROGRAM_TARGET]

    reader = _sed_script_targets if name in _SED_TOOLS else _awk_program_targets
    found = [target for text in texts for target in reader(text)]
    unplaceable = [target for target in found if target == _UNPLACEABLE_PROGRAM_TARGET]

    return unplaceable or _sourced(found, powershell)


def _started_process_targets(tokens: List[str], depth: int) -> List[str]:
    """What Start-Process runs: its -FilePath with its -ArgumentList, from its -WorkingDirectory."""
    global _CD_BASE
    bound = _ps_bind(tokens, _PS_CMDLETS["start-process"])
    program = _ps_values(bound, "-filepath")

    if _ps_values(bound, "-environment"):
        return [_UNPLACEABLE_ENVIRONMENT_TARGET]

    if not program:
        return []

    arguments = [word for value in _ps_values(bound, "-argumentlist", _PS_UNBOUND) for word in _windows_argv(value)]
    saved = _CD_BASE

    try:
        for directory in _ps_values(bound, "-workingdirectory")[:1]:
            _enter_directory([directory])

        return _segment_targets(program[:1] + arguments, depth + 1, _CMD)
    finally:
        _CD_BASE = saved


_CMD_START_VALUE_SWITCHES = {"d", "node", "affinity"}


def _cmd_start_targets(tokens: List[str], depth: int) -> List[str]:
    """What cmd's start runs. A first quoted word may be the window title, so both readings are judged."""
    global _CD_BASE
    index = 1
    directory = ""

    while index < len(tokens) and _is_windows_switch(tokens[index]):
        switch = tokens[index].lstrip("/-").lower()

        if switch in _CMD_START_VALUE_SWITCHES and index + 1 < len(tokens):
            directory = tokens[index + 1] if switch == "d" else directory
            index += 2
            continue

        index += 1

    rest = tokens[index:]
    saved = _CD_BASE

    try:
        if directory:
            _enter_directory([directory])

        targets: List[str] = []

        for start in (0, 1):
            if rest[start:] and rest[start]:
                targets += _segment_targets(rest[start:], depth + 1, _CMD)

        return targets
    finally:
        _CD_BASE = saved


# What a Rule D denial carries in place of a write target, followed by the
# command. _apply_rules picks the reason by this prefix.
_SCRIPT_RUN = "script run: "

_PROGRAM_ALIASES = {"py": "python", "nodejs": "node", "pip3": "pip"}

# Package and task runners. Every subcommand they take runs project code, a
# package's own scripts, or an install that writes into the project.
_PACKAGE_RUNNERS = {
    "npm",
    "npx",
    "pnpm",
    "pnpx",
    "yarn",
    "bunx",
    "uv",
    "uvx",
    "pip",
    "pipx",
    "poetry",
    "pdm",
    "hatch",
    "tsx",
    "ts-node",
}
_SCRIPT_EXTENSIONS = (
    ".py",
    ".pyw",
    ".sh",
    ".bash",
    ".zsh",
    ".ksh",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".mts",
    ".cts",
    ".ps1",
    ".psm1",
    ".rb",
    ".pl",
    ".php",
    ".bat",
    ".cmd",
)
_PYTHON_OPTION_VALUES = {"-W", "-X"}
_JS_INLINE_FLAGS = {"-e", "--eval", "-p", "--print"}
_JS_SCRIPT_FLAGS = {"--test", "--run"}
_JS_OPTION_VALUES = {"-r", "--require", "--import", "--loader", "--experimental-loader", "--input-type", "--env-file"}
_PERLISH_SCRIPT_TOOLS = {"perl", "ruby", "php", "lua", "luajit", "rscript", "r", "julia"}
# Build runners and compilers. Each one runs a build file, build scripts or
# tests the project supplies, or writes its output into the project, so any
# argument beyond a version or help request is a script run. go is read by
# subcommand instead, see _GO_READ_SUBCOMMANDS.
_BUILD_RUNNERS = {
    "make",
    "gmake",
    "nmake",
    "mingw32-make",
    "cargo",
    "dotnet",
    "msbuild",
    "mvn",
    "mvnw",
    "gradle",
    "gradlew",
    "just",
    "rake",
    "ninja",
    "cmake",
    "bazel",
    "bazelisk",
    "meson",
    "scons",
    "ant",
    "sbt",
    "composer",
    "bundle",
    "tsc",
    "rustc",
    "gcc",
    "g++",
    "cc",
    "c++",
    "clang",
    "clang++",
    "javac",
    "csc",
}
_BUILD_INFO_ARGUMENTS = {
    "--version",
    "-version",
    "-v",
    "-V",
    "--help",
    "-help",
    "-h",
    "-?",
    "/?",
    "--info",
    "--list-sdks",
    "--list-runtimes",
    "version",
    "help",
}
_GO_READ_SUBCOMMANDS = {"version", "help", "doc", "list"}
# Programs that only read, which may be named by an absolute path outside the
# repository, as in /usr/bin/grep. Any other program named by a path is a
# script run, and so is any program at all whose path lands inside the
# repository.
_READ_ONLY_TOOLS = {
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "cat",
    "head",
    "tail",
    "ls",
    "dir",
    "wc",
    "stat",
    "file",
    "which",
    "where",
    "whoami",
    "hostname",
    "uname",
    "id",
    "date",
    "pwd",
    "echo",
    "printf",
    "diff",
    "cmp",
    "du",
    "df",
    "tree",
    "realpath",
    "readlink",
    "dirname",
    "basename",
    "md5sum",
    "sha1sum",
    "sha256sum",
    "sha512sum",
    "findstr",
    "true",
    "false",
}


def _canonical_program(token: str) -> str:
    name = _program_name(token)

    return _PROGRAM_ALIASES.get(name, name)


def _python_runs_script(tokens: List[str]) -> bool:
    """python with a script file or -m, as opposed to -c, stdin, or no program."""
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token.startswith("-m"):
            return True

        if token.startswith("-c") or token == "-":
            return False

        if token in _PYTHON_OPTION_VALUES:
            index += 2
            continue

        if token.startswith("-"):
            index += 1
            continue

        return True

    return False


def _js_runs_script(tokens: List[str]) -> bool:
    """node, bun or deno with a script, a test run or a subcommand, not inline code."""
    index = 1

    while index < len(tokens):
        token = tokens[index]

        if token in _JS_INLINE_FLAGS or token.startswith(("--eval=", "--print=")) or token == "-":
            return False

        if token in _JS_SCRIPT_FLAGS or token.startswith(("--test=", "--run=")):
            return True

        if token in _JS_OPTION_VALUES:
            index += 2
            continue

        if token.startswith("-"):
            index += 1
            continue

        return True

    return False


def _perlish_runs_script(name: str, tokens: List[str]) -> bool:
    """perl, ruby or php with a script file, not -e (or php -r) inline code."""
    inline = "r" if name == "php" else "eE"

    for token in tokens[1:]:
        if token == "-" or (token.startswith("-") and not token.startswith("--") and token[-1] in inline):
            return False

        if not token.startswith("-"):
            return True

    return False


def _is_powershell_code_flag(flag: str) -> bool:
    return (
        flag in _PS_COMMAND_ALIASES
        or flag in _PS_COMMAND_WITH_ARGS_FLAGS
        or flag in _PS_ENCODED_ALIASES
        or _is_prefix_of(flag, _PS_COMMAND_FLAG)
        or _is_prefix_of(flag, _PS_ENCODED_FLAG)
    )


def _powershell_runs_script(tokens: List[str]) -> bool:
    """pwsh handed a script by -File or by position, as opposed to a command or standard input."""
    index = 1

    while index < len(tokens):
        flag = tokens[index].lower()

        if flag in ("-f", "-file") or _is_prefix_of(flag, "-file"):
            return index + 1 < len(tokens) and tokens[index + 1] != "-"

        if _is_powershell_code_flag(flag):
            return False

        if flag in _PS_HOST_VALUE_FLAGS:
            index += 2
            continue

        if flag.startswith("-") and len(flag) > 1:
            index += 1
            continue

        return True

    return False


def _git_runs_a_command(tokens: List[str]) -> bool:
    """git bisect run, rebase --exec, submodule foreach and filter-branch run a command of their own."""
    operands = _operands(tokens[1:], _GIT_VALUE_FLAGS)

    if not operands:
        return False

    if operands[0] == "rebase":
        return any(token in ("-x", "--exec") or token.startswith("--exec=") for token in tokens)

    return operands[0] == "filter-branch" or operands[:2] in (["bisect", "run"], ["submodule", "foreach"])


def _runs_a_program_by_path(program: str, name: str) -> bool:
    """True when a program named by a path is one the project supplies, or one the gate does not know.

    A script file name counts wherever it sits, and so does any program whose
    path resolves inside the repository, whatever its name. Outside the
    repository a read-only tool is allowed, and a program Rule D reads by its
    own rule below is left to that rule. Anything else is a native program the
    gate cannot see into.
    """
    if not (_names_a_path(program) or program.startswith("~")):
        return _basename(program).endswith(_SCRIPT_EXTENSIONS)

    if _basename(program).endswith(_SCRIPT_EXTENSIONS) or _resolves_inside_repo(program):
        return True

    return name not in _READ_ONLY_TOOLS and name not in _RULE_D_PROGRAMS


def _builds(name: str, tokens: List[str]) -> bool:
    """True when a build runner or compiler is asked for more than its version or help."""
    arguments = tokens[1:]

    if name == "go":
        return not arguments or arguments[0] not in _GO_READ_SUBCOMMANDS

    return not arguments or any(argument not in _BUILD_INFO_ARGUMENTS for argument in arguments)


def _runs_a_script(tokens: List[str], dialect: str) -> bool:
    """True when this command, wrappers already peeled, runs a script, a module or a build (Rule D)."""
    words = _split_array(tokens[0]) if tokens else []
    program = words[0] if words else ""
    name = _canonical_program(program)

    if dialect == _CMD and name == "call":
        return len(tokens) > 1 and _runs_a_script(tokens[1:], dialect)

    if _runs_a_program_by_path(program, name):
        return True

    if name == "python":
        return _python_runs_script(tokens)

    if name in _JS_TOOLS:
        return _js_runs_script(tokens)

    if name in _PERLISH_SCRIPT_TOOLS:
        return _perlish_runs_script(name, tokens)

    if name in _PACKAGE_RUNNERS:
        return bool(_operands(tokens[1:]))

    if name in _BUILD_RUNNERS or name == "go":
        return _builds(name, tokens)

    if name == "git":
        return _git_runs_a_command(tokens)

    if name in _POWERSHELL_SHELLS:
        return _powershell_runs_script(tokens)

    if name in _POSIX_SHELLS:
        return _nested_shell_code(name, tokens) is None and not _reads_program_from_stdin(name, tokens)

    return False


# Programs the branches of _runs_a_script read by their own rule.
_RULE_D_PROGRAMS = (
    {"python", "git", "go", "call"}
    | _JS_TOOLS
    | _PERLISH_SCRIPT_TOOLS
    | _PACKAGE_RUNNERS
    | _BUILD_RUNNERS
    | _POWERSHELL_SHELLS
    | _POSIX_SHELLS
    | _CMD_SHELLS
)


def _project_allowlist() -> List[List[str]]:
    """Every entry of each project root's own allowlist file, as words."""
    entries: List[List[str]] = []

    for root in _roots():
        try:
            text = (root / ALLOWLIST_FILE).read_text(encoding="utf-8")
        except (OSError, ValueError):
            continue

        entries += [line.split() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

    return entries


def _names_the_same_file(actual: str, expected: str) -> bool:
    """True when a command word and an allowlisted path name one file, from where the command stands."""
    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())
    written = _as_path(actual)

    for base in bases:
        for root in _roots():
            try:
                here = _resolve(written if written.is_absolute() else base / written)

                if here == _resolve(root / _native_path(expected)):
                    return True
            except (OSError, ValueError, RuntimeError):
                continue

    return False


def _names_a_path(word: str) -> bool:
    return "/" in word or "\\" in word


def _same_program(actual: str, expected: str) -> bool:
    """True when a command's first word runs the program an allowlist entry names.

    An entry naming a path matches only the file it names. An entry naming a
    program matches only a word that names no path, so `./tools/python` is
    never the `python` an entry means.
    """
    if _names_a_path(expected):
        return _names_the_same_file(actual, expected)

    return not _names_a_path(actual) and _canonical_program(actual) == _canonical_program(expected)


def _matches_entry(tokens: List[str], entry: List[str]) -> bool:
    open_ended = bool(entry) and entry[-1] == ANY_ARGUMENTS
    words = entry[:-1] if open_ended else entry

    if not words or not _same_program(tokens[0], words[0]):
        return False

    arguments, expected = tokens[1:], words[1:]

    if len(arguments) < len(expected) or (not open_ended and len(arguments) != len(expected)):
        return False

    return all(
        _names_the_same_file(actual, wanted) if "/" in wanted else actual == wanted
        for actual, wanted in zip(arguments, expected)
    )


def _option_width(token: str, following: List[str], check: AllowedCheck) -> int:
    """How many words an option of a built-in check takes up, or 0 when the check does not allow it."""
    name = token.split("=", 1)[0]

    if token in check.switches or (name in check.valued and "=" in token and name.startswith("--")):
        return 1

    if token in check.valued:
        return 2 if following else 0

    if token.startswith(("--", "+")):
        return 0

    if token[:2] in check.valued:
        return 1

    return 1 if all("-" + letter in check.switches for letter in token[1:]) else 0


def _placed_inside(target: str) -> bool:
    """True only when target names a path that resolves inside a repository root from every base."""
    if not target or _has_glob(target) or _has_expansion(target) or _is_unplaceable_windows_path(target):
        return False

    path = _as_path(target)
    roots = _roots()
    bases = _CD_BASE if _CD_BASE is not None else tuple(roots)

    for base in bases:
        try:
            resolved = _resolve(path if path.is_absolute() else base / path)
        except (OSError, ValueError, RuntimeError):
            return False

        if not any(_is_within(resolved, root) for root in roots):
            return False

    return True


def _passes_check(tokens: List[str], check: AllowedCheck) -> bool:
    """True when a command is this built-in check with only the options it allows."""
    count = len(check.words)

    if len(tokens) < count or not _same_program(tokens[0], check.words[0]) or tokens[1:count] != list(check.words[1:]):
        return False

    operands: List[str] = []
    index = count

    while index < len(tokens):
        token = tokens[index]

        if token == "--":
            operands += tokens[index + 1 :]
            break

        if token.startswith(("-", "+")) and len(token) > 1:
            width = _option_width(token, tokens[index + 1 : index + 2], check)

            if not width:
                return False

            index += width
            continue

        operands.append(token)
        index += 1

    if operands and not check.operands:
        return False

    return not check.inside or all(_placed_inside(operand.split("::", 1)[0]) for operand in operands)


def _allowlisted(tokens: List[str]) -> bool:
    if any(_passes_check(tokens, check) for check in MAIN_THREAD_ALLOWLIST):
        return True

    return any(_matches_entry(tokens, entry) for entry in _project_allowlist())


def _segment_targets(
    tokens: List[str], depth: int, dialect: str = _POSIX, feed: Callable[[], Optional[str]] = _no_input
) -> List[str]:
    if depth > _MAX_NESTING:
        return [_UNPLACEABLE_SHELL_TARGET]

    stripped = _strip_wrappers(tokens, dialect)

    if stripped is None:
        return [_UNPLACEABLE_SHELL_TARGET]

    if stripped.directories:
        return _in_directories(stripped, depth, dialect, feed)

    return _stripped_targets(stripped, depth, dialect, feed)


def _in_directories(
    stripped: _Stripped, depth: int, dialect: str, feed: Callable[[], Optional[str]]
) -> List[str]:
    """What a command run by env --chdir or sudo --chdir writes, from the directory it runs in."""
    global _CD_BASE
    saved = _CD_BASE

    try:
        for directory in stripped.directories:
            _enter_directory([directory])

        return _stripped_targets(stripped._replace(directories=()), depth, dialect, feed)
    finally:
        _CD_BASE = saved


def _stripped_targets(
    stripped: _Stripped, depth: int, dialect: str, feed: Callable[[], Optional[str]]
) -> List[str]:
    rest = stripped.argv

    if not rest or not _split_array(rest[0]):
        return []

    powershell = dialect != _POSIX
    name = _program_name(_split_array(rest[0])[0])
    handler, binds = _handler_for(name, dialect)

    if _sets_unplaceable_environment(rest, dialect):
        return [_UNPLACEABLE_ENVIRONMENT_TARGET]

    if not binds:
        rest = _split_arrays(rest)

    if stripped.xargs:
        rest = _xargs_arguments(rest, stripped.replace, feed())
        feed = _no_input

    if _runs_a_script(rest, dialect) and not _allowlisted(rest):
        return [_SCRIPT_RUN + _rejoined(rest)]

    runner = _code_runner_targets(name, rest, depth, dialect, feed)

    if runner is not None:
        return runner

    if name == "find":
        return _find_targets(rest, depth, dialect)

    targets: List[str] = []

    if name in _INPLACE_TOOLS:
        targets += _inplace_targets(name, rest, powershell)

    if name in _INLINE_CODE_TOOLS:
        targets += _inline_code_targets(rest, powershell)

    if handler is not None:
        targets += handler(rest, powershell)

    if dialect == _POWERSHELL and binds:
        targets += _ps_piped_targets(name, rest, feed, powershell)

    if dialect == _POWERSHELL and _PS_ALIASES.get(name, name) == "start-process":
        targets += _started_process_targets(rest, depth)

    if dialect != _POWERSHELL and name == "start":
        targets += _cmd_start_targets(rest, depth)

    targets += _rewriter_targets(name, rest, powershell)
    targets += _script_program_targets(name, rest, powershell)

    return targets


_ON_WINDOWS = sys.platform == "win32"

# Git Bash and MSYS2 spell a Windows drive as a leading `/<letter>/`, and
# WSL as a leading `/mnt/<letter>/`, read that way only for code run by wsl.
_MSYS_DRIVE = re.compile(r"^/([A-Za-z])(?:/|$)")
_WSL_DRIVE = re.compile(r"^/mnt/([A-Za-z])(?:/|$)")

# How many wsl commands the gate is inside while it reads their code.
_WSL_DEPTH = 0

# Windows spellings of a local path that a plain comparison misses: the
# extended-length and device prefixes \\?\ and \\.\ in front of a drive, the
# NT object prefix \??\, their UNC forms such as \\?\UNC\host\share, and an
# administrative share such as \\localhost\C$ on this machine. Each is read
# as the drive path it names.
_WINDOWS_DEVICE_DRIVE = re.compile(r"^(?:[\\/]{2}[?.]|\\\?\?)[\\/](?=[A-Za-z]:)")
_WINDOWS_DEVICE_UNC = re.compile(r"^(?:[\\/]{2}[?.]|\\\?\?)[\\/]UNC[\\/]", re.IGNORECASE)
_WINDOWS_ADMIN_SHARE = re.compile(r"^[\\/]{2}(?P<host>[^\\/]+)[\\/](?P<drive>[A-Za-z])\$(?P<rest>[\\/].*)?$", re.DOTALL)
# A volume named by its GUID or reached through the object manager's
# GLOBALROOT names a disk the gate has no mapping for.
_WINDOWS_VOLUME_PATH = re.compile(r"^(?:[\\/]{2}[?.]|\\\?\?)[\\/](?:Volume\{|GLOBALROOT[\\/])", re.IGNORECASE)
_LOOPBACK_HOSTS = {"localhost", "localhost.localdomain", "::1", "0:0:0:0:0:0:0:1", "."}
_IPV6_LITERAL_SUFFIX = ".ipv6-literal.net"


@functools.lru_cache(maxsize=None)
def _host_addresses(host: str) -> FrozenSet[str]:
    """Every address a host name or literal resolves to, or none when it does not resolve."""
    import socket

    try:
        found = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError, ValueError):
        return frozenset()

    return frozenset(str(entry[4][0]).split("%", 1)[0] for entry in found)


@functools.lru_cache(maxsize=1)
def _machine_names() -> FrozenSet[str]:
    import socket

    names = {os.environ.get("COMPUTERNAME", ""), socket.gethostname()}

    return frozenset(name.lower() for name in names if name)


def _is_local_address(address: str) -> bool:
    import ipaddress

    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False

    mapped = getattr(parsed, "ipv4_mapped", None)

    if mapped is not None:
        parsed = mapped

    return parsed.is_loopback or parsed.is_unspecified


def _is_this_machine(host: str) -> bool:
    """True when a UNC host names this machine by any spelling that resolves to it.

    That is a loopback or unspecified address in any form, IPv4-mapped IPv6
    included, the machine's own name with or without a domain or a trailing
    dot, and any name or address, a LAN address or an alias, that resolves to
    one of the addresses the machine's own name resolves to.
    """
    name = host.lower().rstrip(".").strip("[]")

    if name.endswith(_IPV6_LITERAL_SUFFIX):
        name = name[: -len(_IPV6_LITERAL_SUFFIX)].replace("-", ":").split("s", 1)[0]

    if name in _LOOPBACK_HOSTS or name.split(".", 1)[0] in _machine_names() or _is_local_address(name):
        return True

    addresses = _host_addresses(name)
    own = set().union(*(_host_addresses(machine) for machine in _machine_names()))

    return any(_is_local_address(address) or address in own for address in addresses)


def _local_windows_spelling(text: str) -> str:
    """A device, extended-length or loopback administrative-share path as the drive path it names."""
    unc = _WINDOWS_DEVICE_UNC.match(text)

    if unc:
        text = "\\\\" + text[unc.end() :]
    else:
        text = _WINDOWS_DEVICE_DRIVE.sub("", text, count=1)

    share = _WINDOWS_ADMIN_SHARE.match(text)

    if share and _is_this_machine(share.group("host")):
        return share.group("drive").upper() + ":" + (share.group("rest") or "\\")

    return text


# A path the boundary helpers cannot place: a loopback UNC share that is not
# an administrative drive share, such as \\localhost\share, names a folder
# only the share definition knows. An administrative drive share on any other
# host may still be this machine under a name the gate does not know, so it
# counts too. So does a volume GUID or GLOBALROOT path. The device namespaces
# \\.\ and \\?\ in front of a drive are not shares and stay out of this rule.
_WINDOWS_UNC_SHARE = re.compile(r"^[\\/]{2}(?P<host>[^\\/]+)[\\/][^\\/]+")
_DEVICE_NAMESPACE_HOSTS = {".", "?"}


def _is_unplaceable_windows_path(target: str) -> bool:
    if not _ON_WINDOWS:
        return False

    if _WINDOWS_VOLUME_PATH.match(target):
        return True

    spelled = _local_windows_spelling(target)

    if _WINDOWS_ADMIN_SHARE.match(spelled):
        return True

    share = _WINDOWS_UNC_SHARE.match(spelled)

    if share is None or share.group("host") in _DEVICE_NAMESPACE_HOSTS:
        return False

    return _is_this_machine(share.group("host"))


def _resolve(path: Path) -> Path:
    """path.resolve(), with a local Windows spelling the result lands on mapped back to its drive.

    A link or junction can resolve to an administrative share on this machine
    or to an extended-length drive path, which the text mapping in _native_path never saw, so the resolved form is mapped
    again and resolved again until it stops changing.
    """
    resolved = path.resolve(strict=False)

    if not _ON_WINDOWS:
        return resolved

    for _attempt in range(_MAX_NESTING):
        text = str(resolved)
        mapped = _local_windows_spelling(text)

        if mapped == text:
            break

        resolved = Path(mapped).resolve(strict=False)

    return resolved


def _native_path(text: str) -> Path:
    """The path a shell or payload string names, in this platform's terms.

    On Windows, a leading forward-slash MSYS drive such as `/c/Users` becomes
    `C:/Users`, because that is the directory Git Bash means by it. A
    backslash `\\c\\Users` stays drive-relative, because Windows resolves it
    against the current drive. POSIX keeps `/c` as the real directory it is
    there, and keeps a backslash as the literal filename character it is.
    """
    if not _ON_WINDOWS:
        return Path(text)

    text = _local_windows_spelling(text)

    if _WSL_DEPTH:
        text = _WSL_DRIVE.sub(lambda match: match.group(1).upper() + ":/", text, count=1)

    return Path(_MSYS_DRIVE.sub(lambda match: match.group(1).upper() + ":/", text, count=1))


def _as_path(target: str) -> Path:
    """The path a target names, with a leading `~` or `~user` expanded.

    Both shells expand the tilde before the command sees it, so without this a
    `rm -rf ~/.cache/x` read as a repository-relative `./~/.cache/x` and was
    denied. A tilde the shell leaves literal never reaches here as a leading
    `~`, because _lex prefixes a quoted one with `./`. A user the interpreter
    cannot look up leaves the path unexpanded, which resolves inside the
    repository and so denies.
    """
    path = _native_path(target)

    if not target.startswith("~"):
        return path

    try:
        return path.expanduser()
    except (RuntimeError, KeyError, OSError):
        return path


def _enter_directory(operands: List[str]) -> None:
    """Move the resolution base to the directory a `cd` segment named.

    A relative destination is resolved against every base the command is
    standing in, which starts as every repository root, so a session started
    in a subdirectory still lands somewhere the boundary check can see. A
    destination that is not a directory on disk is dropped rather than
    trusted, because the real shell refuses that `cd` and stays where it was,
    which leaves the roots to decide the rest of the command.
    """
    global _CD_BASE

    candidates = _operands(operands)

    if not candidates:
        return

    target = _as_path(candidates[-1])
    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())
    landings: List[Path] = []

    for base in bases:
        try:
            resolved = _resolve(target if target.is_absolute() else (base / target))
        except (OSError, ValueError):
            continue

        if resolved.is_dir() and resolved not in landings:
            landings.append(resolved)

    _CD_BASE = tuple(landings) or None


def _in_pipeline(segments: List[ShellSegment], position: int) -> bool:
    """True when a pipe borders this segment, whose stage is a subshell."""
    before = segments[position - 1].control if position else ""
    after = segments[position + 1].control if position + 1 < len(segments) else ""

    return "|" in (before, after)


def _command_targets(command: str, depth: int = 0, dialect: str = _POSIX) -> List[str]:
    """Every write target this command touches, as far as the text reveals it.

    Past _MAX_NESTING the gate stops reading, and a command it has not read
    is one it cannot place, which denies.
    """
    if depth > _MAX_NESTING:
        return [_UNPLACEABLE_SHELL_TARGET]

    global _CD_BASE

    powershell = dialect != _POSIX
    segments = _lex(command, dialect)
    targets = _dotnet_targets(command) if dialect == _POWERSHELL or _reaches_dotnet(command) else []
    groups: List[Optional[Tuple[Path, ...]]] = []

    # Only a POSIX shell runs a parenthesised group in a subshell. In
    # PowerShell and cmd a `cd` inside parentheses moves the shell itself.
    subshells = dialect == _POSIX

    for position, segment in enumerate(segments):
        if segment.control == "(":
            if subshells:
                groups.append(_CD_BASE)
            continue

        if segment.control == ")":
            if subshells and groups:
                _CD_BASE = groups.pop()
            continue

        if segment.control:
            continue

        targets += _sourced(list(segment.redirects), powershell)

        if not segment.argv:
            continue

        argv = list(segment.argv)
        saved = _CD_BASE

        changer = _program_name(argv[0])

        if changer in _DIRECTORY_POPPERS:
            if _CD_STACK:
                _CD_BASE = _CD_STACK.pop()
        elif changer in _DIRECTORY_CHANGERS:
            if changer in _DIRECTORY_PUSHERS:
                _CD_STACK.append(_CD_BASE)

            _enter_directory(_split_arrays(argv[1:]))
        elif segment.expression:
            # A statement opening with a quoted string is a value PowerShell
            # writes to its output, as in [IO.File]::ReadAllText('a/b.py'),
            # and runs nothing. The .NET scan above reads the call itself.
            pass
        else:
            feed = functools.partial(_stdin_of, segments, position, dialect)
            targets += _segment_targets(argv, depth, dialect, feed)

        # Each stage of a POSIX or cmd pipeline runs in its own process, so a
        # `cd` in one of them dies with the stage instead of moving the base
        # for what comes after the pipeline. A PowerShell pipeline runs in the
        # shell itself, where Set-Location sticks.
        if dialect != _POWERSHELL and _in_pipeline(segments, position):
            _CD_BASE = saved

    return targets


def _shell_targets(command: str, dialect: str = _POSIX) -> List[str]:
    """Read one shell command from the start, with `cd` followed as it goes."""
    global _CD_BASE, _CD_STACK

    _CD_BASE = None
    _CD_STACK = []

    try:
        return _command_targets(command, dialect=dialect)
    finally:
        _CD_BASE = None
        _CD_STACK = []


def _is_null_device(target: str, powershell: bool = False) -> bool:
    normalized = target.strip().lower()

    if normalized == _POSIX_NULL_DEVICE:
        return True

    return powershell and normalized in _WINDOWS_NULL_DEVICE_TOKENS


# PowerShell drives and providers that hold no files: environment variables,
# functions, variables, aliases, certificates, the registry, WSMan. A path on
# one of them, such as `Env:PATH` or `Function:prompt`, is never a write of
# the repository, and a POSIX shell or cmd reads the same text as a filename.
_PS_NON_FILE_PATH_RE = re.compile(
    r"^(?:(?:env|function|variable|alias|cert|hklm|hkcu|wsman):"
    r"|(?:microsoft\.powershell\.\w+\\)?(?:environment|function|variable|alias|certificate|registry|wsman)::)",
    re.IGNORECASE,
)


def _names_no_file(target: str, powershell: bool = False) -> bool:
    """True for the null device and, in PowerShell, a path on a provider that holds no files."""
    if _is_null_device(target, powershell):
        return True

    return powershell and bool(_PS_NON_FILE_PATH_RE.match(target.strip()))


_GLOB_CHARACTERS = "*?["
_MAX_GLOBSTARS = 4


def _has_glob(target: str) -> bool:
    return any(char in target for char in _GLOB_CHARACTERS)


def _glob_parts(path: Path, base: Path) -> Tuple[str, ...]:
    """A glob pattern's components once made absolute, its literal lead resolved.

    Only the components before the first wildcard can be resolved on disk,
    so symlinks there are followed and the wildcard components are kept as
    they are, to be matched one component at a time.
    """
    absolute = Path(os.path.abspath(path if path.is_absolute() else base / path)).parts
    lead = next((index for index, part in enumerate(absolute) if _has_glob(part)), len(absolute))
    resolved = _resolve(Path(*absolute[:lead])).parts if lead else ()

    return tuple(resolved) + tuple(absolute[lead:])


def _part_matches(pattern: str, name: str, fold: bool = False) -> bool:
    if _ON_WINDOWS or fold:
        pattern, name = pattern.lower(), name.lower()

    return fnmatch.fnmatchcase(name, pattern)


def _glob_matches(pattern: Tuple[str, ...], parts: Tuple[str, ...], fold: bool = False) -> bool:
    """True when the pattern matches exactly these components, `**` spanning any number."""
    if not pattern:
        return not parts

    if pattern[0] == "**":
        return any(_glob_matches(pattern[1:], parts[skip:], fold) for skip in range(len(parts) + 1))

    return bool(parts) and _part_matches(pattern[0], parts[0], fold) and _glob_matches(pattern[1:], parts[1:], fold)


def _glob_reaches(pattern: Tuple[str, ...], root: Path, inside: bool) -> bool:
    """Whether a glob can name the root or a path below it, or, with inside
    False, the root or a directory above it.

    A pattern with more `**` components than the gate is willing to expand
    counts as reaching, which denies.
    """
    if pattern.count("**") > _MAX_GLOBSTARS:
        return True

    parts = root.parts
    fold = _folds_case(root)

    if inside:
        return any(_glob_matches(pattern[:cut], parts, fold) for cut in range(len(pattern) + 1))

    return any(_glob_matches(pattern, parts[:depth], fold) for depth in range(1, len(parts) + 1))


def _glob_reaches_a_root(target: str, inside: bool) -> bool:
    """_glob_reaches against every root, from every base. Unresolvable is True."""
    path = _as_path(target)
    roots = _roots()
    bases = _CD_BASE if _CD_BASE is not None else tuple(roots)

    for base in bases:
        try:
            pattern = _glob_parts(path, base)
        except (OSError, ValueError, RuntimeError):
            return True

        if any(_glob_reaches(pattern, root, inside) for root in roots):
            return True

    return False


@functools.lru_cache(maxsize=None)
def _folds_case(root: Path) -> bool:
    """True when root sits on a case-insensitive POSIX file system, macOS or a WSL /mnt drive.

    Windows paths already compare without case. Elsewhere the root is looked
    up again with its case swapped, and finding the same directory means the
    file system ignores case, so every comparison against this root must too.
    """
    if _ON_WINDOWS:
        return False

    swapped = Path(str(root).swapcase())

    if swapped == root:
        return False

    try:
        return swapped.exists() and os.path.samefile(swapped, root)
    except (OSError, ValueError):
        return False


def _folded(path: Path, root: Path) -> Tuple[Path, Path]:
    if not _folds_case(root):
        return path, root

    return type(path)(str(path).casefold()), type(root)(str(root).casefold())


def _is_within(path: Path, root: Path) -> bool:
    """path.is_relative_to(root), with the root's own case rule."""
    folded_path, folded_root = _folded(path, root)

    return folded_path.is_relative_to(folded_root)


def _is_above(directory: Path, root: Path) -> bool:
    """root.is_relative_to(directory), with the root's own case rule."""
    folded_root, folded_directory = _folded(root, root)[0], _folded(directory, root)[0]

    return folded_root.is_relative_to(folded_directory)


def _same_path(path: Path, root: Path, other: Path) -> bool:
    """path == other, where other sits under root, with the root's own case rule."""
    return _folded(path, root)[0] == _folded(other, root)[0]


def _resolves_inside_repo(target: str) -> bool:
    """True when target resolves inside the repository boundary.

    Rule A protects this repository, not the rest of the filesystem. Every
    wiring is supposed to cd into the project root before invoking the gate
    (see AGENTS.md "Required opening move"), and that guarantee has broken
    silently once before, which would turn every file above a stray working
    directory into a writable target. A relative path is therefore resolved
    against, and checked against, every root in _roots() (the invocation
    directory, the project root the payload named, and the gate's own
    location two parents up while that is a project rather than a home
    directory), and it counts as inside when it resolves inside any one of
    them. Once the command has changed directory the bases are those
    directories instead (see _CD_BASE), and the roots stay the boundary
    being tested. A glob counts as inside when any path it could match is.
    An unresolvable path fails toward True: failing safe here means
    denying, not allowing, and so does a loopback share no rule can map.
    """
    if _is_unplaceable_windows_path(target):
        return True

    if _has_glob(target):
        return _glob_reaches_a_root(target, inside=True)

    path = _as_path(target)
    roots = _roots()
    bases = _CD_BASE if _CD_BASE is not None else tuple(roots)

    for base in bases:
        try:
            resolved = _resolve(path if path.is_absolute() else (base / path))
        except (OSError, ValueError):
            return True

        if _is_unplaceable_windows_path(str(resolved)) or any(_is_within(resolved, root) for root in roots):
            return True

    return False


def _path_exists_in_repo(candidate: str) -> bool:
    """True when a bare git checkout/restore operand names a path that
    actually exists in any repository root (see _roots()), the one case
    where such an operand is unambiguously a file rather than a branch or
    revision. A glob is a pathspec, never a branch, so it counts. An
    unresolvable path fails toward True for the same reason as
    _resolves_inside_repo.
    """
    if _has_glob(candidate) or _is_unplaceable_windows_path(candidate):
        return True

    path = _as_path(candidate)
    bases = _CD_BASE if _CD_BASE is not None else tuple(_roots())

    for base in bases:
        try:
            if _resolve(path if path.is_absolute() else (base / path)).exists():
                return True
        except (OSError, ValueError):
            return True

    return False


def _is_task_list(target: str) -> bool:
    """True for TASK_LIST_NAME sitting directly in a repository root.

    The main thread owns the task list, so Rule A steps aside for that one
    path. A same-named file in a subdirectory is an ordinary target, and so
    is a glob, which may match more than the task list.
    """
    if _has_glob(target):
        return False

    path = _as_path(target)
    roots = _roots()
    bases = _CD_BASE if _CD_BASE is not None else tuple(roots)

    for base in bases:
        try:
            resolved = _resolve(path if path.is_absolute() else (base / path))
        except (OSError, ValueError):
            continue

        if any(_same_path(resolved, root, root / TASK_LIST_NAME) for root in roots):
            return True

    return False


# Text a shell expands before the command sees it: a POSIX parameter,
# command or brace expansion, a PowerShell variable, and a cmd %VAR% or
# delayed !VAR!. The gate does not know the value, so a target holding one,
# after an absolute prefix or not, is a target it cannot place.
_POSIX_EXPANSION_RE = re.compile(r"\$[A-Za-z_{(@*#?$!0-9-]|\{[^{}\s/]*(?:,|\.\.)[^{}\s/]*\}")
_WINDOWS_EXPANSION_RE = re.compile(r"\$[A-Za-z_{(]|%[^%\s\\/]+%|![^!\s\\/]+!")


def _has_expansion(target: str, powershell: bool = False) -> bool:
    return bool((_WINDOWS_EXPANSION_RE if powershell else _POSIX_EXPANSION_RE).search(target))


def _is_write_target(target: str, powershell: bool = False) -> bool:
    """True for any concrete file path inside the repository, with no
    exemption by extension.

    Rule A denies a main-thread write of any file inside this repository,
    documentation and configuration included: see AGENTS.md "Required
    opening move" for why the earlier per-extension exemption was removed,
    and for why the check stops at the repository boundary and never treats
    the null device as a write. The root task list is the one exemption.
    """
    if not target:
        return False

    if _names_no_file(target, powershell):
        return False

    if _has_expansion(target, powershell):
        return True

    if _is_task_list(target):
        return False

    if target in _WILDCARD_PATHSPECS:
        return True

    return _resolves_inside_repo(target)


def _contains_repo(target: str) -> bool:
    """True when target is a repository root or a directory above one.

    Resolved the same way as _resolves_inside_repo, against the `cd` bases
    or else every root, and it fails the same way too: a path that cannot be
    resolved counts as containing the repository, which denies. A glob such
    as `../agent-*` or `../*` counts when any directory it could match is
    the root or above it, matched one component at a time.
    """
    if _has_glob(target):
        return _glob_reaches_a_root(target, inside=False)

    path = _as_path(target)
    roots = _roots()
    bases = _CD_BASE if _CD_BASE is not None else tuple(roots)

    for base in bases:
        try:
            resolved = _resolve(path if path.is_absolute() else (base / path))
        except (OSError, ValueError):
            return True

        if any(_is_above(resolved, root) for root in roots):
            return True

    return False


def _is_removal_target(target: str, powershell: bool = False) -> bool:
    """True for a path a delete or a move may not take away from the main thread.

    That is every write target, and on top of those any directory holding a
    repository root, since removing or moving it removes the repository.
    """
    if _is_write_target(target, powershell):
        return True

    if not target or _names_no_file(target, powershell):
        return False

    return _contains_repo(target)


def _install_root() -> Optional[Path]:
    """The directory the gate was installed into, two parents up from itself.

    A project keeps the script at <project>/.agents/hooks/preflight_gate.py,
    and the user-level install in docs/GLOBAL_SETUP.md puts the same three
    directories under the home directory instead. Either way this is where
    the rest of the installation, the agent trees Rule B reads included,
    sits beside it.
    """
    try:
        return Path(__file__).resolve().parents[2]
    except (OSError, ValueError, IndexError):
        return None


def _script_root() -> Optional[Path]:
    """The install root, but only while it is a project rather than a home.

    Under the user-level install the install root is the user's home
    directory, or something above it. That is not a project, and keeping it
    as one would make Rule A deny every main-thread write anywhere the user
    keeps files, so it is dropped there and the session's own project decides
    the boundary alone. A home directory the interpreter cannot name leaves
    the root in place, which is the behaviour every project install has had
    all along.
    """
    root = _install_root()

    if root is None:
        return None

    try:
        home = Path.home().resolve()
    except (OSError, ValueError, RuntimeError):
        return root

    return None if home.is_relative_to(root) else root


def _roots() -> List[Path]:
    """Every directory Rule A treats as a project root.

    Path comparison carries the platform's own case rule, so a Windows root
    matches whatever case the payload or the shell spelled it in.
    """
    roots: List[Path] = []

    for candidate in (Path.cwd(), _PAYLOAD_ROOT, _script_root()):
        if candidate is None:
            continue

        try:
            resolved = _resolve(candidate)
        except (OSError, ValueError):
            continue

        if resolved not in roots:
            roots.append(resolved)

    return roots


def _read_agent_definition(agent_type: str) -> Optional[str]:
    """The definition text for one subagent name, or None when there is none.

    Rule B looks in every project root and in the install root as well. The
    install root is not a project boundary, so Rule A drops it, but it is
    where a user-level install keeps its agent trees, and Rule B has to find
    them there.
    """
    if not agent_type or "/" in agent_type or "\\" in agent_type or ".." in agent_type:
        return None

    roots = _roots()
    install = _install_root()

    if install is not None and install not in roots:
        roots.append(install)

    for root in roots:
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
    global _PAYLOAD_ROOT

    _PAYLOAD_ROOT = _payload_root(payload)

    try:
        return _apply_rules(payload, fmt, subagent_flag)
    finally:
        _PAYLOAD_ROOT = None


def _apply_rules(payload: Dict[str, Any], fmt: str, subagent_flag: bool) -> Optional[str]:
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

    values = [tool_input[key] for key in COMMAND_KEYS if tool_input.get(key) not in (None, "")]

    # A tool the gate does not know that still carries a command is a shell
    # by another name, and a command that is not a string cannot be read.
    if tool not in SHELL_TOOLS or any(not isinstance(value, str) for value in values):
        return RULE_A_REASON.format(target=_UNPLACEABLE_SHELL_TARGET) if values and tool not in RESEARCH_TOOLS else None

    command = next((value for value in values if value.strip()), "")

    if not command:
        return None

    try:
        targets = _shell_targets(command, _POWERSHELL if tool in _POWERSHELL_SHELLS else _POSIX)
    except _ShellParseError:
        return None

    if targets and targets[0].startswith(_SCRIPT_RUN):
        return RULE_D_REASON.format(command=targets[0][len(_SCRIPT_RUN) :])

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
    """Read --format and --subagent by hand, never through argparse.

    argparse exits 2 on a usage error, and 2 is the deny code in the plain
    format, so a stray flag would read as a block (docs/hooks-contract.md).
    An unknown or missing format returns "", which main() turns into an
    allow.
    """
    tokens = list(argv if argv is not None else sys.argv[1:])
    fmt = ""
    subagent = False
    index = 0

    while index < len(tokens):
        token = tokens[index]

        if token == "--format" and index + 1 < len(tokens):
            fmt = tokens[index + 1]
            index += 2
            continue

        if token.startswith("--format="):
            fmt = token.split("=", 1)[1]
        elif token == "--subagent":
            subagent = True

        index += 1

    return (fmt if fmt in FORMATS else ""), subagent


def _speaks_contract(payload: Dict[str, Any]) -> bool:
    """Whether a runner envelope names a version this gate understands.

    A payload with no `contract` field is read as the current version, so a
    hand-built plain payload keeps working.
    """
    version = payload.get("contract", max(CONTRACTS))

    return type(version) is int and version in CONTRACTS


def main(argv: Optional[List[str]] = None) -> int:
    real_stderr = sys.stderr
    sys.stderr = io.StringIO()

    try:
        fmt, subagent_flag = _parse_args(argv)

        if not fmt:
            return 0

        try:
            raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
            payload = _as_dict(json.loads(raw or "{}"))

            if fmt == "plain" and not _speaks_contract(payload):
                return 0

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
