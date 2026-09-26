# The hook runner contract

Every `*.py` file directly in [.agents/hooks/](../.agents/hooks/) is a hook. The OpenCode and Kilo Code plugin
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

The runner first picks one hooks directory, in this order, and stops at the first match:

1. `<project root>/.agents/hooks/` whenever that directory exists, even empty.
2. Nothing at all when `<project root>/.agents/no-global-hooks` exists. That file is the per-project opt-out from the
   global fallback, and only its presence counts. It never switches off a project's own `.agents/hooks/`.
3. `.agents/hooks/` under the user's home directory, where [GLOBAL_SETUP.md](GLOBAL_SETUP.md) installs the hooks
   (`os.homedir()`, so `%USERPROFILE%` on Windows and `$HOME` elsewhere).

A hook from the global directory runs exactly like a project one: its working directory and the envelope's `cwd` are
the project root, so the gate protects the open project rather than the home directory. A directory that does not exist
yields no hooks, which allows the call.

Inside the chosen directory, a file is picked up when all of these hold:

1. It sits directly in `.agents/hooks/`, not in a subdirectory.
2. Its name ends in `.py`.
3. Its name does not start with `_` or `.`, so `__pycache__` and editor droppings are skipped.

The choice of directory and its listing are both re-read on every tool call. A hook added mid-session, an opt-out
file created, or a project import landing takes effect on the next call, with no restart and no edit to the plugin.

The first rule is also the one way to keep a script out of the runner. A helper that only one agent calls, from its
own wiring and on an event the runner never sees, goes in a subdirectory named for that agent, so it costs OpenCode and
Kilo Code no interpreter start on every tool call. The one such helper today is
[.agents/hooks/copilot/prompt_reminder.py](../.agents/hooks/copilot/prompt_reminder.py), which GitHub Copilot runs on
`userPromptTransformed`. It still ships with every import, because every pathspec pulls `.agents/hooks` whole.

The executable bit is irrelevant. Hooks are always run through the interpreter, so the shebang is decoration and
nothing needs `chmod +x`. This is also why the same file works unchanged on Windows.

---

### Invocation

The runner spawns each hook as:

```text
python3 -S -E <hook path> --format plain
```

The interpreter is `python3` when that name answers and `python` otherwise, because Debian and Ubuntu ship no `python`
and the python.org Windows installer ships no `python3`. The runner decides on its first call by running `-S -E
-c` with a one-line probe under each name in turn and keeping the first that prints the expected answer, so a Windows
Store alias that exists under either name but runs nothing is skipped. A failed probe is retried on the next call, and
when neither name answers no hook runs and the call is allowed. `-S` skips site initialisation and `-E` ignores the
`PYTHON*` environment variables, which takes a slice off the interpreter start the runner pays on every tool call. Both
are safe here only because every hook is standard library only. A hook that needs an installed package does not belong
in this directory.

The working directory is set to the project root, and one JSON object, the envelope, arrives on standard input. There
are no other arguments. Everything a hook needs is in the envelope.

The spawn is asynchronous, with the runner's own 10 second timer. `spawnSync` was measured returning `ETIMEDOUT`
within 100 ms on most tool calls after the first, under the Bun runtime OpenCode 1.18.32 and Kilo Code 7.7.9 ship on
Windows, which skipped every hook on those calls without a trace.

Read standard input as bytes and decode it as UTF-8 yourself. On Windows, `sys.stdin.read()` decodes with the system
code page, which mangles the prose fields.

```python
payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace") or "{}")
```

---

### The envelope

```json
{
  "contract": 3,
  "event": "tool.execute.before",
  "tool_name": "Edit",
  "tool_input": {"file_path": "src/app.py"},
  "agent_type": "general",
  "is_subagent": true,
  "assistant_text": "the newest assistant prose, or an empty string",
  "cwd": "/absolute/path/to/project"
}
```

| Field | Meaning |
| --- | --- |
| `contract` | Envelope version, currently `3`. A hook that does not recognise the value must exit 0. The shipped hooks read a missing field as the current version. |
| `event` | The runtime event that produced the call, `tool.execute.before` or `experimental.text.complete`. |
| `tool_name` | The tool about to run, or `""` when the event carries no tool. |
| `tool_input` | The tool's arguments as an object, `{}` when the runtime gave none. |
| `agent_type` | Name of the acting agent, primary or subagent, `""` when no message in the session names one. |
| `is_subagent` | `true` in a child session, `false` in a root session, absent when the session could not be read. |
| `assistant_text` | The newest assistant prose not yet delivered in this session, `""` when there is none. |
| `cwd` | Absolute project root. The same directory the process already runs in, and the root the gate protects. |
| `text` | Only on `experimental.text.complete`: the finished text part. Absent on a tool call. |

Neither runtime names the caller on `tool.execute.before`, whose input is only `tool`, `sessionID` and `callID`. The
runner reads the session with `client.session.get`: a session with a `parentID` is a subagent's child session, and one
without is the main thread. The answer is cached per session for the life of the plugin, and a failed lookup is
retried on the next call rather than cached. The agent name comes from `client.session.messages`, the newest message
carrying an `agent` or `mode` field, because neither runtime's session object has an agent field. Leaving
`is_subagent` out is how a failed lookup fails open: the gate treats anything but a real boolean as an unknown caller
and allows. The runner asks for only the newest eight messages (`query.limit`, which both runtimes answer with the
newest messages in oldest-first order), and reads the whole history only when all eight came back and they still name
no agent or carry no assistant prose.

Version 3 changed two meanings. `agent_type` now names the primary agent as well, so it no longer tells the main thread
from a subagent on its own, and `is_subagent` may be absent. Version 2 always sent `is_subagent`, and a hook reading a
version 2 envelope could treat its absence as `false`.

`assistant_text` is delivered at most once per distinct text per session. The runner does the de-duplication, so a hook
that checks prose does not have to, and a run of tool calls after one reply does not block twice on prose the model
cannot change mid-turn.

The second event is `experimental.text.complete`, which both runtimes fire once per finished text part with input
`{sessionID, messageID, partID}` and output `{text}` (plugin
[types](https://github.com/anomalyco/opencode/blob/dev/packages/plugin/src/index.ts)). The runner hands every hook the
same envelope, but only to a hook that declares the text event (see Applicability below), with `event` set to that
name, `text` holding the part, `tool_name` and `assistant_text` empty, and no session lookup, so `agent_type` is empty
and `is_subagent` is absent. A hook that wants to replace the text prints one
JSON object, `{"text": "..."}`, on stdout and exits 0. The next hook sees the replacement, and whatever the last hook
leaves is what the runtime stores in place of the part. The event cannot be denied, so exit 2 means nothing here, and
any other outcome keeps the text as it was. The raw text has already streamed to the screen by then, so the stored
version replaces it once the part is finished. The hook name carries the `experimental` prefix in OpenCode 1.18.32 and
Kilo Code 7.7.9, so recheck it on every upgrade.

---

### Applicability

Every hook runs on every tool call. There is no declaration of which tools a hook cares about, and the runner never
decides whether a hook is relevant to a call.

That decision belongs to the hook because it is a rule, and rules do not live in the plugin. A declaration would also
be a second place to keep the truth, free to drift from the code it describes, and a hook could not change its mind
about what it cares about without an edit somewhere else.

The one exception is `experimental.text.complete`, which fires once per finished text part, several times in a single
reply, and which only a hook that rewrites prose has any use for. A hook opts in with one module-level line near the
top of the file, read the same way as `HOOK_ORDER`:

```python
HOOK_TEXT_EVENT = True
```

A hook without that line never sees the event, so a text part costs no interpreter start for the gate, the task list
or the markdown lint. `no_ai_markers_check.py` is the one shipped hook that declares it.

The cost on a tool call is one interpreter start for a hook that turns out not to apply. Keep the not-applicable path
at the top of `main()` and return 0 before doing any real work.

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

The runner reads it, and `HOOK_TEXT_EVENT`, out of the first 16384 characters of the file. A hook that declares
nothing gets `100`, which puts it after the shipped hooks and keeps a third hook working before anyone thinks about
ordering.

Current values:

| Order | Hook | Why there |
| --- | --- | --- |
| 10 | `preflight_gate.py` | A policy denial about the action being attempted outranks a note about prose already sent. |
| 20 | `no_ai_markers_check.py` | Formatting, checked only when there is new prose to check. It is also the one hook that rewrites a finished text part. |
| 30 | `task_list_sync.py` | Bookkeeping, and it never denies. It exits 0 immediately on the plain format. |
| 40 | `markdown_lint_check.py` | Gated behind `--format claude` only. It exits 0 at once on the plain format. |

The first denial stops the chain. Later hooks are not run.

---

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Allow. The hook did not apply, or it applied and found nothing. Stdout is ignored, except the replacement text on `experimental.text.complete`. |
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
- the hook crashes, is killed by a signal, or exceeds the 10 second timeout, in which case the runner kills it
- the hook exits with any code other than 2

The first of those matters more than it looks. Python exits 2 when it cannot open the script it was handed, and 2 is
the denial code, so the runner reads every candidate file itself and skips the ones it cannot open rather than letting
the interpreter turn an I/O error into a block.

A session the runner cannot read leaves `is_subagent` out of the envelope, which the gate reads as an unknown caller.

An unreadable hooks directory yields no hooks, which allows every call. Write your own hook the same way:
wrap the body in `try` and return 0 on any exception.

---

### Events the other three agents wire directly

The runner has one event. The three agents that call hooks from their own configuration have many, and the table below
is what this repo wires today. Each cell names the event in that agent's own spelling.

| Hook | Claude Code | Codex | GitHub Copilot |
| --- | --- | --- | --- |
| `preflight_gate.py` | `PreToolUse` | `PreToolUse` | `preToolUse` |
| `no_ai_markers_check.py` | `MessageDisplay`, `Stop`, `SubagentStop` | `Stop` | `agentStop` |
| `task_list_sync.py` | `TaskCreated`, `TaskCompleted`, `SessionStart`, `PreCompact`, `Stop` | `SessionStart` | `sessionStart` |
| `markdown_lint_check.py` | `PostToolUse` on `Edit`, `Write`, `MultiEdit` | not wired | not wired |
| `copilot/prompt_reminder.py` | not wired | not wired | `userPromptTransformed` |

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

OpenCode and Kilo Code have neither a session-start nor a pre-compact event, so nothing can be injected at either
point. The per-prompt gate reminder does reach the model: the plugin's `chat.message` handler, a stable hook in both
runtimes, appends the reminder as a synthetic text part to every user message of a root session. The runtime saves
the parts after the handler returns and sends every text part that is not `ignored` to the model. Measured on OpenCode
1.18.32 and Kilo Code 7.7.9: the model quoted the reminder back verbatim. The reminder is wording, not a rule, so it is
the one thing the plugin carries rather than a hook in this directory.

What reaches a subagent is its own definition, the project's `AGENTS.md`, the gate on every tool call, and the
subagent text from the Required opening move in [AGENTS.md](../AGENTS.md), never the reminder. The reminder tells its
reader to delegate, and a subagent told that turns its own task away. The subagent text says the delegation and
no-write rules belong to the main thread and tells the subagent to do the work itself. The `chat.message` handler also
fires for the task prompt that starts a subagent's child session, so the plugin places the session with the same
cached `client.session.get` lookup the runner uses: no `parentID` gets the reminder, a `parentID` gets the subagent
text, and a session the lookup cannot read gets neither. Claude Code and Codex inject the subagent text on
`SubagentStart` and Copilot on `subagentStart`, each as `additionalContext`. Claude Code carries the reminder on
`UserPromptSubmit` and `SessionStart`, and its hooks reference names tool events as the ones that fire inside a
subagent, so the reminder is not expected to reach a Claude Code subagent. That last point is read from the reference
and not measured. Codex does run `UserPromptSubmit` for the message that starts a subagent: live run 36163866070
recorded the reminder in a docs-architect rollout, right after the subagent text. Its payload carries `agent_id` only
inside a subagent, per the input schema Codex 0.150.1 embeds, so the Codex reminder command prints nothing when the
payload holds an `"agent_id"` key. Copilot runs `userPromptTransformed` for the prompt that opens a subagent's session
too, and live run 36176881215 recorded the reminder appended to two of them. That payload carries only the subagent's
own `sessionId`, but Copilot CLI 1.0.81 puts the `subagentStart` text at the start of the subagent's `prompt`, so
`prompt_reminder.py` prints nothing for a prompt that opens with `PREFLIGHT for a subagent:`. A later prompt in the same
subagent session, such as a formatting block reason, carries neither marker nor agent id and still gets the reminder.

The line breaks and blank lines in both texts are part of the wording, so every wiring delivers real newlines to the
model. Claude Code prints plain text through `echo` with the newlines inside the single-quoted literal, which `sh`,
Git Bash and PowerShell all print unchanged. Codex and Copilot read JSON, so they carry `\n` escapes inside
`additionalContext`, printed by `printf '%s\n'` in a POSIX shell, because `dash` turns an `echo` argument's `\n` into a
raw newline that breaks the JSON, and by `echo` in PowerShell, which prints a single-quoted literal as written. The
plugin and [.agents/hooks/copilot/prompt_reminder.py](../.agents/hooks/copilot/prompt_reminder.py) hold the text as a
string constant.

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

The formatting check blocks a reply that is already on screen. Claude Code shows the block reason to the model "as a
system reminder so it understands why it must continue" ([hooks](https://code.claude.com/docs/en/hooks)), and Codex
"automatically creates a new continuation prompt that acts as a new user prompt, using your `reason` as that prompt
text" ([hooks](https://learn.chatgpt.com/docs/hooks)). A reason that asked for the whole reply again made the user read
it twice, so the reason now lists what it found and asks only for the fixed sentences, one per line, each starting with
`Correction:` and quoting the fixed text, with nothing else. Every format uses that same wording for a reply on
screen. A subagent's reply is not on screen: it is the report its caller receives, and the subagent's next reply
replaces it. Live run 36176881215 recorded the cost on Copilot, where the corrected turn became the whole task result
and the main thread never read the subagent's report. A stop payload naming `SubagentStop`, or carrying `agent_id` or
Copilot's `agentId`, therefore gets a reason that asks for the whole report again with every violation fixed.

Where a surface can rewrite what the user sees, the hook fixes the mechanical markers itself and blocks only on what
is left. `fix_prose` turns a dash into a comma with clean spacing (a hyphen in a digit range such as `3-5`), strips
bold except the NOW line, and strips italic, leaving code spans, fenced blocks, link targets and URLs exactly as
written. It works line by line, so a batch of whole lines comes out the same as the whole text. A semicolon joining
two clauses needs the sentence read, so it is never fixed, only reported.

Claude Code 2.1.152 and later runs `MessageDisplay` "while assistant message text is displayed", and "`displayContent`
replaces the displayed text on screen. Display-only: the transcript and what Claude sees keep the original"
([hooks](https://code.claude.com/docs/en/hooks)). The wiring calls `no_ai_markers_check.py --format claude --display`,
which prints the fixed batch as `displayContent` and prints nothing when there is nothing to fix. Interactive sessions
send a batch of newly completed lines at a time, and `claude -p` sends the whole message once. A fenced block can span
batches, so the fence still open after a batch is kept in a small file in the payload's `scratchpad_dir`, or in a
private `agent-standards-<user>` directory under the system temp directory when the payload names none, and the file
goes when the fence closes or the message ends. When neither place is usable, a later batch is shown unchanged rather
than risk rewriting code. The event cannot block and never fires for a subagent's messages.

The same state file records, under each `message_id`, the original text of every line the display fix changed, for
the newest 16 messages of the session. Its `Stop` wiring passes `--display-fixed`, which reads that record and runs
only the recorded lines through the fix before checking, then clears the record. The `Stop` payload names no message,
and the display's `message_id` "can't be correlated with transcript message ids", so the lines of every recorded
message in the session count. A line the display never fixed, and a reply with no record at all, because the display
hook is older than 2.1.152, failed, or could not write its file, is checked in full. The check therefore blocks only
on what the display could not fix, a semicolon or a bold run that spans lines, and never asks for a correction of a
slip the user did not see. `SubagentStop` keeps the full check. Measured on Claude Code 2.1.281 with `claude -p`: a
reply holding an em dash and a bold word was shown as `The plan is simple, delegate the work.`, `MessageDisplay` ran
before `Stop`, and the Stop hook stayed silent. Replaying the captured `Stop` payload once the record was gone
blocked on the em dash. Two `MessageDisplay` hooks on one message both received the original text and one replacement
was shown, never both.

OpenCode and Kilo Code store the fixed text part through `experimental.text.complete`, described above, so the
runner check at the next tool call reads the fixed text and blocks only on what remains. Codex has no display hook,
so its `Stop` keeps the full check.

GitHub Copilot has no display hook for the main agent either, so `agentStop` runs the full check. Its payload names
only `transcriptPath`, and the hook reads the newest `assistant.message` event with text from that file. GitHub does
not document the transcript format, so a line the parser does not recognise is skipped and a file it cannot read
allows. A block "forces another agent turn using `reason` as the prompt" ([hooks
reference](https://docs.github.com/en/copilot/reference/hooks-reference)). The same page lists `stop_hook_active` in
the camelCase `agentStop` payload, "true when this turn was already forced to continue by a prior "block" decision
from this hook", and the hook also accepts the camelCase spelling `stopHookActive` in case a payload uses it. Neither
flag is trusted to arrive: the hook keeps a counter of blocks in a row per session, in a
`no-ai-markers-stop-<session>.json` file beside the display state, allows the next stop after a block, and resets the
counter whenever a stop is allowed. A payload with no session id cannot be counted and blocks as before, which the
agent's own override bounds: "After 8 consecutive `block` continuations, the CLI overrides the hook and ends the turn
anyway". Claude Code documents the same cap of 8 for its `Stop`.

The Copilot CLI also runs the hooks in `.claude/settings.json`. The JetBrains plugin does not: its bundled agent
hardcodes `.github/hooks/**/*.json` and rejects PascalCase event names. Measured on Copilot CLI 1.0.81 in the sandbox
image, the CLI maps its own tool names to Claude's (`create` reaches the hook as `Write`) and hands the gate a
Claude-shaped payload (`hook_event_name`, `session_id`, an ISO `timestamp`, `cwd`, `tool_name`, `tool_input`) that
carries no `agent_id` for a subagent and a main thread alike. Read as Claude Code's, that absence named every caller
the main thread, so live run 36155485254 denied the docs-architect subagent's own write under Rule A. The CLI sets
`COPILOT_CLI=1` in the hook's environment, and the gate reads a claude-format call carrying it, and no
`transcript_path`, as an unknown caller, the same verdict
[.github/hooks/preflight.json](../.github/hooks/preflight.json) gets. Claude Code always sends `transcript_path` and
the Copilot CLI does not, so a Claude Code session that inherited the variable from a Copilot shell stays identified.
The Claude matcher is not widened to Copilot's tool names, because the CLI reads both files and the gate already runs
twice on every mapped tool call. `SubagentStart` takes no matcher, and the reference accepts a PascalCase event name
in its "VS Code compatible format", so the CLI may deliver the subagent text twice, once from each file. The text is
identical, and this is not measured.

A PascalCase `Stop` in `.claude/settings.json` gets the "VS Code compatible" payload, which the reference lists as
`hook_event_name`, `session_id`, `timestamp` ("ISO 8601 timestamp"), `cwd`, `transcript_path`, `stop_reason` and
`stop_hook_active`. Claude Code's own `Stop` carries `last_assistant_message` and `permission_mode` and neither
`stop_reason` nor `timestamp`. The claude format stays silent only when all three differences agree (`stop_reason`
present, `timestamp` a string, no `last_assistant_message`), because `stop_reason` alone is one field Claude Code
could add in any release, and a payload that matches only partly is checked, which at worst checks a reply twice. The
CLI therefore checks a reply once, from `agentStop`. Its borrowed `SubagentStop` still runs, because Copilot's own
wiring has no `subagentStop` entry. Copilot is not installed where this was written, so this path is verified against
the reference and the unit tests only.

Claude Code and Codex run every matching hook from every configuration layer, so a user-level install from
[GLOBAL_SETUP.md](GLOBAL_SETUP.md) and a project wiring would both block the same reply with the same reason. In the
`claude`, `codex` and `copilot` formats a copy of `no_ai_markers_check.py` whose own resolved path lies outside the
project stays silent when the project already wires the check on the same event. The project is `CLAUDE_PROJECT_DIR` on
Claude Code, otherwise the payload's `cwd` walked up to the nearest directory holding `.git`. The files read are
`.claude/settings.json` and `.claude/settings.local.json` for Claude Code, `.codex/config.toml` and `.codex/hooks.json`
for Codex, every `.github/hooks/*.json` for Copilot, and the event is the payload's `hook_event_name`, or `agentStop`
for a Copilot payload that names none. The same rule keeps a user-level `MessageDisplay` copy silent where the project
wires its own. A copy inside the project always checks. A project directory that cannot be found or a wiring file that
cannot be read leaves the check running, because a double block is better than none.

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
