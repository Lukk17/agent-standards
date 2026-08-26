# Global install shape: e2e test

Suite B, global setup. Setup cost class 4: the whole documented global installation into the container's home
directory, plus a second bare directory to assert from.

This spec's Run section is the canonical global install command list for the whole suite.
[7-global-agent-discovery-test.md](7-global-agent-discovery-test.md),
[8-global-mcp-visibility-test.md](8-global-mcp-visibility-test.md), and
[9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md) run it by reference rather than repeating it,
so there is one copy of it to keep correct.

---

### What this verifies

- The installation described in [docs/global-setup.md](../../docs/global-setup.md) lands every shared tree in the
  container's home directory: one skills tree, five per-agent subagent trees, one instruction file with a pointer
  from each agent, the gate script, and the plugin shim.
- Every assertion runs from `/work/bare`, a directory that has had nothing imported into it. This is the point of the
  suite. A global install is only proven when the working directory contains none of the per-project files, because
  otherwise there is no way to tell which layer the agent read.
- The gate wiring at user scope names the gate by absolute path. Every shipped wiring calls
  `python .agents/hooks/preflight_gate.py`, a project-relative path that resolves to nothing in a bare directory, so
  the global copies have to be rewritten and this spec asserts that they were.
- Out of scope, because the container is given no provider credentials: this spec starts no agent. Whether each tool
  reports what it found is [7-global-agent-discovery-test.md](7-global-agent-discovery-test.md), and whether the
  global gate copy refuses anything is [9-global-gate-enforcement-test.md](9-global-gate-enforcement-test.md).
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

Clear every directory the install writes to. In a fresh container none of them exist, so this is what makes the spec
re-runnable in a container that has already run it once.

```bash
rm -rf "$HOME/.agent-standards" "$HOME/.agents" "$HOME/.claude" "$HOME/.codex" "$HOME/.config/opencode" "$HOME/.config/kilo" "$HOME/.copilot"
```

Clear and recreate the bare directory the assertions run from.

```bash
rm -rf /work/bare
```

```bash
mkdir -p /work/bare
```

Let git read the mounted repository, which it refuses by default because the checkout belongs to another user.

```bash
git config --global --add safe.directory /repo
```

---

### Run

The commands below are [docs/global-setup.md](../../docs/global-setup.md) step for step, with two substitutions, both
of which are properties of the container rather than changes to the procedure. The clone source is the mounted
repository instead of the GitHub address, so the run tests the committed state of this checkout. And the clone drops
`--filter=blob:none`, because a partial clone needs the serving side to allow filtering and a local path has nothing
to save anyway.

1. Clone the shared checkout into the home directory.

```bash
git clone --sparse /repo "$HOME/.agent-standards"
```

2. Select the directories, exactly as the document lists them.

```bash
git -C "$HOME/.agent-standards" sparse-checkout set .agents .claude .codex .github .kilo .opencode docs
```

3. Stop the clone pushing anywhere by accident.

```bash
git -C "$HOME/.agent-standards" remote set-url --push origin no_push
```

4. Create the one shared tree every agent reads.

```bash
mkdir -p "$HOME/.agents"
```

5. Copy the canonical content into it: skills, the OpenCode-format subagents, the hooks, and the plugin shim.

```bash
cp -R "$HOME/.agent-standards/.agents/." "$HOME/.agents/"
```

6. Put the machine-wide instruction file where every agent's pointer can reach it.

```bash
cp "$HOME/.agent-standards/AGENTS.md.example" "$HOME/.agents/AGENTS.md"
```

7. Create Claude Code's configuration directory.

```bash
mkdir -p "$HOME/.claude"
```

8. Link Claude Code's skills location at the shared tree. This is the one agent that reads neither `AGENTS.md` nor
   `~/.agents/skills`.

```bash
ln -s "$HOME/.agents/skills" "$HOME/.claude/skills"
```

9. Copy Claude Code's subagents, which are in a format no other agent takes.

```bash
cp -R "$HOME/.agent-standards/.claude/agents" "$HOME/.claude/"
```

10. Point Claude Code at the shared instructions with the single import line.

```bash
cp /repo/e2e/fixtures/global/claude-CLAUDE.md "$HOME/.claude/CLAUDE.md"
```

11. Wire the gate into Claude Code's user settings, with the gate named by absolute path.

```bash
cp /repo/e2e/fixtures/global/claude-settings.json "$HOME/.claude/settings.json"
```

12. Create Codex's configuration directory.

```bash
mkdir -p "$HOME/.codex"
```

13. Copy Codex's TOML subagents.

```bash
cp -R "$HOME/.agent-standards/.codex/agents" "$HOME/.codex/"
```

14. Point Codex at the shared instructions.

```bash
ln -s "$HOME/.agents/AGENTS.md" "$HOME/.codex/AGENTS.md"
```

15. Wire the gate into Codex's user-level hooks file, by absolute path.

```bash
cp /repo/e2e/fixtures/global/codex-hooks.json "$HOME/.codex/hooks.json"
```

16. Create OpenCode's configuration directories.

```bash
mkdir -p "$HOME/.config/opencode/plugins"
```

17. Copy the OpenCode-format subagents into the documented global location.

```bash
cp -R "$HOME/.agents/agents" "$HOME/.config/opencode/agents"
```

18. Install the gate plugin, which loads automatically at startup.

```bash
cp "$HOME/.agents/plugin/hooks.js" "$HOME/.config/opencode/plugins/hooks.js"
```

19. Point OpenCode at the shared instructions.

```bash
ln -s "$HOME/.agents/AGENTS.md" "$HOME/.config/opencode/AGENTS.md"
```

20. Give OpenCode its global configuration, carrying the two servers that are genuinely machine-wide.

```bash
cp /repo/e2e/fixtures/global/opencode.json "$HOME/.config/opencode/opencode.json"
```

21. Create Kilo Code's configuration directories.

```bash
mkdir -p "$HOME/.config/kilo/plugin"
```

22. Copy the same OpenCode-format subagents into Kilo Code's own global location.

```bash
cp -R "$HOME/.agents/agents" "$HOME/.config/kilo/agents"
```

23. Install the same plugin, which Kilo Code accepts unchanged.

```bash
cp "$HOME/.agents/plugin/hooks.js" "$HOME/.config/kilo/plugin/hooks.js"
```

24. Give Kilo Code its global configuration. This is the file that carries `skills.paths`, without which Kilo Code is
    the one agent that never sees the shared skills tree from the home directory.

```bash
cp /repo/e2e/fixtures/global/kilo.jsonc "$HOME/.config/kilo/kilo.jsonc"
```

25. Create GitHub Copilot's configuration directories.

```bash
mkdir -p "$HOME/.copilot/agents" "$HOME/.copilot/hooks"
```

26. Copy Copilot's subagents.

```bash
cp -R "$HOME/.agent-standards/.github/agents/." "$HOME/.copilot/agents/"
```

27. Copy Copilot's hooks file.

```bash
cp "$HOME/.agent-standards/.github/hooks/preflight.json" "$HOME/.copilot/hooks/preflight.json"
```

28. Rewrite the gate call in that copy to an absolute path. Without this step that half of the gate works only in
    projects that ran the per-project import, which is exactly the confusion this suite exists to rule out.

```bash
sed -i "s#python .agents/hooks/preflight_gate.py#python $HOME/.agents/hooks/preflight_gate.py#g" "$HOME/.copilot/hooks/preflight.json"
```

29. Point Copilot at the shared instructions.

```bash
ln -s "$HOME/.agents/AGENTS.md" "$HOME/.copilot/copilot-instructions.md"
```

30. Move to the bare directory. Every assertion below runs from here.

```bash
cd /work/bare
```

---

### Expected

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

There is one shared instruction file.

```bash
test -s "$HOME/.agents/AGENTS.md"
```

Expect exit 0.

Claude Code points at it with an import line rather than a copy.

```bash
grep -qF "@~/.agents/AGENTS.md" "$HOME/.claude/CLAUDE.md"
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

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format claude"))' "$HOME/.claude/settings.json"
```

Expect exit 0.

Codex's user hooks file does the same.

```bash
jq -e '[.hooks.PreToolUse[].hooks[].command] | any(contains("/.agents/hooks/preflight_gate.py --format codex"))' "$HOME/.codex/hooks.json"
```

Expect exit 0.

Copilot's user hooks file does the same, after run step 28 rewrote it.

```bash
jq -e '[.hooks.preToolUse[].command.bash] | any(contains("/.agents/hooks/preflight_gate.py --format copilot"))' "$HOME/.copilot/hooks/preflight.json"
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

- `e2e/fixtures/global/claude-CLAUDE.md`: the single `@~/.agents/AGENTS.md` import line.
- `e2e/fixtures/global/claude-settings.json`: user-scope Claude Code hooks calling the gate at
  `/home/sandbox/.agents/hooks/preflight_gate.py`.
- `e2e/fixtures/global/codex-hooks.json`: user-scope Codex hooks calling the same absolute path.
- `e2e/fixtures/global/opencode.json`: global OpenCode configuration with the two machine-wide servers.
- `e2e/fixtures/global/kilo.jsonc`: global Kilo Code configuration with `skills.paths`, `instructions`, and the same
  two servers.

The global fixtures hard-code the container's home path. They are container inputs, not templates for a real machine.

---

### Concurrency

- Mutates: the container's home directory, specifically `$HOME/.agent-standards`, `$HOME/.agents`, `$HOME/.claude`,
  `$HOME/.codex`, `$HOME/.config/opencode`, `$HOME/.config/kilo`, and `$HOME/.copilot`, plus `/work/bare`. Nothing
  outside the container: `/repo` is mounted read-only and the container is discarded on exit.
- Conflicts with: every other spec in either suite when they share a container shell, because this one deletes and
  rewrites the whole global layer. Nothing at all when every spec gets its own `docker compose run --rm` container.
- Serial: false
