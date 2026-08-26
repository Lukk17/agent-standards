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

CI is manual-only. There is no automatic build on push or PR. To validate a change:

1. Open the [Actions tab](https://github.com/Lukk17/agent-standards/actions/workflows/ci.yml).
2. Pick the **CI** workflow.
3. Click **Run workflow** against your branch.

Releases are also manual via the [Release](https://github.com/Lukk17/agent-standards/actions/workflows/release.yml)
workflow. Maintainers only. The version string (e.g. `v0.2.0`) goes in the workflow's input field.

---

### Things to watch for in your PR

- **No em-dashes** or en-dashes in human-facing markdown (`README.md`, `AGENTS.md.example`, `docs/*.md`,
  `.agents/skills/**/*.md`). CI lint will flag them. The `markdown-writer` skill explains why.
- **Prose lines under 120 characters** in the same files. Tables, fenced code blocks, badge lines, and
  `<summary>` tags are exempt.
- **Generator output in sync.** If you edit any canonical subagent under `subagents/`, re-run
  `python tools/gen_subagents.py` and commit the regenerated copies under `.claude/agents/`, `.agents/agents/`,
  `.codex/agents/`, and `.github/agents/`. CI runs `--check` and fails on drift.
- **JSON validity** for `.mcp.json`, `opencode.json`, `.vscode/mcp.json`, `.claude/settings.json`, and
  `.github/hooks/preflight.json` if you touch those, and TOML validity for `.codex/config.toml`.
- **Tests for the shared hooks.** If you change [.agents/hooks/preflight_gate.py](.agents/hooks/preflight_gate.py) or
  [.agents/hooks/no_ai_markers_check.py](.agents/hooks/no_ai_markers_check.py), add or update the matching case in
  [tools/tests/](tools/tests/). CI runs the suite.
- **Dependencies declared once.** [tools/pyproject.toml](tools/pyproject.toml) is the only file where a dependency or
  a version is written by hand. [tools/requirements.txt](tools/requirements.txt) beside it is a generated hash-pinned
  lock, so never hand-edit it: recompile it from the `tools` directory with the `uv pip compile` line recorded in its
  own header, and commit both files in the same change.

Install the locked dependencies before running anything below. PowerShell or Unix shell, same command:

```bash
pip install --require-hashes -r tools/requirements.txt
```

Run the markdown linter to catch style issues before pushing:

```bash
python tools/check-markdown.py
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
option below before cloning, otherwise Git writes each link out as a plain text file holding its target path and every
agent that follows the link finds nothing.

```powershell
git config --global core.symlinks true
```

If you already cloned without it, fix the setting and then run the generator, which recreates and repairs the agent
symlinks:

```powershell
python tools/gen_subagents.py
```

---

### Adding a new skill

Drop a folder under `.agents/skills/<name>/` containing a `SKILL.md` with YAML frontmatter
(`name:`, `description:`). The folder name and the `name:` field must match. Pattern-match an existing skill
(e.g. [coding-standards](.agents/skills/coding-standards/SKILL.md)) for shape.

If the skill is human-facing prose, follow the [markdown-writer](.agents/skills/markdown-writer/SKILL.md) rules
(em-dash ban, 120-char wrap, divider per section, link every file/folder mention). If the skill is machine-facing
reference for a tool or stack, the voice rules relax, so just stay consistent with the existing skills in that genre.

Bump the skill-count badge in [README.md](README.md) in the same change. Counts live in the badges and nowhere else,
so that one edit is the whole update.

---

### Adding a new subagent

Add a frontmatter-headed Markdown file under `subagents/<name>.md`. Run `python tools/gen_subagents.py` to emit
per-tool copies in `.claude/agents/`, `.agents/agents/`, `.codex/agents/`, and `.github/agents/`. The same run repairs
the `.opencode/agents` and `.kilo/agents` symlinks, which point at `.agents/agents` rather than holding their own copy.
Commit the canonical source AND the generated outputs, and bump the subagent-count badge in [README.md](README.md).

---

### Changing the preflight wiring

The gate lives in one script and five wiring files. If your change touches how a tool call is judged, or how any agent
reaches the script, the unit tests are not the whole story: run the containerised sandbox in
[sandbox-agent/](sandbox-agent/README.md), which installs all five agent command-line tools, imports this repository
into a throwaway project, and asserts what each agent actually discovers. The specs it runs are documented in
[e2e/README.md](e2e/README.md).

---

### License

By contributing, you agree your changes are licensed under MIT (see [LICENSE](LICENSE)).
