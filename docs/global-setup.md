# Global setup

Install the shared agent configuration once into your home directory so every project on the machine gets it, even the
ones that never ran the per-project import.

This is the counterpart to the per-project flow in [README.md](../README.md). The two are additive rather than
exclusive: an agent reads both scopes and merges them, so a project that also ran the per-project import keeps winning
on the paths where both scopes define the same thing.

---

### What this is, and how it differs from the per-project setup

The per-project import drops files into a repository and commits them, so the whole team gets the same setup and the
files travel with the code. A global install writes into your home directory instead. Nothing is committed, nothing is
shared with anyone else, and every project you open on this machine picks it up without being touched.

That difference decides what belongs where.

Belongs globally, because it is the same for you in every repository:

- Skills. A skill such as `python-testing` says nothing about one project, so one copy in the home directory serves
  every project. This is also the part with the biggest payoff, because most of the agents read the same
  `~/.agents/skills` directory.
- Subagents. Same reasoning. A `code-reviewer` definition is not project-specific.
- The preflight gate. The rule "name the skills and subagents that own this task before you start" is a working habit,
  not a project policy, so it is worth having in every session.
- Your personal instruction file, the parts of it that are about how you work rather than about one codebase.

Stays per project, because a global copy would be wrong or actively harmful:

- MCP servers. A connection string, a Grafana URL, or a SonarQube token belongs to one project. Servers that really are
  machine-wide (Context7 and Playwright, for example) are the exception and are fine globally.
- Project instructions. Build commands, module layout, and architecture decisions are the project's, not yours.
- The blocking half of the gate. The shipped hook wiring calls `python .agents/hooks/preflight_gate.py`, a
  project-relative path, and the gate reads the project's subagent definitions to decide. See
  [Limitations](#limitations) for exactly how far the global half gets.

---

### Windows prerequisites

Several of the steps below create a symlink, so on Windows do both of these before you start.

Turn on Developer Mode in Settings, System, For developers. Without it, creating a symlink needs an elevated shell.
Claude Code's own documentation says the same thing about symlinking `CLAUDE.md`
([memory docs](https://code.claude.com/docs/en/memory)).

Tell git to honour symlinks, so the clone in step 1 writes real links rather than text files holding a path.
PowerShell:

```powershell
git config --global core.symlinks true
```

Unix shell:

```bash
git config --global core.symlinks true
```

PowerShell has no `ln`. Use `New-Item -ItemType SymbolicLink`, which is the only command that makes a real symlink.
`New-Item -ItemType Junction` and a shortcut file are not the same thing, and the agents will not follow them.

On Windows, `~` and `$HOME` both resolve to `%USERPROFILE%`, so `~/.claude` means `%USERPROFILE%\.claude`
([Claude Code settings](https://code.claude.com/docs/en/settings)).

---

### Step 1, one shared checkout

Clone this repository once into a working location in your home directory. The clone is the staging area, not the live
configuration: later steps copy or link out of it, and the update section pulls new commits into it.

The clone is sparse and blobless, so only the directories the agents actually need come down. Cone mode also brings
every file in the repository root along, which is how `AGENTS.md.example` arrives.

PowerShell:

```powershell
git clone --filter=blob:none --sparse https://github.com/Lukk17/agent-standards.git $HOME\.agent-standards
```

Unix shell:

```bash
git clone --filter=blob:none --sparse https://github.com/Lukk17/agent-standards.git ~/.agent-standards
```

Select the directories. PowerShell:

```powershell
git -C $HOME\.agent-standards sparse-checkout set .agents .claude .codex .github .kilo .opencode docs
```

Unix shell:

```bash
git -C ~/.agent-standards sparse-checkout set .agents .claude .codex .github .kilo .opencode docs
```

Stop the clone pushing anywhere by accident. PowerShell:

```powershell
git -C $HOME\.agent-standards remote set-url --push origin no_push
```

Unix shell:

```bash
git -C ~/.agent-standards remote set-url --push origin no_push
```

---

### Step 2, the one shared tree every agent reads

Create the shared directory. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.agents
```

Unix shell:

```bash
mkdir -p ~/.agents
```

Copy the canonical content into it. This is `skills/`, the OpenCode-format `agents/` tree, the `hooks/` scripts, and
the `plugin/` shim, all in one move. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.agents\* $HOME\.agents\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.agents/. ~/.agents/
```

After this one step, Codex, OpenCode, and GitHub Copilot already see every skill, with no further wiring. Claude Code
needs a symlink and Kilo Code needs one config line, both covered in their sections below.

Now put your machine-wide instruction file where the agents can find it. `AGENTS.md.example` is written for a project,
so treat it as a starting point and cut the project-specific sections out of the global copy, leaving the parts that
describe how you want to work everywhere. PowerShell:

```powershell
Copy-Item $HOME\.agent-standards\AGENTS.md.example $HOME\.agents\AGENTS.md
```

Unix shell:

```bash
cp ~/.agent-standards/AGENTS.md.example ~/.agents/AGENTS.md
```

Nothing reads `~/.agents/AGENTS.md` on its own. Each per-agent section below points its agent at this one file, so the
text lives in one place instead of five.

---

### Per-agent setup

Every subsection assumes steps 1 and 2 are done. Take only the subsections for the agents you actually run. Adding a
second agent later is nothing more than running its subsection too, because the shared tree is the same files.

#### Claude Code

Claude Code is the one agent that reads neither `AGENTS.md` nor `~/.agents/skills`. Its personal skills location is
`~/.claude/skills/<skill-name>/SKILL.md` ([skills docs](https://code.claude.com/docs/en/skills)), so the shared tree
reaches it through a symlink, exactly as the per-project setup does. Personal subagents live in `~/.claude/agents/`
([sub-agents docs](https://code.claude.com/docs/en/sub-agents)), user hooks and settings in `~/.claude/settings.json`,
and personal instructions in `~/.claude/CLAUDE.md` ([memory docs](https://code.claude.com/docs/en/memory)).

Create the parent directory first, because the symlink command will not make it for you. PowerShell:

```powershell
New-Item -ItemType Directory -Force $HOME\.claude
```

Unix shell:

```bash
mkdir -p ~/.claude
```

Link the skills. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.claude\skills -Target $HOME\.agents\skills
```

Unix shell:

```bash
ln -s ~/.agents/skills ~/.claude/skills
```

The documentation guarantees the symlink is followed for a `<skill-name>` entry inside the skills directory, and says
Claude Code loads a skill once even when the same target is reachable from two locations. Linking the whole `skills`
directory in one go, which is what the command above does and what this repo does at project level, is not spelled out
in the documentation. If it ever stops working, fall back to one symlink per skill directory, which is the documented
shape.

Copy the subagents. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.claude\agents $HOME\.claude\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.claude/agents ~/.claude/
```

Point Claude Code at the shared instructions by adding one import line to `~/.claude/CLAUDE.md`. Imports in a
user-scope memory file load without the external-import approval dialog, because that file is one you wrote yourself.

```text
@~/.agents/AGENTS.md
```

Wire the gate into `~/.claude/settings.json`. Hooks in that file apply to every project on the machine
([hooks docs](https://code.claude.com/docs/en/hooks)). Replace the two absolute paths with your real home directory.
Forward slashes work on Windows too and save you escaping backslashes inside JSON.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, or say none apply and why. Delegate investigation, review and bounded implementation by default."
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|NotebookEdit|Bash",
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "python /home/you/.agents/hooks/preflight_gate.py --format claude"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "timeout": 10,
            "command": "python /home/you/.agents/hooks/no_ai_markers_check.py"
          }
        ]
      }
    ]
  }
}
```

If you already have a `~/.claude/settings.json`, merge the `hooks` block into it rather than overwriting the file.

MCP at user scope is stored in `~/.claude.json`, and the supported way to write it is the CLI rather than hand-editing
([MCP docs](https://code.claude.com/docs/en/mcp)). One server per command, so add only the ones that genuinely are
machine-wide. PowerShell:

```powershell
claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp
```

Unix shell:

```bash
claude mcp add --transport http context7 --scope user https://mcp.context7.com/mcp
```

#### Codex

Codex needs the least work of the five. It scans `$HOME/.agents/skills` for skills natively and follows symlinked
skill folders while scanning ([build skills](https://learn.chatgpt.com/codex/build-skills)), so step 2 finished the
skills job. There is no `~/.codex/skills` in the documentation at all.

Copy the TOML subagents into `~/.codex/agents/`
([subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents)). PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.codex\agents $HOME\.codex\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.codex/agents ~/.codex/
```

Give Codex the shared instructions. It reads `~/.codex/AGENTS.md`
([AGENTS.md docs](https://learn.chatgpt.com/codex/agent-configuration/agents-md)). PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.codex\AGENTS.md -Target $HOME\.agents\AGENTS.md
```

Unix shell:

```bash
ln -s ~/.agents/AGENTS.md ~/.codex/AGENTS.md
```

Wire the gate in `~/.codex/hooks.json`, which is the user-level hooks file
([hooks docs](https://learn.chatgpt.com/codex/hooks)). The same tables can go inline in `~/.codex/config.toml` instead,
and Codex asks you to pick one form per configuration layer rather than using both. Replace the absolute path.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "command": "echo '{\"hookSpecificOutput\": {\"hookEventName\": \"UserPromptSubmit\", \"additionalContext\": \"PREFLIGHT: name the skills and subagents that own this task and invoke them, or say none apply and why.\"}}'"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "statusMessage": "Preflight gate",
            "timeout": 10,
            "command": "python /home/you/.agents/hooks/preflight_gate.py --format codex"
          }
        ]
      }
    ]
  }
}
```

MCP servers go in `[mcp_servers.<name>]` tables in `~/.codex/config.toml`, which is shared by the Codex CLI, the IDE
extension, and the ChatGPT desktop app ([MCP docs](https://learn.chatgpt.com/codex/extend/mcp)). Copy the tables you
want from [MCP_SETUP.md](MCP_SETUP.md).

#### OpenCode

OpenCode reads `~/.agents/skills/<name>/SKILL.md` natively as one of its six skill locations, so step 2 finished that
too ([skills docs](https://opencode.ai/docs/skills/)). It also reads `~/.claude/skills`, which means the Claude Code
symlink from the previous section is a second route to the same files. OpenCode loads a skill from whichever location
it finds it in, so there is nothing to undo.

Copy the OpenCode-format subagents into the documented global location, `~/.config/opencode/agents/`
([agents docs](https://opencode.ai/docs/agents/)). PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agents\agents $HOME\.config\opencode\agents
```

Unix shell:

```bash
cp -R ~/.agents/agents ~/.config/opencode/agents
```

Install the gate plugin. Files in `~/.config/opencode/plugins/` load automatically at startup
([plugins docs](https://opencode.ai/docs/plugins/)). PowerShell:

```powershell
Copy-Item $HOME\.agents\plugin\hooks.js $HOME\.config\opencode\plugins\hooks.js
```

Unix shell:

```bash
cp ~/.agents/plugin/hooks.js ~/.config/opencode/plugins/hooks.js
```

Read the [Limitations](#limitations) section before you rely on this one. The plugin looks for the gate scripts under
the project directory it was started in, so a global copy stays silent in a project that has no `.agents/hooks/`.

Give OpenCode the shared instructions. Its global rules file is `~/.config/opencode/AGENTS.md`
([rules docs](https://opencode.ai/docs/rules/)). PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.config\opencode\AGENTS.md -Target $HOME\.agents\AGENTS.md
```

Unix shell:

```bash
ln -s ~/.agents/AGENTS.md ~/.config/opencode/AGENTS.md
```

MCP servers and any extra `instructions` entries go under the `mcp` and `instructions` keys of
`~/.config/opencode/opencode.json` ([config docs](https://opencode.ai/docs/config/)). Take the `mcp` block from
[MCP_SETUP.md](MCP_SETUP.md) and keep the machine-wide servers only.

#### Kilo Code

Kilo Code is the one agent where the shared skills tree is not automatic. Its documented global skill locations are
`~/.kilo/skills/` and `~/.claude/skills/`, the second only when Claude Code Compatibility is turned on. A
home-directory `~/.agents/skills` is not on that list, and `.agents/skills/` is documented as a project-relative
compatibility directory only ([skills docs](https://kilo.ai/docs/customize/skills)).

The documented way to add it is the `skills.paths` key, which accepts `~/` home-relative paths. Put this in
`~/.config/kilo/kilo.jsonc`:

```jsonc
{
  "skills": {
    "paths": ["~/.agents/skills"]
  }
}
```

Copy the OpenCode-format subagents into `~/.config/kilo/agents/`
([custom subagents](https://kilo.ai/docs/customize/custom-subagents)). PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agents\agents $HOME\.config\kilo\agents
```

Unix shell:

```bash
cp -R ~/.agents/agents ~/.config/kilo/agents
```

Install the same gate plugin. Kilo's global plugin directory is `~/.config/kilo/plugin/`, and it accepts an
OpenCode-format plugin unchanged ([plugins docs](https://kilo.ai/docs/automate/extending/plugins)). PowerShell:

```powershell
Copy-Item $HOME\.agents\plugin\hooks.js $HOME\.config\kilo\plugin\hooks.js
```

Unix shell:

```bash
cp ~/.agents/plugin/hooks.js ~/.config/kilo/plugin/hooks.js
```

Kilo Code reads no global `AGENTS.md`. Global rules come from the `instructions` key of the global config file
([custom rules](https://kilo.ai/docs/customize/custom-rules)), so point that at the shared file. Merge this into the
same `~/.config/kilo/kilo.jsonc`:

```jsonc
{
  "instructions": ["~/.agents/AGENTS.md"],
  "mcp": {}
}
```

MCP servers go under the `mcp` key of that file, in the same shape as `opencode.json`
([CLI docs](https://kilo.ai/docs/code-with-ai/platforms/cli)). `{env:VAR}` does work here. Kilo refuses environment
references in a project config file, and rejects the whole file when it finds one, but the global config is trusted
and expands them normally, in `environment` blocks and in remote `headers` alike. This is the place to put the
Context7 API key header if you want Kilo to use your key rather than the free tier, and an MCP entry has to be a
complete server block, since a partial override fails validation:

```jsonc
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp",
      "headers": { "CONTEXT7_API_KEY": "{env:CONTEXT7_API_KEY}" },
      "enabled": true
    }
  }
}
```

#### GitHub Copilot

Copilot reads `~/.agents/skills` as a personal skills location alongside `~/.copilot/skills`
([about agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)), so step 2 finished the
skills job here too, across the cloud agent, code review, the CLI, the Copilot app, and agent mode in VS Code and
JetBrains.

Everything else on this list is CLI-only. The CLI configuration directory is `~/.copilot`, relocatable with
`COPILOT_HOME`
([CLI config dir reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference)).

Copy the `*.agent.md` subagents into `~/.copilot/agents/`. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.github\agents\* $HOME\.copilot\agents\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.github/agents/. ~/.copilot/agents/
```

Copy the gate into the user-level hooks directory, `~/.copilot/hooks/`
([hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)). PowerShell:

```powershell
Copy-Item $HOME\.agent-standards\.github\hooks\preflight.json $HOME\.copilot\hooks\preflight.json
```

Unix shell:

```bash
cp ~/.agent-standards/.github/hooks/preflight.json ~/.copilot/hooks/preflight.json
```

Then open the copy and change the two `preToolUse` commands from `python .agents/hooks/preflight_gate.py` to the
absolute path of `~/.agents/hooks/preflight_gate.py`, or that half of the gate only works in projects that ran the
per-project import.

Personal instructions live in `~/.copilot/copilot-instructions.md`. Point it at the shared file. PowerShell:

```powershell
New-Item -ItemType SymbolicLink -Path $HOME\.copilot\copilot-instructions.md -Target $HOME\.agents\AGENTS.md
```

Unix shell:

```bash
ln -s ~/.agents/AGENTS.md ~/.copilot/copilot-instructions.md
```

The CLI also honours `COPILOT_CUSTOM_INSTRUCTIONS_DIRS`, a comma-separated list of directories it searches for an
`AGENTS.md`. Setting it to `~/.agents` is the alternative to the symlink above, and it needs no Developer Mode on
Windows.

MCP for the CLI is `~/.copilot/mcp-config.json`. In VS Code, run the `MCP: Open User Configuration` command to open the
`mcp.json` in your user profile folder, which applies across every workspace. The JetBrains plugin is global-only and
GitHub documents the in-IDE user interface rather than the path, so no file is given here. The manual blocks for both
are in [MCP_SETUP.md](MCP_SETUP.md).

---

### Global path map

Every global location this document touches, per agent. Read it next to the project-level equivalent in
[agent-compatibility.md](agent-compatibility.md).

| Agent | Skills | Subagents | Hooks or plugin | MCP config | Global instructions | Config-dir env var |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code | `~/.claude/skills/`, reached by symlink to `~/.agents/skills` | `~/.claude/agents/` | `hooks` in `~/.claude/settings.json` | `~/.claude.json`, written by `claude mcp add --scope user` | `~/.claude/CLAUDE.md`, plus `~/.claude/rules/` | `CLAUDE_CONFIG_DIR` |
| Codex | `$HOME/.agents/skills` native, also `/etc/codex/skills` | `~/.codex/agents/` as TOML | `~/.codex/hooks.json`, or inline `[[hooks.*]]` in `~/.codex/config.toml` | `[mcp_servers.*]` in `~/.codex/config.toml` | `~/.codex/AGENTS.md`, override `~/.codex/AGENTS.override.md` | `CODEX_HOME` |
| OpenCode | `~/.agents/skills/`, `~/.claude/skills/`, `~/.config/opencode/skills/`, all native | `~/.config/opencode/agents/` | `~/.config/opencode/plugins/`, or the `plugin` key in `~/.config/opencode/opencode.json` | `mcp` key in `~/.config/opencode/opencode.json` | `~/.config/opencode/AGENTS.md`, falls back to `~/.claude/CLAUDE.md` | `OPENCODE_CONFIG_DIR`, and `OPENCODE_CONFIG` for the file |
| Kilo Code | `~/.kilo/skills/`, `~/.claude/skills/` behind a compatibility setting, plus anything in `skills.paths` | `~/.config/kilo/agents/` | `~/.config/kilo/plugin/` | `mcp` key in `~/.config/kilo/kilo.jsonc` | none, use `instructions` in `~/.config/kilo/kilo.jsonc` | NOT DOCUMENTED |
| GitHub Copilot | `~/.copilot/skills/` and `~/.agents/skills/`, both native | `~/.copilot/agents/`, CLI only | `~/.copilot/hooks/`, CLI only | `~/.copilot/mcp-config.json` for the CLI, user-profile `mcp.json` for VS Code | `~/.copilot/copilot-instructions.md`, or `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` | `COPILOT_HOME` |

---

### The unification story

Three of the five agents read `~/.agents/skills` straight out of the box: Codex, OpenCode, and every GitHub Copilot
surface that supports skills. For those three, step 2 is the entire skills installation.

Claude Code does not read it. Its only personal skills location is `~/.claude/skills`, so it needs the symlink. That is
the same bridge the per-project setup uses, for the same reason.

Kilo Code does not read it either, at least not from the home directory. It reads `~/.kilo/skills` and, with the
compatibility setting on, `~/.claude/skills`. The documented `.agents/skills` support is project-relative. So Kilo gets
one line of config, `skills.paths`, which the documentation says accepts a `~/` path. If you would rather avoid the
config edit, turning on Claude Code Compatibility makes Kilo read `~/.claude/skills`, which the Claude Code symlink has
already pointed at the shared tree.

What cannot be shared, and why:

- Subagents. There is no shared subagent format. Claude Code takes its own markdown, Codex takes TOML, Copilot takes
  `*.agent.md`, and OpenCode and Kilo take OpenCode-format markdown in two different directories. Every global install
  is therefore a copy into a per-agent directory. OpenCode and Kilo could share one tree through a symlink the way the
  project setup does, but neither documents following a symlinked agents directory, so this document copies instead.
- Hooks. Five different schemas, five different event vocabularies, five different files. The wording is identical
  everywhere, the wiring never is.
- MCP. Five schemas again, and the environment-variable substitution syntax differs in each. That one is a smaller loss
  than it looks, because most servers should not be global anyway.
- Instructions. One file can be shared, and this document shares it, but each agent needs its own pointer at it: an
  `@` import for Claude Code, a symlink for Codex, OpenCode, and the Copilot CLI, and a config key for Kilo Code.

---

### Updating the global installation

Everything above either copies out of `~/.agent-standards` or links into `~/.agents`. Updating means refreshing the
clone, then refreshing only the trees you have not edited yourself.

Fetch and fast-forward the clone. PowerShell:

```powershell
git -C $HOME\.agent-standards pull --ff-only
```

Unix shell:

```bash
git -C ~/.agent-standards pull --ff-only
```

Refresh the shared tree. Both commands copy over the top rather than wiping first, so a skill you wrote yourself under
`~/.agents/skills` survives, while an upstream skill you edited in place is overwritten. If you have local edits worth
keeping, copy them somewhere else before running this. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.agents\* $HOME\.agents\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.agents/. ~/.agents/
```

Refresh Claude Code's subagents. The `skills` symlink needs nothing, because it follows the directory it points at.
PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.claude\agents $HOME\.claude\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.claude/agents ~/.claude/
```

Refresh Codex's subagents. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.codex\agents $HOME\.codex\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.codex/agents ~/.codex/
```

Refresh the Copilot CLI's subagents. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agent-standards\.github\agents\* $HOME\.copilot\agents\
```

Unix shell:

```bash
cp -R ~/.agent-standards/.github/agents/. ~/.copilot/agents/
```

Refresh the OpenCode subagents from the shared tree you just updated, and run the same pair against
`$HOME\.config\kilo\agents` for Kilo Code. PowerShell:

```powershell
Copy-Item -Recurse -Force $HOME\.agents\agents\* $HOME\.config\opencode\agents\
```

Unix shell:

```bash
cp -R ~/.agents/agents/. ~/.config/opencode/agents/
```

Never refreshed by any command above, on purpose, because they become yours the moment you install them:
`~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.claude.json`, `~/.codex/hooks.json`, `~/.codex/config.toml`,
`~/.config/opencode/opencode.json`, `~/.config/kilo/kilo.jsonc`, `~/.copilot/hooks/preflight.json`,
`~/.copilot/mcp-config.json`, and `~/.agents/AGENTS.md`. When upstream changes the gate wording or adds an MCP server,
merge it into those by hand.

A deleted skill is the one case the copy commands get wrong: they bring back anything you removed on purpose. Once you
start curating the set, use the selective approach in [AGENTS-UPDATE.md](AGENTS-UPDATE.md), which enumerates what is
already on disk and refreshes only that.

---

### Limitations

Honest list of what a global install cannot do.

1. The blocking half of the preflight gate is project-shaped. Every shipped hook wiring calls
   `python .agents/hooks/preflight_gate.py`, resolved against the session's working directory. At user level you have
   to rewrite that to an absolute path, which the Claude Code, Codex, and Copilot sections above tell you to do. The
   gate script then looks for subagent definitions in both the current directory and its own grandparent, so a copy at
   `~/.agents/hooks/preflight_gate.py` does find `~/.claude/agents` and `~/.agents/agents`. The text-injection half,
   the `echo` that reminds the model to name its skills, has no file dependency and works globally as it ships.

2. The OpenCode and Kilo Code plugin cannot be fixed the same way. It resolves the gate scripts against the project
   directory it is handed at startup and allows the call when the file is missing, by design, so that a broken gate
   never breaks a session. A global copy of that plugin is therefore a no-op in any project that has not run the
   per-project import. Making it work globally means editing the two path constants at the top of `hooks.js` to
   absolute paths, which this document does not tell you to do, because it writes your home directory into a file the
   update step overwrites.

3. GitHub Copilot's hooks exist only in the CLI and the cloud agent. VS Code, JetBrains, and Copilot code review get no
   hook surface at all, so there is no global gate for them and no project-level one either. They still read
   `~/.agents/skills` and the instruction files, so the advisory half of the gate reaches them as prose.

4. The Copilot cloud agent reads hooks only from `.github/hooks/*.json` in the cloned repository. Nothing in your home
   directory reaches it, by definition, because it runs on GitHub's machines.

5. Claude Code Cowork sessions and cloud sessions do not read `~/.claude/skills` on your machine at all. Cowork loads
   the skills enabled for your claude.ai account, and cloud sessions additionally load project skills from the cloned
   repository. Cowork also skips a `~/.claude/CLAUDE.md` that is itself a symlink, and skips imports in a user-scope
   file that resolve outside the session's working directory, which is exactly what `@~/.agents/AGENTS.md` does. So the
   global install covers your local sessions and not those two.

6. Kilo Code documents no environment variable that relocates its whole configuration directory. `KILO_CONFIG` and
   `KILO_CONFIG_CONTENT` pass configuration content rather than moving the directory. The other four agents all have
   one: `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `OPENCODE_CONFIG_DIR`, and `COPILOT_HOME`.

7. Symlink behaviour is documented for two agents and merely observed for the rest. Claude Code documents that a
   `<skill-name>` entry may be a symlink, and that `.claude/rules/` supports them. Codex documents that it follows
   symlinked skill folders. OpenCode, Kilo Code, and GitHub Copilot document nothing either way, and no agent documents
   following a symlinked subagents directory. Where this document needs a subagent tree in two places it copies rather
   than links.

8. Project settings win. A project that ran the per-project import brings its own `.claude/settings.json`,
   `opencode.json`, `.codex/config.toml`, and skills, and those take precedence over the global ones. That is the
   correct behaviour, and it means the global install is a floor rather than a policy.

---

### Where these paths come from

Every path in this document was taken from the current published documentation, listed here so you can recheck it when
a tool moves something.

| Agent | Pages used |
| --- | --- |
| Claude Code | [settings](https://code.claude.com/docs/en/settings), [skills](https://code.claude.com/docs/en/skills), [sub-agents](https://code.claude.com/docs/en/sub-agents), [memory](https://code.claude.com/docs/en/memory), [hooks](https://code.claude.com/docs/en/hooks), [MCP](https://code.claude.com/docs/en/mcp) |
| Codex | [build skills](https://learn.chatgpt.com/codex/build-skills), [subagents](https://learn.chatgpt.com/codex/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/codex/hooks), [config basics](https://learn.chatgpt.com/codex/config-file/config-basic), [AGENTS.md](https://learn.chatgpt.com/codex/agent-configuration/agents-md), [MCP](https://learn.chatgpt.com/codex/extend/mcp) |
| OpenCode | [config](https://opencode.ai/docs/config/), [skills](https://opencode.ai/docs/skills/), [agents](https://opencode.ai/docs/agents/), [plugins](https://opencode.ai/docs/plugins/), [rules](https://opencode.ai/docs/rules/) |
| Kilo Code | [skills](https://kilo.ai/docs/customize/skills), [custom subagents](https://kilo.ai/docs/customize/custom-subagents), [plugins](https://kilo.ai/docs/automate/extending/plugins), [CLI](https://kilo.ai/docs/code-with-ai/platforms/cli), [custom rules](https://kilo.ai/docs/customize/custom-rules) |
| GitHub Copilot | [CLI config dir](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-config-dir-reference), [agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills), [hooks](https://docs.github.com/en/copilot/reference/hooks-reference), [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) |
