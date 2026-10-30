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

Three jobs run in parallel, and none of them waits on another:

- `actionlint` lints the workflow YAML, including a ShellCheck pass over every `run:` block.
- `validate` runs the JSON and TOML checks, the generator drift check, the markdown linter, the badge-count check, and
  the pytest suite. Every one of those is a command you can run locally, listed further down this page.
- `sandbox` builds the container image once and then runs the containerised suite three times over: the per-project
  import assertions, a global install run twice against the container's own home to prove it is idempotent, and a
  scoped single-agent install to prove it writes only that agent's paths. This is the slow job, several minutes against
  the other two, which is why it runs alongside them rather than behind them.

The scoped check names the individual files the installer writes rather than asserting that `~/.claude` and its
siblings are absent. Asking each agent command-line tool for its version, which the container does on startup, already
creates some of those directories, so their absence would be the wrong thing to measure.

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

The front matter carries `name` and `description` and nothing else, beyond an optional `license` or `compatibility`,
following the open [Agent Skills specification](https://agentskills.io/specification). Write the description in the third person and in trigger form, at about 300 to 400 characters: what the skill covers, then the phrases a user would actually say ("Use when the user says ..."), then one "Not for" pointer naming the skill that owns the nearest neighbouring job. Keep it short, because every skill description in a project shares one listing budget in Claude Code, which "scales at 1% of the model's context window", and once the listing overflows Claude Code drops the descriptions of the skills used least ([Claude Code skills, "Skill descriptions are cut short"](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short)).

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

Add a frontmatter-headed Markdown file under `subagents/<name>.md`. Run `python tools/gen_subagents.py` to emit
per-tool copies in `.claude/agents/`, `.agents/agents/`, `.codex/agents/`, and `.github/agents/`. The same run repairs
the `.opencode/agents` and `.kilo/agents` symlinks, which point at `.agents/agents` rather than holding their own copy.
Commit the canonical source AND the generated outputs, and bump the subagent-count badge in [README.md](README.md)
and the subagent count on [docs/assets/social-card.svg](docs/assets/social-card.svg).

Write the description the way a skill description is written: third person, 300 to 400 characters, opening with "Use when the user ..." and the phrases a user would actually say, then what the agent does, and ending with exactly one "Not for X, use `agent`" pointer naming the agent that owns the nearest neighbouring job. [tools/tests/test_gen_subagents.py](tools/tests/test_gen_subagents.py) checks the opening, the single pointer and the length on every canonical subagent. The version rule for skills applies here unchanged: the major version or versions the agent targets where it matters, and no date, no "current" claim, no real commit hash or digest and no new exact patch-version pin.

List in `skills` only the three to six skills the role uses on every run. Claude Code preloads every listed skill and "the full skill content is injected, not only the description" ([Claude Code subagents, frontmatter fields](https://code.claude.com/docs/en/sub-agents)), so a long list spends the context window before the agent reads any code. Name a stack skill in the body instead, as one to load when the change touches that stack. Never write a skill path into the body: the generator's Preloaded skills section tells the agent to load a skill by name or to read `<name>/SKILL.md` from the skills folder it was installed with, which is `.agents/skills/` in a project and the global skills folder under [docs/GLOBAL_SETUP.md](docs/GLOBAL_SETUP.md). Give the agent every tool its routine needs and no other, and never promise work in the body that needs a tool the `tools` list does not grant. A subagent cannot ask the user mid-run, so it stops and returns the open question to its caller, and it stops and returns the proposed command for anything that changes production, deploys, rolls back, kills, evicts, sends load or attack traffic, or closes or merges a tracker item.

The generator validates before it writes. Every name in the `skills` list needs a folder under `.agents/skills/`,
every name in `tools` has to be one it knows, and a `model` key is rejected outright: a subagent never pins a model,
and no generated file carries one either, so every agent falls back to the user's own subagent default, such as
`CLAUDE_CODE_SUBAGENT_MODEL` on Claude Code, and otherwise to the model the session is on. A
`tools` list of exactly `read`, `grep` and `glob` is read-only on every target, because no target grants a tool the list leaves out, and it also earns `permissionMode: plan` in the Claude Code output.

A read-only agent that needs git keeps `bash` and sets `readonly: true`, optionally with `readonly-commands` naming more command patterns, such as `"gh pr diff*"`. Its shell is then limited to `git diff*`, `git log*`, `git show*`, `git status*` and those extras, and the generator rejects the marker beside `write`, `edit` or `task`. What enforces it differs per target:

| Target | What the generator writes | Enforced by |
| --- | --- | --- |
| Claude Code | `tools` with `Bash`, `permissionMode: plan`, and a "Read-only shell" body section | Rule E of the preflight gate. Plan mode alone is not enough: Claude Code ignores a subagent's `permissionMode` while the session is in auto, `acceptEdits` or `bypassPermissions` mode ([subagents, "Permission modes"](https://code.claude.com/docs/en/sub-agents#permission-modes)), and a `tools` entry such as `Bash(git log *)` does not narrow the tool. Both let a `touch` through on Claude Code 2.1.314 under an auto-mode session |
| OpenCode and Kilo Code | `permission` with `edit: deny` and a `bash` map, `"*": deny` first and each command `allow` after it, because OpenCode evaluates permissions "with the last matching rule winning" ([permissions](https://opencode.ai/docs/permissions/)) | the permission map natively, and Rule E through the plugin |
| Codex | the body section only, because a Codex agent file has no tool or permission field | Rule E alone, wherever the Codex hook payload names the subagent |
| GitHub Copilot | `tools` without `bash` or `powershell`, and the body section telling the agent it has no shell | the missing tool. The `preToolUse` payload names no agent, so the gate cannot hold a Copilot shell to a list, and the agent works from the diff its caller supplies |

`subagents/*.md` is inside the markdown lint scope, so run
`python tools/check-markdown.py` on the new file too. That check also validates the front matter: it has to parse as
YAML, `name` has to match the file stem, `description` has to be a non-empty single-line string of at most 1024
characters, and a description containing a colon followed by a space has to be double-quoted, or GitHub Copilot
refuses to load it.

---

### Placing a skill or a subagent in the plugin map

Every skill and every subagent also lives in exactly one Claude Code plugin, named in [tools/plugins.yaml](tools/plugins.yaml). Add a new one to the map in the same change that adds it, because [tools/tests/test_gen_plugins.py](tools/tests/test_gen_plugins.py) fails on a skill or a subagent that sits in no plugin, or in two. Place it by these rules. The same tests enforce the first four:

1. A subagent goes into the domain plugin whose work it does, and that plugin lists `core` under `dependencies`.
2. A skill the subagent preloads goes into the subagent's own plugin, unless subagents in another plugin preload it too. Then it goes into `core`. `core` holds exactly the skills that subagents in two or more plugins preload, so a change to a `skills` list can move a skill into `core` or back out of it, and the test names the move.
3. A skill no subagent preloads goes into the domain it serves, or into a host group when it administers a machine or a personal tool. A host group carries `category: host` and `defaultEnabled: false`.
4. A new server in [.mcp.json](.mcp.json) gets its own `mcp-<server>` plugin holding only `mcp: <server>`, and joins the `dependencies` of `mcp-all`. A new plugin of any other kind joins the `dependencies` of `all`.
5. Add no plugin for a single subagent with no skill of its own. Put that subagent into the nearest domain instead.

Check the map and render it into a scratch directory outside the repository:

```bash
python -m pytest tools/tests/test_gen_plugins.py
```

```bash
python tools/gen_plugins.py ../plugins-out
```

The rendered tree is never committed on `master`. On every push to `master`, [.github/workflows/plugins.yml](.github/workflows/plugins.yml) renders it, runs `claude plugin validate --strict` on the marketplace and on each plugin, and commits the result to the `plugins` branch.

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
