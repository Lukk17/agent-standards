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

- The installer lands every shared tree in the container's home directory: one skills tree, five per-agent subagent
  trees, one instruction file with a pointer from each agent, the gate script, and the plugin shim. This is the
  procedure a reader actually follows, run against the mounted repository rather than against GitHub.
- Running it a second time changes nothing and still exits 0. The second run performs the same two operations the
  Updating section of [docs/GLOBAL_SETUP.md](../../docs/GLOBAL_SETUP.md) tells a reader to perform by hand, a
  fast-forward of the shared clone followed by a copy over the top, so an install that is not idempotent would mean
  the documented update is not safe either.
- Every assertion runs from `/work/bare`, a directory that has had nothing imported into it. This is the point of the
  suite. A global install is only proven when the working directory contains none of the per-project files, because
  otherwise there is no way to tell which layer the agent read.
- The gate wiring at user scope names the gate by absolute path. Every shipped wiring calls
  `python .agents/hooks/preflight_gate.py`, a project-relative path that resolves to nothing in a bare directory, so
  the installer rewrites it and this spec asserts that it did.
- The user-scope wiring keeps the shape of the project wiring it stands in for: the same event set per agent, the same
  tool matcher, the same canonical wording, and the same forced zero exit that turns a missing or broken gate back
  into an allow. A global install that drops an event or a zero exit gates less than the project install does, which
  is the exact difference this spec is here to catch.
- Out of scope, because the container is given no provider credentials: this spec starts no agent. Whether each tool
  reports what it found is [7-global-agent-discovery-test.md](7-global-agent-discovery-test.md), and whether the
  global gate copy refuses anything is [9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md).
- Also out of scope for this suite: installing for one agent rather than all five, which the installer supports by
  taking agent names as arguments. Every spec in suite B needs all five installed, so no spec here can end in a
  single-agent home directory. That case is covered instead by
  [verify-global.sh](../../sandbox-agent/verify-global.sh) run with `--scoped <agent>`, which the sandbox job in CI
  runs as its own step.
- Also out of scope, and worth stating because it is a real limitation rather than a gap in the test: the OpenCode
  and Kilo Code plugin resolves the gate script against the project directory it was started in and allows the call
  when the file is missing, by design. The global copy of that plugin is therefore inert in a bare directory. This
  spec asserts the file landed. It does not claim the file does anything there.

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
rm -rf "$HOME/.agent-standards" "$HOME/.agents" "$HOME/.claude" "$HOME/.claude.json" "$HOME/.codex" "$HOME/.config/opencode" "$HOME/.config/kilo" "$HOME/.copilot"
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
substitution that is a property of the container rather than a change to the procedure: it clones the mounted
repository at `/repo` instead of the GitHub address, so the run tests the committed state of this checkout. The
script lives in the sandbox image at `/sandbox/setup-global.sh`, alongside the per-project
[setup-project.sh](../../sandbox-agent/setup-project.sh) it mirrors, and it is baked into the image rather than read
from the mount, so a change to the script itself needs a rebuild before this spec sees it.

Everything the installer copies comes from the clone it makes, so those are committed state.

1. Install for all five agents. Read `echo $?` immediately after this step, before running the next one.

```bash
/sandbox/setup-global.sh
```

2. Install again, unchanged. This is the update path, and the assertions below check that it neither duplicated
   anything nor failed. Read `echo $?` immediately after this step too.

```bash
/sandbox/setup-global.sh
```

3. Move to the bare directory. Every assertion below runs from here.

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

The second install exited 0 as well, which is what makes re-running it safe as the update path.

```bash
echo $?
```

Expect `0`, read straight after run step 2.

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

Claude Code's skills location is a symlink that resolves to a directory.

```bash
test -L "$HOME/.claude/skills" -a -d "$HOME/.claude/skills"
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

OpenCode has every subagent in its own global location.

```bash
test "$(find "$HOME/.config/opencode/agents" -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
```

Expect exit 0.

Kilo Code has every subagent in its own global location, which is a separate directory holding the same format.

```bash
test "$(find "$HOME/.config/kilo/agents" -maxdepth 1 -name '*.md' | wc -l)" -eq "$(find /repo/.agents/agents -maxdepth 1 -name '*.md' | wc -l)"
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
test ! -e "$HOME/.config/opencode/agents/agents" -a ! -e "$HOME/.config/kilo/agents/agents" -a ! -e "$HOME/.claude/agents/agents"
```

Expect exit 0.

There is one shared instruction file.

```bash
test -s "$HOME/.agents/AGENTS.md"
```

Expect exit 0.

Claude Code points at it with an import line rather than a copy, and with exactly one such line after two installs.

```bash
test "$(grep -cxF "@~/.agents/AGENTS.md" "$HOME/.claude/CLAUDE.md")" -eq 1
```

Expect exit 0.

Codex points at it with a symlink that resolves to a file.

```bash
test -L "$HOME/.codex/AGENTS.md" -a -f "$HOME/.codex/AGENTS.md"
```

Expect exit 0.

OpenCode points at it with a symlink that resolves to a file.

```bash
test -L "$HOME/.config/opencode/AGENTS.md" -a -f "$HOME/.config/opencode/AGENTS.md"
```

Expect exit 0.

Copilot points at it with a symlink that resolves to a file.

```bash
test -L "$HOME/.copilot/copilot-instructions.md" -a -f "$HOME/.copilot/copilot-instructions.md"
```

Expect exit 0.

Kilo Code reads no global instruction file, so it points at the shared one through its own config key instead.

```bash
jq -e '[.instructions[]] | any(contains(".agents/AGENTS.md"))' "$HOME/.config/kilo/kilo.jsonc"
```

Expect exit 0.

Kilo Code is told where the shared skills tree is, which is the one line without which it never sees those skills
from the home directory.

```bash
jq -e '[.skills.paths[]] | any(contains(".agents/skills"))' "$HOME/.config/kilo/kilo.jsonc"
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
mean the old standard-error-discarding wrapper had come back. Claude Code is still the one surface whose command
cannot carry a shell redirect, because no redirect token means the same thing in both shells it might pick, which is
exactly why the gate script now silences its own standard error internally for this format instead.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py") and contains("--format claude") and endswith("; exit 0") and (contains("subprocess.DEVNULL") | not))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Claude Code forces a zero exit as well, in the `; exit 0` form both bash and PowerShell parse, because it has one
command field and picks the shell itself.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(endswith("; exit 0"))' "$HOME/.claude/settings.json"
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
jq -e '[.hooks.PreToolUse[].hooks[] | .command, .commandWindows] | length > 0 and all(endswith("|| exit 0"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Codex injects the canonical gate wording on a new prompt and again at the start of a subagent, not a shortened copy of
it. Both events are needed: without `SubagentStart` a subagent under a global Codex gets no injection at all, while the
same subagent inside an imported project does.

```bash
jq -e '[.hooks.UserPromptSubmit[].hooks[].command, .hooks.SubagentStart[].hooks[].command] | length >= 2 and all(contains("Delegate investigation, review and bounded implementation by default."))' "$HOME/.codex/hooks.json"
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

No project-relative gate call survived that rewrite.

```bash
grep -qF "python .agents/hooks/preflight_gate.py" "$HOME/.copilot/hooks/preflight.json"
```

Expect exit 1, meaning the phrase is gone. Exit 0 here is a failure of the test.

The plugin shim landed in both places that load one at startup. It is inert in a bare directory, for the reason given
under What this verifies, so this asserts presence and claims nothing more.

```bash
test -f "$HOME/.config/opencode/plugins/hooks.js" -a -f "$HOME/.config/kilo/plugin/hooks.js"
```

Expect exit 0.

---

### Fixtures

None. The installer writes every configuration file it needs, with the absolute paths taken from the container's own
`$HOME`, so there is nothing to copy in and nothing that hard-codes a home directory.

---

### Concurrency

- Mutates: the container's home directory, specifically `$HOME/.agent-standards`, `$HOME/.agents`, `$HOME/.claude`,
  `$HOME/.codex`, `$HOME/.config/opencode`, `$HOME/.config/kilo`, and `$HOME/.copilot`, plus `/work/bare`. Nothing
  outside the container: `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, because this one deletes and
  rewrites the whole global layer. Nothing at all when every spec gets its own `docker compose run --rm` container.
- Serial: false
