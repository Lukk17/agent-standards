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
- Prose lines under 120 characters in the same files. Tables, fenced code blocks, badge lines, and
  `<summary>` tags are exempt.
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

Check that the README badge counts still match the tree:

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
following the open [Agent Skills specification](https://agentskills.io/specification). Write the description in
trigger form: what the skill covers, then the phrases a user would actually say, then what it is not for and which
skill owns that instead. Keep the manifest short and push the depth into a `references/` subdirectory. When a topic
grows into several near-siblings, make it one hub with a reference file per topic rather than a family of skills
competing to match the same phrase.

If the skill is human-facing prose, follow the [markdown-writer](.agents/skills/markdown-writer/SKILL.md) rules
(em-dash ban, 120-char wrap, divider per section, link every file/folder mention). If the skill is machine-facing
reference for a tool or stack, the voice rules relax, so just stay consistent with the existing skills in that genre.

Renaming or deleting a skill is not a local change. Every canonical subagent that lists it has to be updated in the
same commit, because [tools/gen_subagents.py](tools/gen_subagents.py) exits with an error naming any skill that has
no folder, and CI runs it with `--check`.

Bump the skill-count badge in [README.md](README.md) in the same change. Counts live in the badges and nowhere else,
so that one edit is the whole update.

---

### Adding a new subagent

Add a frontmatter-headed Markdown file under `subagents/<name>.md`. Run `python tools/gen_subagents.py` to emit
per-tool copies in `.claude/agents/`, `.agents/agents/`, `.codex/agents/`, and `.github/agents/`. The same run repairs
the `.opencode/agents` and `.kilo/agents` symlinks, which point at `.agents/agents` rather than holding their own copy.
Commit the canonical source AND the generated outputs, and bump the subagent-count badge in [README.md](README.md).

The generator validates before it writes. Every name in the `skills` list needs a folder under `.agents/skills/`,
every name in `tools` has to be one it knows, and `model` has to be `opus`, `sonnet`, `haiku`, or `inherit`. A
`tools` list of exactly `read`, `grep` and `glob` also earns `permissionMode: plan` in the Claude Code output, which
is how a read-only agent stays read-only. `subagents/*.md` is inside the markdown lint scope, so run
`python tools/check-markdown.py` on the new file too. That check also validates the front matter: it has to parse as
YAML, `name` has to match the file stem, `description` has to be a non-empty single-line string of at most 1024
characters, and a description containing a colon followed by a space has to be double-quoted, or GitHub Copilot
refuses to load it.

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
