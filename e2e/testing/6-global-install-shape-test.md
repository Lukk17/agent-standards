# Global install shape: e2e test

Suite B, global setup. Setup cost class 4: the whole documented global installation into the container's home
directory, plus a second bare directory to assert from.

The installation is one command, [setup-global.sh](../../sandbox-agent/setup-global.sh), the container's counterpart
of the per-agent procedure [docs/GLOBAL_SETUP.md](../../docs/GLOBAL_SETUP.md) describes a reader following on their
own machine. It lives beside [setup-project.sh](../../sandbox-agent/setup-project.sh) and runs only inside the
container, which is why it is a bash script with no Windows half and why it is not shipped to consumers.

This spec's Reset state and Run sections are the canonical global install for the whole suite.
[7-global-agent-discovery-test.md](7-global-agent-discovery-test.md),
[8-global-mcp-visibility-test.md](8-global-mcp-visibility-test.md), and
[9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md) run them by reference rather than repeating
them, so there is one copy to keep correct.

---

### What this verifies

- The installer follows [docs/GLOBAL_SETUP.md](../../docs/GLOBAL_SETUP.md) step for step. It clones into a temporary
  directory and deletes the clone when it is done, so no copy of the repository stays in the home directory. It fills
  `~/.agents`, the one shared folder, with the skills, the OpenCode-format subagents, the hook scripts and the plugin,
  and records the commit it installed in `~/.agents/.upstream-commit`.
- `~/.claude/CLAUDE.md` is the one instruction file. It starts from `AGENTS.md.example` when none exists. Codex and
  Copilot reach it through a link each, Kilo Code through its `instructions` key, and OpenCode through its own fallback,
  so OpenCode gets no rules file of its own.
- OpenCode and Kilo Code read `~/.agents/agents` through a link each rather than a copy. Claude Code, Codex and Copilot
  keep their own formats in their own directories, because none of the three can read the OpenCode format.
- OpenCode and Kilo Code both name the shared plugin by absolute path, OpenCode as a plain path in `opencode.json` and
  Kilo Code as a `file://` URL in `kilo.jsonc`, and neither holds a copy of it, because a copy in their plugin
  directories would load the runner a second time.
- The Claude Code and Codex user hooks are exactly the blocks the guide prints, with the guide's placeholder home
  directory replaced by the container's own. That includes the `SubagentStart` text that tells a subagent to do its
  delegated task itself.
- Running the install a second time changes nothing and still exits 0, which is what makes adding a second agent later
  safe.
- The update refreshes only what is installed. It restores a damaged hook script, leaves a skill of the user's own
  alone, does not bring back a skill the user deleted, never touches `~/.claude/settings.json`, records the new commit,
  and leaves no clone behind.
- Every assertion runs from `/work/bare`, a directory that has had nothing imported into it. This is the point of the
  suite. A global install is only proven when the working directory contains none of the per-project files, because
  otherwise there is no way to tell which layer the agent read.
- Every hook call at user scope names its script by absolute path. Each shipped wiring calls
  `.agents/hooks/<name>.py`, a project-relative path that resolves to nothing in a bare directory, so the
  installer rewrites it and this spec asserts that it did, for the gate and for the task-list mirror both.
- The user-scope wiring keeps the shape of the project wiring it stands in for: the same event set per agent, the same
  tool matcher, the same canonical wording, the same trimmed interpreter flags, and the same forced zero exit that turns a
  missing or broken hook back into an allow. A global install that drops an event or a zero exit gates less than the
  project install does, which is the exact difference this spec is here to catch.
- One deliberate difference from the project wiring: `markdown_lint_check.py` is copied and never wired. It shells out
  to `tools/check-markdown.py`, which never leaves the upstream repository, so wiring it globally would start an
  interpreter that returns 0 every time. This spec asserts the file landed and that no wiring names it.
- Out of scope, because the container is given no provider credentials: this spec starts no agent. Whether each tool
  reports what it found is [7-global-agent-discovery-test.md](7-global-agent-discovery-test.md), and whether the
  global gate copy refuses anything is [9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md).
- Also out of scope for this suite: installing for one agent rather than all five, which the installer supports by
  taking agent names as arguments. Every spec in suite B needs all five installed, so no spec here can end in a
  single-agent home directory. That case is covered instead by
  [verify-global.sh](../../sandbox-agent/verify-global.sh) run with `--scoped <agent>`, which the sandbox job in CI
  runs as its own step.
- Also out of scope: what the OpenCode and Kilo Code plugin does at runtime. It prefers the project's own
  `.agents/hooks/` and falls back to the `~/.agents/hooks/` this installer fills, unless the project holds the
  `.agents/no-global-hooks` opt-out, so in a bare directory it runs the home copies. No agent is started here, so
  this spec asserts the plugin file and the hook scripts landed and leaves the fallback to the plugin's unit tests.

---

### Prerequisites

Check that Docker answers on the host. PowerShell:

```powershell
docker compose version
```

Unix shell:

```bash
docker compose version
```

Expect exit 0.

Check the sandbox image exists. PowerShell:

```powershell
docker image inspect agent-standards-sandbox:local
```

Unix shell:

```bash
docker image inspect agent-standards-sandbox:local
```

Expect exit 0.

Record the commit under test, because the global install clones committed state only. PowerShell:

```powershell
git rev-parse --short HEAD
```

Unix shell:

```bash
git rev-parse --short HEAD
```

Expect exit 0. Copy the short hash into the run record.

---

### Reset state

Move into the sandbox directory, which is where Compose finds its `compose.yaml`. The same line works in
PowerShell and in a Unix shell.

```bash
cd sandbox-agent
```

Start the container shell. Everything after this block is typed into that shell. PowerShell:

```powershell
docker compose run --rm sandbox /bin/bash
```

Unix shell:

```bash
docker compose run --rm sandbox /bin/bash
```

Clear every directory the install writes to, plus `~/.claude.json`, which is not written by the install but by the
`claude mcp add` in [8-global-mcp-visibility-test.md](8-global-mcp-visibility-test.md). In a fresh container none of
them exist, so this is what makes the spec, and every spec that inherits this reset, re-runnable in a container that
has already run it once.

```bash
rm -rf "$HOME/.agents" "$HOME/.claude" "$HOME/.claude.json" "$HOME/.codex" "$HOME/.config/opencode" "$HOME/.config/kilo" "$HOME/.copilot"
```

Clear and recreate the bare directory the assertions run from.

```bash
rm -rf /work/bare
```

```bash
mkdir -p /work/bare
```

Let git read the mounted repository, which it refuses by default because the checkout belongs to another user. Two
entries are needed: git checks the working tree it discovered and the repository directory it resolved, and a clone
whose source is a path is keyed on that path's `.git` directory.

```bash
git config --global --add safe.directory /repo
```

```bash
git config --global --add safe.directory /repo/.git
```

---

### Run

The installer performs the same steps [docs/GLOBAL_SETUP.md](../../docs/GLOBAL_SETUP.md) describes, with one
substitution that is a property of the container rather than a change to the procedure: its temporary clone is made
from the mounted repository at `/repo` instead of the GitHub address, so the run tests the committed state of this
checkout. With `--update` it performs the guide's Updating section instead. The script lives in the sandbox image at
`/sandbox/setup-global.sh`, alongside the per-project [setup-project.sh](../../sandbox-agent/setup-project.sh) it
mirrors, and it is baked into the image rather than read from the mount, so a change to the script itself needs a
rebuild before this spec sees it.

Everything the installer copies comes from the clone it makes, so those are committed state.

1. Install for all five agents. Read `echo $?` immediately after this step, before running the next one.

```bash
/sandbox/setup-global.sh
```

2. Install again, unchanged, the way a reader adds a second agent later. The assertions below check that it neither
   duplicated anything nor failed. Read `echo $?` immediately after this step too.

```bash
/sandbox/setup-global.sh
```

3. Prepare the update. Delete one installed skill, the way a reader drops one they do not want.

```bash
rm -rf "$HOME/.agents/skills/markdown-writer"
```

4. Add a skill of your own, which no upstream skill shares a name with.

```bash
mkdir -p "$HOME/.agents/skills/e2e-own-skill" && printf -- '---\nname: e2e-own-skill\ndescription: Own skill.\n---\n' > "$HOME/.agents/skills/e2e-own-skill/SKILL.md"
```

5. Damage an installed hook script, so the update has something to restore.

```bash
printf '\n# damaged\n' >> "$HOME/.agents/hooks/preflight_gate.py"
```

6. Record the digest of the Claude Code settings, which the update must not touch.

```bash
sha256sum "$HOME/.claude/settings.json" > /tmp/global-settings-before.txt
```

7. Run the update. Read `echo $?` immediately after this step.

```bash
/sandbox/setup-global.sh --update
```

8. Record which skills the update left, before the next step puts the deleted one back.

```bash
ls "$HOME/.agents/skills" > /tmp/global-update-skills.txt
```

9. Put the deleted skill back the way the guide adds one, by copying its folder, and remove your own skill again, so
   every later spec sees the full canonical set.

```bash
cp -R /repo/.agents/skills/markdown-writer "$HOME/.agents/skills/markdown-writer" && rm -rf "$HOME/.agents/skills/e2e-own-skill"
```

10. Move to the bare directory. Every assertion below runs from here.

```bash
cd /work/bare
```

---

### Expected

The first install exited 0.

```bash
echo $?
```

Expect `0`, read straight after run step 1.

The second install exited 0 as well, which is what makes running a section again safe.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

The update exited 0.

```bash
echo $?
```

Expect `0`, read straight after run step 7.

No temporary clone outlived the install or the update, and no permanent copy of the repository sits in the home
directory.

```bash
test -z "$(find "${TMPDIR:-/tmp}" -mindepth 2 -maxdepth 2 -name agent-standards)" -a ! -e "$HOME/.agent-standards"
```

Expect exit 0.

The shared folder records the commit the update refreshed from, which is the one under test.

```bash
test "$(cat "$HOME/.agents/.upstream-commit")" = "$(git -C /repo rev-parse HEAD)"
```

Expect exit 0.

The update restored the damaged hook script to the committed file.

```bash
git -C /repo show HEAD:.agents/hooks/preflight_gate.py | cmp - "$HOME/.agents/hooks/preflight_gate.py"
```

Expect exit 0.

The update did not bring back the skill you deleted.

```bash
grep -qx markdown-writer /tmp/global-update-skills.txt
```

Expect exit 1, meaning the name is absent. Exit 0 here is a failure of the test.

The update left your own skill alone.

```bash
grep -qx e2e-own-skill /tmp/global-update-skills.txt
```

Expect exit 0.

The update did not touch `~/.claude/settings.json`, which holds settings of your own.

```bash
sha256sum -c /tmp/global-settings-before.txt
```

Expect exit 0.

The working directory holds none of the per-project files. If any of them were here, no later assertion in this suite
could tell which layer an agent read.

```bash
ls -A /work/bare | grep -E "^(\.agents|\.claude|\.codex|\.github|\.kilo|\.opencode|\.vscode|\.mcp\.json|opencode\.json|AGENTS\.md)$"
```

Expect exit 1, meaning `grep` matched nothing. Exit 0 here is a failure of the test.

The shared skills tree holds every canonical skill, counted against the mounted repository rather than a number
written into this spec.

```bash
test "$(find "$HOME/.agents/skills" -mindepth 1 -maxdepth 1 -type d | wc -l)" -eq "$(find /repo/.agents/skills -mindepth 1 -maxdepth 1 -type d | wc -l)"
```

Expect exit 0.

Claude Code's skills location is a link to the shared skills.

```bash
test "$(readlink "$HOME/.claude/skills")" = "$HOME/.agents/skills"
```

Expect exit 0.

The same number of skills is reachable through that symlink.

```bash
test "$(find -L "$HOME/.claude/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)" -eq "$(find /repo/.agents/skills -mindepth 2 -maxdepth 2 -name SKILL.md | wc -l)"
```

Expect exit 0.

The gate script landed in the shared tree, which every user-scope wiring below names by absolute path.

```bash
test -f "$HOME/.agents/hooks/preflight_gate.py"
```

Expect exit 0.

The other three hook scripts landed beside it. The markdown lint is on this list because the copy is one directory
rather than a file list, and the assertions further down are what say it stays unwired.

```bash
test -f "$HOME/.agents/hooks/no_ai_markers_check.py" -a -f "$HOME/.agents/hooks/task_list_sync.py" -a -f "$HOME/.agents/hooks/markdown_lint_check.py"
```

Expect exit 0.

Claude Code has every subagent in its own markdown format.

```bash
test "$(find "$HOME/.claude/agents" -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

Codex has every subagent in TOML.

```bash
test "$(find "$HOME/.codex/agents" -maxdepth 1 -name '*.toml' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

OpenCode and Kilo Code read their subagents through a link each to the shared tree, not a copy.

```bash
test "$(readlink "$HOME/.config/opencode/agents")" = "$HOME/.agents/agents" -a "$(readlink "$HOME/.config/kilo/agents")" = "$HOME/.agents/agents"
```

Expect exit 0.

The shared tree holds every subagent, and both links reach them. The trailing slash makes `find` follow the link.

```bash
test "$(find "$HOME/.config/opencode/agents/" -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)" -a "$(find "$HOME/.config/kilo/agents/" -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

GitHub Copilot has every subagent as `*.agent.md`.

```bash
test "$(find "$HOME/.copilot/agents" -maxdepth 1 -name '*.agent.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

The second install nested no tree inside the one the first install made. Copying a directory onto an existing
directory of the same name is the classic way an install stops being repeatable, and it would leave the agent tree one
level deeper than any agent looks.

```bash
test ! -e "$HOME/.agents/agents/agents" -a ! -e "$HOME/.agents/skills/skills" -a ! -e "$HOME/.claude/agents/agents"
```

Expect exit 0.

There is one instruction file, `~/.claude/CLAUDE.md`, and it started from the template because none existed. The
shared folder holds none of its own.

```bash
git -C /repo show HEAD:AGENTS.md.example | cmp - "$HOME/.claude/CLAUDE.md" && test ! -e "$HOME/.agents/AGENTS.md"
```

Expect exit 0.

Codex and Copilot point at it with a link each.

```bash
test "$(readlink "$HOME/.codex/AGENTS.md")" = "$HOME/.claude/CLAUDE.md" -a "$(readlink "$HOME/.copilot/copilot-instructions.md")" = "$HOME/.claude/CLAUDE.md"
```

Expect exit 0.

OpenCode gets no global rules file, so it falls back to `~/.claude/CLAUDE.md` on its own.

```bash
test ! -e "$HOME/.config/opencode/AGENTS.md"
```

Expect exit 0.

Kilo Code reads no global instruction file, so it points at the one file through its `instructions` key, by absolute
path.

```bash
jq -e --arg f "$HOME/.claude/CLAUDE.md" '.instructions == [$f]' "$HOME/.config/kilo/kilo.jsonc"
```

Expect exit 0.

Kilo Code carries no `skills.paths` entry, because it reads `~/.agents/skills` natively.

```bash
jq -e 'has("skills") | not' "$HOME/.config/kilo/kilo.jsonc"
```

Expect exit 0.

The Claude Code user settings are exactly the guide's block, with its placeholder home directory read as the
container's own, so the `SubagentStart` text and every other entry match what a reader pastes.

```bash
python3 -c 'import json,os,re,sys;h=os.environ["HOME"];g=open("/repo/docs/GLOBAL_SETUP.md").read();b=[x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if "MessageDisplay" in x][0];sys.exit(json.loads(b.replace("/home/you/",h+"/"))!=json.load(open(h+"/.claude/settings.json")))'
```

Expect exit 0.

The Codex user hooks are the guide's block in the same way.

```bash
python3 -c 'import json,os,re,sys;h=os.environ["HOME"];g=open("/repo/docs/GLOBAL_SETUP.md").read();b=[x for x in re.findall(r"^\x60{3}json\n(.*?)^\x60{3}$",g,re.M|re.S) if "commandWindows" in x][0];sys.exit(json.loads(b.replace("/home/you/",h+"/"))!=json.load(open(h+"/.codex/hooks.json")))'
```

Expect exit 0.

Claude Code's user settings call the gate by absolute path, not by the project-relative path the shipped wiring uses.
The command runs the gate script directly, with no wrapper in between, so the format flag shows up as a plain
` --format claude` substring in the command string.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py") and contains("--format claude"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code's gate call runs the script directly here too, and it must carry no `subprocess.DEVNULL`, which would
mean the old standard-error-discarding wrapper had come back. The gate script silences its own standard error for
this format, so the command needs no redirect.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py") and contains("--format claude") and endswith("; exit 0") and (contains("subprocess.DEVNULL") | not))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code forces a zero exit as well, with a trailing `; exit 0`. The command is POSIX shell, which Claude Code runs
under `sh -c`, or under Git Bash on Windows.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(endswith("; exit 0"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code's matcher covers the two web tools as well as the six that can write, `PowerShell` among them, because
the gate hands research to a subagent rather than letting the main thread fetch or search directly, and because Claude
Code on Windows routes shell commands through its PowerShell tool whenever that tool is on.

```bash
jq -e '[.hooks.PreToolUse[].matcher] | any(type == "string" and test("Edit") and test("Write") and test("MultiEdit") and test("NotebookEdit") and test("Bash") and test("PowerShell") and test("WebFetch") and test("WebSearch"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code wires every event the project wiring wires, apart from the `PostToolUse` the markdown lint sits on. An
event missing here is an event the global install does not gate.

```bash
jq -e '[.hooks | keys[]] == ["MessageDisplay", "PreCompact", "PreToolUse", "SessionStart", "Stop", "SubagentStart", "SubagentStop", "TaskCompleted", "TaskCreated", "UserPromptSubmit"]' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code tells a subagent to do its delegated task itself and never hands it the main-thread reminder, which tells
its reader to delegate.

```bash
jq -e '[.hooks.SubagentStart[].hooks[].command] | length > 0 and all(contains("PREFLIGHT for a subagent:") and (contains("Delegate investigation") | not))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code injects the subagent supervision text at session start, beside the gate text.

```bash
jq -e '[.hooks.SessionStart[].hooks[].command] | any(contains("When you launch a background subagent") and contains("every 10 minutes"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

No wiring names the markdown lint, for the reason given under What this verifies.

```bash
jq -e '[.hooks[][].hooks[].command] | any(contains("markdown_lint_check.py")) | not' "$HOME/.claude/settings.json"
```

Expect exit 0.

The reply formatting check runs on both stop events, once each, by absolute path.

```bash
jq -e '[[.hooks.Stop[].hooks[].command], [.hooks.SubagentStop[].hooks[].command] | map(select(contains("/.agents/hooks/no_ai_markers_check.py --format claude")))] | all(length == 1)' "$HOME/.claude/settings.json"
```

Expect exit 0.

`MessageDisplay` fixes the reply before it is shown, and the `Stop` check runs with `--display-fixed` so it judges
only what that fix leaves.

```bash
jq -e '([.hooks.Stop[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format claude --display-fixed"))) and ([.hooks.MessageDisplay[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format claude --display ")))' "$HOME/.claude/settings.json"
```

Expect exit 0.

The task-list mirror runs on the five events that carry it, each with its own `--event` value, so a compaction cannot
lose the list and a finished turn cannot leave items open with nothing to show for them.

```bash
jq -e '[.hooks.SessionStart[].hooks[].command, .hooks.PreCompact[].hooks[].command, .hooks.TaskCreated[].hooks[].command, .hooks.TaskCompleted[].hooks[].command, .hooks.Stop[].hooks[].command | select(contains("/.agents/hooks/task_list_sync.py")) | capture("--event (?<event>[a-z]+)").event] | sort == ["precompact", "sessionstart", "stop", "taskcompleted", "taskcreated"]' "$HOME/.claude/settings.json"
```

Expect exit 0.

Every Claude Code hook resolves its own interpreter the same way the project wiring does, `python3` first and
`python` second, then runs it on `-S -E`. Those flags skip site initialisation and ignore the `PYTHON*` environment
variables, which is safe because every hook is standard library only, and they take a slice off an interpreter start
the gate pays on every single tool call.

```bash
jq -e '[.hooks[][].hooks[].command | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Codex's user hooks file names the gate by absolute path too, and there the flag is part of the command string.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format codex"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex scopes the gate to the tools that can write, rather than firing it on every tool call.

```bash
jq -e '[.hooks.PreToolUse[].matcher] | any(type == "string" and test("Bash") and test("apply_patch"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex forces a zero exit on the gate call, on the POSIX command and on its Windows sibling both. The codex format
denies with exit 0 and JSON on stdout and never uses a non-zero exit, so a bare invocation whose script is missing
would deny every tool call instead of allowing it.

```bash
jq -e '[.hooks.PreToolUse[].hooks[] | .command] | length > 0 and all(endswith("|| exit 0"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

The Windows siblings run in PowerShell, where `||` after a command is a parse error, so every one of them ends in
`; exit 0` instead.

```bash
jq -e '[.hooks[][].hooks[] | (.commandWindows // empty)] | length > 0 and all(endswith("; exit 0"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex injects the canonical gate wording on a new prompt, not a shortened copy of it, and the subagent text at the
start of a subagent, because the gate wording tells its reader to delegate and a subagent told that turns its own task
away.

```bash
jq -e '[.hooks.UserPromptSubmit[].hooks[].command] | length >= 1 and all(contains("Delegate investigation, review and bounded implementation by default."))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

```bash
jq -e '[.hooks.SubagentStart[].hooks[].command] | length > 0 and all(contains("PREFLIGHT for a subagent:") and (contains("Delegate investigation") | not))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex wires the same five events its project configuration wires. `SessionStart` and `Stop` are the two that a
gate-only global install used to drop.

```bash
jq -e '[.hooks | keys[]] == ["PreToolUse", "SessionStart", "Stop", "SubagentStart", "UserPromptSubmit"]' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex checks the reply formatting on `Stop`, by absolute path.

```bash
jq -e '[.hooks.Stop[].hooks[].command] | any(contains("/.agents/hooks/no_ai_markers_check.py --format codex"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex puts the task list back at the start of a session, by absolute path. `SessionStart` is also what carries the
list through a compaction, because it fires again with `source` set to `compact`.

```bash
jq -e '[.hooks.SessionStart[].hooks[].command] | any(contains("/.agents/hooks/task_list_sync.py --event sessionstart --format codex"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Every Codex POSIX command resolves the interpreter the same way the project wiring does, and still names the script
by absolute path.

```bash
jq -e '[.hooks[][].hooks[] | (.command // empty) | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Its Windows sibling moves to the project root in PowerShell first and then stays on `python`, which is the only
name the python.org installer puts on the path, so this spec asserts the asymmetry rather than assuming it.

```bash
jq -e '[.hooks[][].hooks[] | (.commandWindows // empty) | select(contains(".py"))] | length > 0 and all(startswith("$root = git rev-parse --show-toplevel 2>$null; if ($root) { Set-Location -LiteralPath $root }; python -S -E /"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Every Codex command has a Windows sibling, because Codex picks one of the two per platform and a command with no
sibling is simply absent on the other.

```bash
jq -e '[.hooks[][].hooks[] | select(has("command"))] | length > 0 and all(has("commandWindows"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Copilot's user hooks file does the same, from the shipped project wiring the installer rewrote.

```bash
jq -e '[.hooks.preToolUse[].bash] | any(contains("/.agents/hooks/preflight_gate.py --format copilot"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

Copilot puts the task list back on `sessionStart`, by absolute path, which is the second call the installer has to
rewrite in that file.

```bash
jq -e '[.hooks.sessionStart[].bash] | any(contains("/.agents/hooks/task_list_sync.py --event sessionstart --format copilot"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

Copilot appends the reminder to every prompt on `userPromptTransformed`, by absolute path, which is the third call the
installer has to rewrite in that file.

```bash
jq -e '[.hooks.userPromptTransformed[].bash] | any(contains("/.agents/hooks/copilot/prompt_reminder.py"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

Copilot checks the reply formatting on `agentStop`, by absolute path, which is the fourth call the installer has to
rewrite in that file.

```bash
jq -e '[.hooks.agentStop[].bash] | any(contains("/.agents/hooks/no_ai_markers_check.py --format copilot"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

Every Copilot bash command resolves the interpreter the same way the project wiring does, and still names the
script by absolute path.

```bash
jq -e '[.hooks[][] | (.bash // empty) | select(contains(".py"))] | length > 0 and all(contains("PY=$(command -v python3 || command -v python)") and contains("\"$PY\" -S -E /"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

Its PowerShell sibling stays on `python`, which is the only name the python.org installer puts on the path, so this
spec asserts the asymmetry rather than assuming it.

```bash
jq -e '[.hooks[][] | (.powershell // empty) | select(contains(".py"))] | length > 0 and all(startswith("python -S -E /"))' "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 0.

No project-relative hook call survived that rewrite. The needle carries the space before the leading dot, because an
absolute path ends in the same `.agents/hooks/` the relative one starts with and a bare substring would match both.

```bash
grep -qF -- "-E .agents/hooks/" "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 1, meaning the phrase is gone. Exit 0 here is a failure of the test.

The plugin sits once, in the shared folder, and OpenCode names it by absolute path. Its fallback to the home hooks is
runtime behaviour, for the reason given under What this verifies, so this asserts the wiring and claims nothing more.

```bash
jq -e --arg p "$HOME/.agents/plugin/hooks.js" '.plugin == [$p]' "$HOME/.config/opencode/opencode.json"
```

Expect exit 0.

Kilo Code names the same file as an absolute `file://` URL.

```bash
jq -e --arg p "file://$HOME/.agents/plugin/hooks.js" '.plugin == [$p]' "$HOME/.config/kilo/kilo.jsonc"
```

Expect exit 0.

Neither holds a copy of the plugin in its own plugin directory, which it would load at startup as a second runner.

```bash
test -f "$HOME/.agents/plugin/hooks.js" -a ! -e "$HOME/.config/opencode/plugins" -a ! -e "$HOME/.config/kilo/plugin"
```

Expect exit 0.

---

### Fixtures

None. The installer writes every configuration file it needs, with the absolute paths taken from the container's own
`$HOME`, so there is nothing to copy in and nothing that hard-codes a home directory. The expected Claude Code and
Codex wiring is read out of [docs/GLOBAL_SETUP.md](../../docs/GLOBAL_SETUP.md) itself, so the guide and this spec
cannot drift apart.

---

### Concurrency

- Mutates: the container's home directory, specifically `$HOME/.agents`, `$HOME/.claude`, `$HOME/.codex`,
  `$HOME/.config/opencode`, `$HOME/.config/kilo`, and `$HOME/.copilot`, plus `/work/bare`, the temporary clone the
  installer makes and deletes under `$TMPDIR`, and the `/tmp/global-*` records the update steps write. Nothing outside
  the container: `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, because this one deletes and
  rewrites the whole global layer. Nothing at all when every spec gets its own `docker compose run --rm` container.
- Serial: false
