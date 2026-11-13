# Contributing to agent-standards

Issues and pull requests welcome. For non-trivial changes please open an issue first so we agree on direction before
you spend time writing.

---

### Branching and commits

- Branch from `master`, and name branches `<type>/<short-slug>` (e.g. `feat/add-rust-skill`,
  `fix/markdown-line-width`).
- Use conventional-commit-style messages (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, etc.) with an optional scope.
  Not enforced by CI, but the release workflow uses `--generate-notes` which quotes commit subjects verbatim into
  the public changelog. Write subjects you'd be happy to see on the GitHub Releases page.
- Squash-merge or rebase-merge. Avoid merge commits unless the PR is a long-running feature branch with meaningful
  intermediate state.

---

### Pipeline triggers

CI runs on every pull request and on every push to `master`. The workflow keeps its `workflow_dispatch` trigger too,
so you can still start it by hand from the
[Actions tab](https://github.com/Lukk17/agent-standards/actions/workflows/ci.yml) against any branch.

Four jobs run in parallel, and none of them waits on another:

- `actionlint` lints the workflow YAML, including a ShellCheck pass over every `run:` block.
- `validate` runs the JSON and TOML checks, the generator drift check, the markdown linter, the badge-count check, and
  the pytest suite. Every one of those is a command you can run locally, listed further down this page.
- `sandbox` builds the container image once and then runs the containerised suite three times over: the per-project import assertions, a global install run twice against the container's own home to prove it is idempotent, and a scoped single-agent install to prove it writes only that agent's paths. The per-project run includes the subagent-write section, where each pinned agent binary has a real `python-pro` subagent write a real file and the gate refuse the main thread's own write, against a scripted mock model, as [sandbox-agent/README.md](sandbox-agent/README.md) describes under "A real subagent writes a real file, on every agent". This is the slow job, several minutes against the other two, which is why it runs alongside them rather than behind them.
- `quality-loop` copies each sample project under [tools/tests/quality_samples/](tools/tests/quality_samples/) into a fresh repository with `.metrics/tools`, the way an import delivers it, runs `.metrics/tools/run measure` and `summary` through the launcher of the runner's system, and checks that coverage was read, the planted duplicate was found and exactly the planted mutants survived. It runs Python, TypeScript, Java with Maven and Java with Gradle on Ubuntu, and Python and Java with Gradle on Windows, where mutator's symlinks and the wrapper's Windows commands are measured. Run one sample locally with `python tools/tests/quality_samples/run_sample.py python`.

The scoped check names the individual files the installer writes rather than asserting that `~/.claude` and its
siblings are absent. Asking each agent command-line tool for its version, which the container does on startup, already
creates some of those directories, so their absence would be the wrong thing to measure.

The [Plugins](.github/workflows/plugins.yml) workflow is separate from CI and runs on every pull request and every push to `master`. Its `validate` job installs the pinned Claude Code CLI from npm and runs `claude plugin validate --strict` on the marketplace committed at [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json). `install` serves the repository over smart HTTP with [tools/git_http.py](tools/git_http.py) and runs [tools/tests/test_marketplace_install.py](tools/tests/test_marketplace_install.py) with the same release: one skill plugin installs only that skill, `agent-python-pro` installs one agent file and the skills it preloads, one hook plugin installs only that hook, a bundle installs every plugin it lists, and the `quality-loop` skill carries Robert C. Martin's tools into the cache. Run it locally with `AGENT_STANDARDS_INSTALL_TEST=1` set and the `claude` command line installed. On a push to `master` only, after both, `tag-plan` lists every plugin version that has no `<name>--v<version>` tag yet with [tools/plugin_tags.py](tools/plugin_tags.py), read-only and with no package installed, and `tag` creates those tags at the tested commit and pushes them. The default token reaches that one push step, and no checkout keeps credentials. A newer push to a pull request cancels the older run, while runs on `master` queue, so a tag push is never cut short.

Releases stay manual via the [Release](https://github.com/Lukk17/agent-standards/actions/workflows/release.yml)
workflow. Maintainers only. The version string (e.g. `v0.2.0`) goes in the workflow's input field. That workflow calls
the same CI workflow first, so a release runs the container suite as well.

---

### Things to watch for in your PR

- No em-dashes or en-dashes in human-facing markdown (`README.md`, `AGENTS.md.example`, `docs/*.md`,
  `.agents/skills/**/*.md`, `subagents/*.md`). CI lint will flag them. The `markdown-writer` skill explains why.
- No hard-wrapped prose in new or edited text. A paragraph, list item or table row is one physical line, and the lint has no line-length limit.
- A skill file links only inside its own skill folder, because a consumer can delete any skill it does not use. Name another skill in backticks instead. The same lint run rejects such a link.
- Section headings start at level 3 in the same files. Level 1 is the document title and level 2 is never used. The
  same lint run rejects a level-2 heading.
- Generator output in sync. If you edit any canonical subagent under `subagents/`, re-run
  `python tools/gen_subagents.py` and commit the regenerated copies under `.claude/agents/`, `.agents/agents/`,
  `.codex/agents/`, and `.github/agents/`. CI runs `--check` and fails on drift.
- JSON validity for `.mcp.json`, `opencode.json`, `.vscode/mcp.json`, `.github/mcp.json`, `.claude/settings.json`,
  and `.github/hooks/preflight.json` if you touch those, and TOML validity for `.codex/config.toml`.
- Tests for the shared hooks. If you change any of the four scripts in [.agents/hooks/](.agents/hooks/), add or
  update the matching case in [tools/tests/](tools/tests/). CI runs the suite. Keep every hook standard library only,
  because they run on `-S -E`, and keep `argparse` out of them, because it exits 2 on a usage error and 2 is
  the deny code.
- Dependencies declared once. [tools/pyproject.toml](tools/pyproject.toml) is the only file where a dependency or
  a version is written by hand, and no lock file sits beside it. Every version is an exact pin: the runtime ones
  under `[project.dependencies]`, the test ones in the `dev` dependency group, and the build backend under
  `[build-system]`.
- Instruction files small and no `CLAUDE.md`. `AGENTS.md` and `AGENTS.md.example` stay under 200 lines and 32 KiB,
  any other `AGENTS.md` under 60 lines, and no `CLAUDE.md` is tracked anywhere, because any one of them stops Claude
  Code reading `AGENTS.md` natively. CI runs [tools/check-agents-md.py](tools/check-agents-md.py) and fails on either.

---

### Local checks

These are the checks the `validate` job in CI runs. Run all of them before you push.

Install the pinned dependencies before running anything below. The `--group` flag needs pip 25.1 or newer, so upgrade
first if yours is older. PowerShell or Unix shell, same command:

```bash
python -m pip install --upgrade "pip==26.2.1"
```

Then install the project together with its dev group:

```bash
pip install ./tools --group ./tools/pyproject.toml:dev
```

Run the markdown linter to catch style issues before pushing:

```bash
python tools/check-markdown.py
```

Check that the README badge counts and the counts on the social card still match the tree:

```bash
python tools/check-badges.py
```

Run the hook test suite:

```bash
python -m pytest tools/
```

Confirm the generated subagent trees still match their canonical sources:

```bash
python tools/gen_subagents.py --check
```

Confirm the committed plugin marketplace still matches the plugin map and the items it lists:

```bash
python tools/gen_plugins.py --check
```

Confirm every plugin your branch changed raised its version, against the merge base with `origin/master`, which the next section explains. CI runs it on every pull request:

```bash
python tools/check_versions.py
```

Check that no `CLAUDE.md` is tracked and every `AGENTS.md` is within its size limit:

```bash
python tools/check-agents-md.py
```

Check that every skill a skill file names has a folder under `.agents/skills`:

```bash
python tools/check-skill-mentions.py
```

Check that every JSON configuration and hook file parses:

```bash
python -c "import json; [json.load(open(f)) for f in ['.mcp.json','opencode.json','.vscode/mcp.json','.github/mcp.json','.claude/settings.json','.github/hooks/preflight.json']]"
```

Check that the Codex configuration parses:

```bash
python -c "import tomllib; tomllib.load(open('.codex/config.toml','rb'))"
```

---

### Versioning a plugin

Every skill, subagent, Claude Code hook and MCP server is its own plugin in [.claude-plugin/marketplace.json](.claude-plugin/marketplace.json), and so is every bundle. Claude Code keeps a user on the copy it cached until the plugin's version string changes ([plugin loading, "How Claude Code computes the version"](https://code.claude.com/docs/en/plugins/loading)), so any change to an item must raise its version in the same change: the patch number for a fix, the minor number for new behaviour, the major number for a breaking change. A new item starts at `1.0.0`.

| Item | Where its version lives | What counts as a change |
| --- | --- | --- |
| Skill | `metadata.version` in its `SKILL.md` | any file in its folder, a file reached through a link in it included, such as `quality-loop/tools` |
| Subagent | `version` in `subagents/<name>.md` | the canonical file, its generated `.claude/agents/<name>/` folder, or the skills it preloads |
| Hook | `version` of its entry under `hooks` in [tools/plugins.yaml](tools/plugins.yaml) | any file in its folder under `.agents/hooks/`, or its wiring in [.claude/settings.json](.claude/settings.json) |
| MCP server | `version` of its entry under `servers` in the same map | its block in [.mcp.json](.mcp.json) or its description |
| Bundle | `version` of its entry under `bundles` in the same map | the plugins it lists or its description |

[tools/check_versions.py](tools/check_versions.py) reads the catalog the merge base commits in its marketplace, renders the one on your branch, and fails, naming the plugin, when one changed and its version is not strictly higher, when a version went down, or when a new version's `<name>--v<version>` tag already exists. A base that commits no marketplace counts every plugin as new, and a base marketplace it cannot read fails the check. On every push to `master` the [Plugins](.github/workflows/plugins.yml) workflow tags each plugin version that has no tag yet as `<name>--v<version>`, the tag form Claude Code resolves a dependency range against ([plugin dependencies](https://code.claude.com/docs/en/plugins/dependencies)).

---

### Cloning on Windows

The repo ships symlinks: `.claude/skills` points at `.agents/skills`, and `.opencode/agents` and `.kilo/agents` both
point at `.agents/agents`. Git only creates them when it is allowed to. Turn on Windows Developer Mode and set the
option below, otherwise Git writes each link out as a plain text file holding its target path and every agent that
follows the link finds nothing.

```powershell
git config core.symlinks true
```

That form applies to the repository you run it in. Adding `--global` sets it for every repository on the machine,
including clones you have not made yet, which is the form to use before cloning rather than after.

If you already cloned without it, fix the setting and then run the generator, which recreates and repairs the agent
symlinks:

```powershell
python tools/gen_subagents.py
```

---

### Adding a new skill

Drop a folder under `.agents/skills/<name>/` containing a `SKILL.md`. The folder name and the `name:` field must
match. Pattern-match an existing skill (e.g. [coding-standards](.agents/skills/coding-standards/SKILL.md)) for shape.

The front matter carries `name`, `description` and the skill's plugin version as `metadata.version`, written as a quoted MAJOR.MINOR.PATCH string such as `"1.0.0"`, and nothing else beyond an optional `license` or `compatibility`, following the open [Agent Skills specification](https://agentskills.io/specification), whose `metadata` field is "a map from string keys to string values" for properties the specification does not define. A new skill starts at `1.0.0`, and the markdown linter fails a manifest with no version or one that is not MAJOR.MINOR.PATCH. A `model` key is never allowed, because skills never pin a model and run on the user's default model, and the markdown linter fails a manifest that carries one. Write the description in the third person and in trigger form, at about 300 to 400 characters: what the skill covers, then the phrases a user would actually say ("Use when the user says ..."), then one "Not for" pointer naming the skill that owns the nearest neighbouring job. Keep it short, because every skill description in a project shares one listing budget in Claude Code, which "scales at 1% of the model's context window", and once the listing overflows Claude Code drops the descriptions of the skills used least ([Claude Code skills, "Skill descriptions are cut short"](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short)).

Keep the manifest short and push the depth into a `references/` subdirectory. A `SKILL.md` stays at or under 8,000 characters, front matter included, which is about 2,000 tokens, because it loads in full whenever the skill activates and every subagent that lists the skill preloads it on every run, while a reference file loads only when the agent opens it. The manifest keeps the purpose line, "When to activate" and "When not to activate", each rule in a line or two, the checklist, and a routing table that links each reference file with one line on when to open it. Examples, pass and fail code, long explanations and large tables go to `references/`, one level deep. The markdown linter fails a manifest over the limit and names its size. A reference file over 100 lines opens with a Contents list linking its sections, so an agent can jump to the part it needs instead of reading the whole file. When a topic grows into several near-siblings, make it one hub with a reference file per topic rather than a family of skills competing to match the same phrase.

State a version only where it changes the advice, and then only the major version or versions the content is written for, such as "Spring Boot 4", "Java 25" or "Spring Boot 3 and 4". No "current as of", no date, no "the current release is X", no real commit hash or digest, and no new exact patch-version pin: each one is stale the day after it is written, and an agent reads it as fact.

The advice a skill gives a project is the opposite: pin everything. A third-party GitHub Action goes to a full commit SHA with its version tag in a trailing comment, an image to a tag plus its digest, and a dependency through a lock file. Show those pins as placeholders, such as `uses: actions/checkout@<commit-sha> # v5` and `image: <name>:<version-tag>@sha256:<digest>`, with one line naming the command that resolves the value, such as `git ls-remote https://github.com/actions/checkout refs/tags/v5` or `docker buildx imagetools inspect <image>:<tag>`.

The markdown linter fails on the dated and "current version" forms, on a real 40-character SHA after `@` in a `uses:` line, and on a real 64-character `sha256:` digest, in skill files, subagent sources and the generated agent trees.

If the skill is human-facing prose, follow the [markdown-writer](.agents/skills/markdown-writer/SKILL.md) rules
(em-dash ban, no hard wrap, divider per section, link every file/folder mention). If the skill is machine-facing
reference for a tool or stack, the voice rules relax, so just stay consistent with the existing skills in that genre.

Renaming or deleting a skill is not a local change. Every canonical subagent that lists it has to be updated in the
same commit, because [tools/gen_subagents.py](tools/gen_subagents.py) exits with an error naming any skill that has
no folder, and CI runs it with `--check`.

Bump the skill-count badge in [README.md](README.md) and the skill count on
[docs/assets/social-card.svg](docs/assets/social-card.svg) in the same change. Counts live in those two places and
nowhere else, and [tools/check-badges.py](tools/check-badges.py) fails when either one disagrees with the tree.

---

### Adding a new subagent

Add a frontmatter-headed Markdown file under `subagents/<name>.md`, with a top-level `version: "1.0.0"`, quoted, beside `name` and `description`. The version is the one the agent's marketplace plugin carries, and the generator writes it into no generated agent file. Run `python tools/gen_subagents.py` to emit
per-tool copies in `.claude/agents/<name>/<name>.md`, `.agents/agents/`, `.codex/agents/`, and `.github/agents/`. The same run repairs
the `.opencode/agents` and `.kilo/agents` symlinks, which point at `.agents/agents` rather than holding their own copy.
Commit the canonical source AND the generated outputs, and bump the subagent-count badge in [README.md](README.md)
and the subagent count on [docs/assets/social-card.svg](docs/assets/social-card.svg).

Write the description the way a skill description is written: third person, 300 to 400 characters, opening with "Use when the user ..." and the phrases a user would actually say, then what the agent does, and ending with exactly one "Not for X, use `agent`" pointer naming the agent that owns the nearest neighbouring job. [tools/tests/test_gen_subagents.py](tools/tests/test_gen_subagents.py) checks the opening, the single pointer and the length on every canonical subagent. The version rule for skills applies here unchanged: the major version or versions the agent targets where it matters, and no date, no "current" claim, no real commit hash or digest and no new exact patch-version pin.

List in `skills` only the three to six skills the role uses on every run. Claude Code preloads every listed skill and "the full skill content is injected, not only the description" ([Claude Code subagents, frontmatter fields](https://code.claude.com/docs/en/sub-agents)), so a long list spends the context window before the agent reads any code. Name a stack skill in the body instead, as one to load when the change touches that stack. Never write a skill path into the body: the generator's Preloaded skills section tells the agent to load a skill by name or to read `<name>/SKILL.md` from the skills folder it was installed with, which is `.agents/skills/` in a project and the global skills folder under [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md). Give the agent every tool its routine needs and no other, and never promise work in the body that needs a tool the `tools` list does not grant. A subagent cannot ask the user mid-run, so it stops and returns the open question to its caller, and it stops and returns the proposed command for anything that changes production, deploys, rolls back, kills, evicts, sends load or attack traffic, or closes or merges a tracker item.

The generator validates before it writes. Every name in the `skills` list needs a folder under `.agents/skills/`,
every name in `tools` has to be one it knows, and a `model` key is rejected outright: a subagent never pins a model,
and no generated file carries one either, so every agent falls back to the user's own subagent default, such as
`CLAUDE_CODE_SUBAGENT_MODEL` on Claude Code, and otherwise to the model the session is on. A
`tools` list holding only `read`, `grep` and `glob` is read-only without a marker. Not every target can narrow the tools to that list: Codex has no key that takes `apply_patch` or web search away from a custom agent, and OpenCode and Kilo Code grant whatever their permission map leaves on. So every target gets a "Read-only shell" section with no command in it, which Rule E reads as no shell and no edit wherever the hook names the agent, the Claude Code output earns `permissionMode: plan`, and the OpenCode map denies `edit`, `bash`, `task`, the web, `todowrite`, `lsp` and every MCP tool.

Any agent whose `tools` leave out `bash` gets `features.shell_tool = false` in its Codex file, the one capability a Codex custom agent can switch off besides apps, plugins, memories and the permission request tool ([subagents, "Custom agent file schema"](https://developers.openai.com/codex/subagents)). Measured on Codex 0.167.0 by the free mock case in [sandbox-agent/e2e-mock/subagent-write.sh](sandbox-agent/e2e-mock/subagent-write.sh), such an agent is offered neither `exec_command` nor `write_stdin`. Codex reads such a file from `.codex/agents/` from 0.115.0 on, the first release that discovers that folder (`discover_agent_roles_in_dir` in [agent_roles.rs at rust-v0.115.0](https://raw.githubusercontent.com/openai/codex/rust-v0.115.0/codex-rs/core/src/config/agent_roles.rs)), so an older release never reads the file, and every release from 0.115.0 honours the key: through 0.148.0 the file joins the session as a whole config layer ([role.rs at rust-v0.148.0](https://raw.githubusercontent.com/openai/codex/rust-v0.148.0/codex-rs/core/src/agent/role.rs)), and from 0.149.0 only a `false` on `shell_tool`, `apps`, `plugins`, `memories` or `request_permissions_tool` carries over ([role.rs at rust-v0.149.0](https://raw.githubusercontent.com/openai/codex/rust-v0.149.0/codex-rs/core/src/agent/role.rs)). A `features` key a release does not know never rejects the file: the release logs `unknown feature key in config` and ignores the key ([features.rs at rust-v0.115.0](https://raw.githubusercontent.com/openai/codex/rust-v0.115.0/codex-rs/core/src/features.rs)), and `shell_tool` is a known key in every release that reads the file. On OpenCode and Kilo Code an agent that does not list `webfetch` or `websearch` gets each denied.

A read-only agent that needs git keeps `bash` and sets `readonly: true`, optionally with `readonly-commands` naming more command patterns, such as `"gh pr diff*"`. Its shell is then limited to `git --no-pager diff*`, `git --no-pager log*`, `git --no-pager show*`, `git --no-pager status*` and those extras, and the generator rejects the marker beside `write`, `edit` or `task`. An extra may carry `*` only as its last character and never in its first word, carries no backtick, spells any git command `git --no-pager ...`, and is dropped when the built-in list already holds it. The gate denies git in any other form on every format, because git on a terminal opens a pager whose `!` runs any command, and on Codex it denies such an agent every gh command, because gh has no flag that keeps its pager off, Codex never shows the hook the terminal, and Codex's shell snapshot can restore a `GH_PAGER` the user exports over the `cat` Codex sets. The gate also refuses every character such a command does not need, quotes included, so the agent spells a space in a git format `%x20` and names an upstream branch rather than `@{u}`, and it allows the agent no tool beyond reading, searching, listing and loading a skill, and no shell key such as `workdir` that moves the command ("Hook enforcement" in [docs/agent-compatibility.md](docs/agent-compatibility.md)). What enforces it differs per target:

| Target | What the generator writes | Enforced by |
| --- | --- | --- |
| Claude Code | `tools` with `Bash`, `permissionMode: plan`, and a "Read-only shell" body section | Rule E of the preflight gate. Plan mode alone is not enough: Claude Code ignores a subagent's `permissionMode` while the session is in auto, `acceptEdits` or `bypassPermissions` mode ([subagents, "Permission modes"](https://code.claude.com/docs/en/sub-agents#permission-modes)), and a `tools` entry such as `Bash(git log *)` does not narrow the tool. Both let a `touch` through on Claude Code 2.1.314 under an auto-mode session |
| OpenCode and Kilo Code | `permission` with `edit: deny`, `task: deny`, denies for `webfetch`, `websearch`, `todowrite`, `lsp` and every MCP tool through `"*_*"`, and a `bash` map: `"*": deny` first, each command as an exact rule and a `"command *"` rule, then denies for `*--out*`, `*$*`, `*>*`, gh's `--web`, `-w`, `--jq`, `-q`, `--template`, `-t` and `--watch`, and the characters the gate refuses that a rule can name (`OPENCODE_READ_ONLY_DENIES` in [tools/gen_subagents.py](tools/gen_subagents.py)). OpenCode evaluates permissions "with the last matching rule winning", and its `*` "matches zero or more of any character" ([permissions](https://opencode.ai/docs/permissions/)), so a bare `git diff*` would also allow `git difftool`. A subagent session already gets `task` denied when its definition names no task rule (`tool/task.ts` in OpenCode 1.19.5) | Rule E through the plugin, which is the boundary. The permission map only narrows what reaches it, because a backslash and a `workdir` key cannot be written as a rule there. Kilo Code is assumed to match OpenCode here, not measured |
| Codex | the body section only, because a Codex agent file has no per-tool or permission field, only `features.shell_tool`, which a read-only agent keeps on for its listed commands, and no `sandbox_mode` either: "Other session settings, including `sandbox_mode`, `approval_policy`, `model_provider`, and `mcp_servers`, don't override the parent configuration when placed in a custom agent file" ([subagents, "Custom agents"](https://developers.openai.com/codex/subagents)) | Rule E alone, which finds the definition by the `PreToolUse` payload's `agent_type`. The generated input schema lists `agent_id` and `agent_type` as optional fields at `rust-v0.156.1` ([schema](https://raw.githubusercontent.com/openai/codex/rust-v0.156.1/codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json)) and the [hooks page](https://developers.openai.com/codex/hooks) lists neither for `PreToolUse`, but live run 41348146352 measured both on Codex 0.166.0: a call from inside the read-only `code-reviewer` carried the payload keys `agent_id`, `agent_type`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path` and `turn_id`, with `agent_type` `code-reviewer`. Rule E also denies the agent every gh command here, as above. A payload without the field is allowed. Rule E covers every format whose hook sees the tool, so web search stays open to a read-only agent here, because neither the agent file nor the hook matcher reaches it |
| GitHub Copilot | `tools` without `bash` or `powershell`, and the body section telling the agent it has no shell | the missing tool. The `preToolUse` payload names no agent, so the gate cannot hold a Copilot shell to a list, and the agent works from the diff its caller supplies. The generator maps `webfetch` and `websearch` both to Copilot's `web` alias, which "Allows fetching content from URLs and performing a web search" ([custom agents configuration, "Tool aliases"](https://docs.github.com/en/copilot/reference/custom-agents-configuration)), so listing either grants both there |

`subagents/*.md` is inside the markdown lint scope, so run
`python tools/check-markdown.py` on the new file too. That check also validates the front matter: it has to parse as
YAML, `name` has to match the file stem, `description` has to be a non-empty single-line string of at most 1024
characters, and a description containing a colon followed by a space has to be double-quoted, or GitHub Copilot
refuses to load it.

---

### Placing an item in the plugin marketplace

[.claude-plugin/marketplace.json](.claude-plugin/marketplace.json) lists every skill, every subagent, every Claude Code hook and every MCP server as its own plugin, and groups them in bundles that install other plugins and hold no files. [tools/gen_plugins.py](tools/gen_plugins.py) writes it from [tools/plugins.yaml](tools/plugins.yaml) and the items' own files, so never edit it by hand:

- a skill becomes the plugin named for it, with its folder as the plugin source and its `metadata.version` as the plugin version;
- a subagent becomes `agent-<name>`, with its own folder of the generated Claude Code tree as the source, its canonical `version`, and the skills it preloads as its dependencies;
- a hook the Claude Code wiring in [.claude/settings.json](.claude/settings.json) runs becomes `hook-<name>`, with its folder under [.agents/hooks/](.agents/hooks/) as the source and the same events, matchers, timeouts and arguments, each command running the script from `${CLAUDE_PLUGIN_ROOT}`. Its version and description live in the `hooks` list of the map;
- a server in [.mcp.json](.mcp.json) becomes `mcp-<server>` with the block inline, and its version and description live in the `servers` list of the map.

Every new skill and subagent also joins exactly one bundle in the map, in the same change that adds it, because the generator refuses a map with a skill or a subagent in no bundle or in two. Place it by these rules:

1. A subagent goes into the domain bundle whose work it does, and that bundle lists `core` under `dependencies`.
2. A skill the subagent preloads goes into the subagent's own bundle, unless subagents in another bundle preload it too. Then it goes into `core`. `core` holds exactly the skills that subagents in two or more bundles preload, so a change to a `skills` list can move a skill into `core` or back out of it, and the check names the move.
3. A skill no subagent preloads goes into the domain it serves, or into a host group when it administers a machine or a personal tool. A host group carries `category: host`.
4. A new server gets its own entry in the `servers` list and joins the `dependencies` of `mcp-all`. A new hook the Claude Code wiring runs gets its own entry in the `hooks` list, named for its folder, and joins `hooks-all`. A new domain carries `category: development` and joins the `dependencies` of `all`, which installs `core` and the development domains and never a host group, a server or a hook.
5. Add no bundle for a single subagent with no skill of its own. Put that subagent into the nearest domain instead.

`check_map` in [tools/plugin_map_rules.py](tools/plugin_map_rules.py) enforces the mechanical half of these rules, and [tools/tests/test_gen_plugins.py](tools/tests/test_gen_plugins.py) holds one failing map for each. Which domain a subagent works in, which domain or host group a skill serves, and rule 5 are conventions no test can check, so review them by hand. After a change, regenerate the marketplace and commit it with the change:

```bash
python tools/gen_plugins.py
```

A dependency names a plugin and never a version range, because a range on the dependency of a marketplace entry had no effect when measured on Claude Code 2.1.323. Installing a host group installs and enables every plugin in it: `defaultEnabled: false` on a bundle would switch off only the empty bundle, measured on Claude Code 2.1.323, so no bundle carries it.

---

### Changing the preflight wiring

The gate lives in one shared script, and each agent wires that script to its own hook surface. If your change touches
how a tool call is judged, or how any agent reaches the script, the unit tests are not the whole story. Run the
containerised sandbox in [sandbox-agent/](sandbox-agent/README.md), which installs all five agent command-line tools,
imports this repository into a throwaway project, and asserts what each agent actually discovers. The specs it runs
are documented in [e2e/README.md](e2e/README.md). CI runs the same suite on your pull request, so running it locally
first is about getting the answer sooner, not about whether it gets checked.

---

### License

By contributing, you agree your changes are licensed under MIT (see [LICENSE](LICENSE)).
