# The hook runner contract

Every `*.py` file in [.agents/hooks/](../.agents/hooks/) is a hook. The OpenCode and Kilo Code plugin
[.agents/plugin/hooks.js](../.agents/plugin/hooks.js) discovers them at runtime and runs them all. There is no
registry, no manifest, and no list to keep in sync: dropping a file in that directory is the whole registration step,
and a project that checks out only some of these files runs only the ones it has.

This file stays in the agent-standards repo only. It is not shipped to consumer projects.

Claude Code, Codex, and GitHub Copilot do not use the runner. They call individual hooks straight from their own
configuration with `--format claude`, `--format codex`, or `--format copilot`. Those wirings are unaffected by anything
below, and a hook that wants to serve them keeps whatever extra formats and modes it needs. They anchor the hook at the
project root themselves and discard a non-zero exit, because those three formats deny with exit 0 on stdout, so a
missing hook allows there for the same reason it allows here.

---

### Discovery

A file is picked up when all of these hold:

1. It sits directly in `.agents/hooks/`, not in a subdirectory.
2. Its name ends in `.py`.
3. Its name does not start with `_` or `.`, so `__pycache__` and editor droppings are skipped.

The directory is re-read on every tool call. A hook added mid-session takes effect on the next call, with no restart
and no edit to the plugin.

The executable bit is irrelevant. Hooks are always run through the interpreter, so the shebang is decoration and
nothing needs `chmod +x`. This is also why the same file works unchanged on Windows.

---

### Invocation

The runner spawns each hook as:

```text
python3 -S -E <hook path> --format plain
```

The interpreter is `python` on Windows and `python3` everywhere else, because Windows has no `python3` on the path from
a standard install. `-S` skips site initialisation and `-E` ignores the `PYTHON*` environment variables, which takes a
slice off the interpreter start the runner pays on every tool call. Both are safe here only because every hook is
standard library only. A hook that needs an installed package does not belong in this directory.

The working directory is set to the project root, and one JSON object, the envelope, arrives on standard input. There
are no other arguments. Everything a hook needs is in the envelope.

Read standard input as bytes and decode it as UTF-8 yourself. On Windows, `sys.stdin.read()` decodes with the system
code page, which mangles the prose fields.

```python
payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
```

---

### The envelope

```json
{
  "contract": 2,
  "event": "tool.execute.before",
  "tool_name": "Edit",
  "tool_input": {"file_path": "src/app.py"},
  "agent_type": "python-pro",
  "is_subagent": true,
  "assistant_text": "the newest assistant prose, or an empty string",
  "cwd": "/absolute/path/to/project"
}
```

| Field | Meaning |
| --- | --- |
| `contract` | Envelope version, currently `2`. A hook that does not recognise the value must exit 0. |
| `event` | The runtime event that produced the call. Only `tool.execute.before` exists today. |
| `tool_name` | The tool about to run, or `""` when the event carries no tool. |
| `tool_input` | The tool's arguments as an object, `{}` when the runtime gave none. |
| `agent_type` | Name of the acting subagent, `""` on the main thread. |
| `is_subagent` | `true` when a subagent is acting. |
| `assistant_text` | The newest assistant prose not yet delivered in this session, `""` when there is none. |
| `cwd` | Absolute project root. The same directory the process already runs in. |

`assistant_text` is delivered at most once per distinct text per session. The runner does the de-duplication, so a hook
that checks prose does not have to, and a run of tool calls after one reply does not block twice on prose the model
cannot change mid-turn.

---

### Applicability

Every hook runs on every event. There is no declaration of what a hook cares about, and the runner never decides
whether a hook is relevant.

That decision belongs to the hook because it is a rule, and rules do not live in the plugin. A declaration would also
be a second place to keep the truth, free to drift from the code it describes, and a hook could not change its mind
about what it cares about without an edit somewhere else.

The cost is one interpreter start for a hook that turns out not to apply. Keep the not-applicable path at the top of
`main()` and return 0 before doing any real work.

```python
if payload.get("event") != "tool.execute.before":
    return 0

if not payload.get("assistant_text", "").strip():
    return 0
```

---

### Order

Hooks run in ascending `HOOK_ORDER`, and ties break on the file name. Declare it as a plain module-level integer near
the top of the file:

```python
HOOK_ORDER = 10
```

The runner reads it out of the first 4096 characters of the file. A hook that declares nothing gets `100`, which puts
it after the shipped hooks and keeps a third hook working before anyone thinks about ordering.

Current values:

| Order | Hook | Why there |
| --- | --- | --- |
| 10 | `preflight_gate.py` | A policy denial about the action being attempted outranks a note about prose already sent. |
| 20 | `no_ai_markers_check.py` | Formatting, checked only when there is new prose to check. |
| 30 | `task_list_sync.py` | Bookkeeping, and it never denies. It exits 0 immediately on the plain format. |
| 40 | `markdown_lint_check.py` | Gated behind `--format claude` only. It exits 0 at once on the plain format. |

The first denial stops the chain. Later hooks are not run.

---

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Allow. The hook did not apply, or it applied and found nothing. Anything on stdout is ignored. |
| 2 | Deny. The runner aborts the tool call and shows the hook's stderr to the model. |
| anything else | Allow. |

Exit 2 is the only denial, which means nothing else in the hook may exit 2 on your behalf. `argparse` exits 2 on a
usage error, so either parse arguments yourself or catch `SystemExit`. A hook that exits 2 because of a bad flag looks
exactly like a hook that blocked the call.

Write the denial reason to stderr as UTF-8 bytes. It is the entire message the model sees, so it has to say what was
blocked and what to do instead. A hook that exits 2 with empty stderr gets a bare `Blocked by <file name>.`

```python
sys.stderr.buffer.write(reason.encode("utf-8"))
sys.stderr.buffer.flush()
return 2
```

---

### Failing open

A broken hook must never break a session. The runner treats all of these as an allow and moves to the next hook:

- the file is missing or cannot be opened, in which case it is dropped before it is ever run
- the file is not valid Python
- the interpreter is absent or fails to spawn
- the hook crashes, is killed by a signal, or exceeds the 10 second timeout
- the hook exits with any code other than 2

The first of those matters more than it looks. Python exits 2 when it cannot open the script it was handed, and 2 is
the denial code, so the runner reads every candidate file itself and skips the ones it cannot open rather than letting
the interpreter turn an I/O error into a block.

An unreadable `.agents/hooks/` directory yields no hooks, which allows every call. Write your own hook the same way:
wrap the body in `try` and return 0 on any exception.

---

### Events the other three agents wire directly

The runner has one event. The three agents that call hooks from their own configuration have many, and the table below
is what this repo wires today. Each cell names the event in that agent's own spelling.

| Hook | Claude Code | Codex | GitHub Copilot |
| --- | --- | --- | --- |
| `preflight_gate.py` | `PreToolUse` | `PreToolUse` | `preToolUse` |
| `no_ai_markers_check.py` | `Stop`, `SubagentStop` | `Stop` | not wired, no confirmed reply-formatting surface |
| `task_list_sync.py` | `TaskCreated`, `TaskCompleted`, `SessionStart`, `PreCompact`, `Stop` | `SessionStart` | `sessionStart` |
| `markdown_lint_check.py` | `PostToolUse` on `Edit`, `Write`, `MultiEdit` | not wired | not wired |

Three limits behind that table are worth knowing before extending it.

Only Claude Code has task events. `TaskCreated` and `TaskCompleted` carry `task_id` and `task_subject`, and no
task-updated event exists on any of the three, which is why the hook writes only the open and done statuses and leaves
in progress and blocked to the model editing the file. The task id is written between backticks in the file, for
example ``- [open] `feat:001`: subject``, and a bare id with no backticks is still read back for a hand-written line.

No agent delivers `additionalContext` from a pre-compact event. Claude Code lists the delivery points for the field and
`PreCompact` is not among them, Codex gives `PreCompact` the common output fields only, and Copilot marks `preCompact`
as notification only. The `PreCompact` entry above is therefore wiring against a future, and the mechanism that
actually carries a task list through a compaction is `SessionStart` firing again with `source` set to `compact`, which
both Claude Code and Codex document.

OpenCode and Kilo Code have neither a session-start nor a pre-compact event, so nothing can be injected there at all.
That is the same gap that keeps per-turn gate injection out of the plugin, and it is why the plugin is a tool-call
runner and nothing more.

The markdown lint is the only hook wired to a post-tool event, and it is also the only one gated behind a single
format rather than run on the runner surface. `markdown_lint_check.py` returns 0 before it even reads standard input
unless it is called with `--format claude`, returns 0 for any tool other than `Edit`, `Write`, or `MultiEdit`, and
returns 0 when `tools/check-markdown.py` is missing, which every consumer checkout is, since `tools/` never ships
downstream. On OpenCode, on Kilo Code, and in a consumer repository it therefore does nothing at all. Only here, on
Claude Code, does it read the edited path from `tool_input.file_path`, check that path against the lint scope
(`README.md`, `AGENTS.md.example`, `docs/`, `.agents/skills/` and `subagents/`), run `tools/check-markdown.py` over
that one file, and hand the violations back as `additionalContext`. It reports rather than denies, so it always
returns 0 there too.

The same script also validates front matter on every `.agents/skills/*/SKILL.md` and `subagents/*.md` file it lints:
the block has to parse as YAML, `name` has to match the skill folder or the subagent file stem, and `description` has
to be a non-empty single-line string of at most 1024 characters. A skill's front matter may carry only `name`,
`description`, `license`, `compatibility` and `metadata`, and a description containing a colon followed by a space
has to be double-quoted, because GitHub Copilot refuses to load a manifest that breaks that rule.

---

### A third hook, end to end

```python
#!/usr/bin/env python3
"""Blocks a Bash call that pipes a remote script straight into a shell."""

import json
import sys

HOOK_ORDER = 30

REASON = "PREFLIGHT: piping a downloaded script into a shell is not allowed. Fetch it, read it, then run it."


def main(argv):
    try:
        if "--format" not in argv:
            return 0

        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")

        if payload.get("tool_name", "").lower() not in ("bash", "shell"):
            return 0

        command = payload.get("tool_input", {}).get("command", "")

        if "curl" not in command or "| sh" not in command:
            return 0

        sys.stderr.buffer.write(REASON.encode("utf-8"))
        sys.stderr.buffer.flush()

        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

Drop that file into [.agents/hooks/](../.agents/hooks/) and it is live on the next tool call.
