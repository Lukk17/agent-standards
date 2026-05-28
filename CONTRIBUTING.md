# Contributing to agent-standards

Issues and pull requests welcome. For non-trivial changes please open an issue first so we agree on direction before
you spend time writing.

---

### Branching and commits

- Branch from `master`; name branches `<type>/<short-slug>` (e.g. `feat/add-rust-skill`, `fix/markdown-line-width`).
- Use conventional-commit-style messages (`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, etc.) with an optional scope.
  Not enforced by CI, but the release workflow uses `--generate-notes` which quotes commit subjects verbatim into
  the public changelog. Write subjects you'd be happy to see on the GitHub Releases page.
- Squash-merge or rebase-merge; avoid merge commits unless the PR is a long-running feature branch with meaningful
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

- **No em-dashes** or en-dashes in human-facing markdown (`README.md`, `AGENTS.md.example`, `docs/*.md`).
  CI lint will flag them. The `markdown-writer` skill explains why.
- **Prose lines under 120 characters** in the same files. Tables, fenced code blocks, badge lines, and
  `<summary>` tags are exempt.
- **Generator output in sync.** If you edit any canonical subagent under `subagents/`, re-run
  `python tools/gen_subagents.py` and commit the regenerated copies under `.claude/agents/` and `.opencode/agents/`.
  CI runs `--check` and fails on drift.
- **JSON validity** for `.mcp.json.example` and `opencode.json.example` if you touch those.
- **Run the markdown linter locally** to catch issues before pushing:

```bash
python tools/check-markdown.py
```

---

### Adding a new skill

Drop a folder under `.agents/skills/<name>/` containing a `SKILL.md` with YAML frontmatter
(`name:`, `description:`). The folder name and the `name:` field must match. Pattern-match an existing skill
(e.g. [coding-standards](.agents/skills/coding-standards/SKILL.md)) for shape.

If the skill is human-facing prose, follow the [markdown-writer](.agents/skills/markdown-writer/SKILL.md) rules
(em-dash ban, 120-char wrap, divider per section, link every file/folder mention). If the skill is machine-facing
reference for a tool or stack, the voice rules relax; just stay consistent with the existing skills in that genre.

---

### Adding a new subagent

Add a frontmatter-headed Markdown file under `subagents/<name>.md`. Run `python tools/gen_subagents.py` to emit
per-tool copies in `.claude/agents/` and `.opencode/agents/`. Commit the canonical source AND the generated outputs.

---

### License

By contributing, you agree your changes are licensed under MIT (see [LICENSE](LICENSE)).
