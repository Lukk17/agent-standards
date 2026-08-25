# e2e-runbooks

OpenSpec schema for spec-driven, AI-or-human-executable, behaviour-only e2e capability tests.

## What it does

Each capability test you add gets an **immutable spec** describing what it verifies, a paired **immutable
tasks-template** with checkboxes mirroring the spec, and one **run record** per execution. Run records carry start /
end UTC, computed duration, and best-estimate LLM token consumption.

Assertions are observable behaviour only: HTTP status codes, response body content, persisted state in MinIO / Qdrant
/ Postgres / etc. Never log substrings; they drift across versions and aren't visible from every runner's shell.

## Artifact DAG

```text
proposal ─► test-spec ─► tasks-template ─► run (per execution)
```

- **proposal** — required only when adding a new capability test. Names the behaviour, setup cost class, fixtures, API
  client invocation, chosen N prefix.
- **test-spec** — immutable spec describing one capability in seven fixed sections (What this verifies, Prerequisites, Reset state, Run, Expected, Fixtures, Concurrency).
- **tasks-template** — immutable checklist mirroring the spec.
- **run** — execution record. Filled per execution.

## Concurrency profile

Every proposal (and the test-spec generated from it) carries a three-line **Concurrency profile** declaring how the
test interacts with other tests in a sweep:

- **Mutates:** the backing-service resources the test writes to, deletes from, or invalidates. Name the store and the
  collection / table / bucket; add a partition (user id, tenant id) when the test only touches one. Read-only probes
  do not count — write `none`.
- **Conflicts with:** other tests this one cannot run alongside even when the `Mutates:` lists do not overlap.
  Typical entries: `"any test that restarts the stack"`, `"any test that talks to the license server"`. Leave blank
  if the only conflicts come from `Mutates:` overlap.
- **Serial:** literal `true` or `false`. `true` means the test must run alone — schema migrations, full-stack
  restarts, anything touching global config. Default `false`.

The main agent driving a sweep reads these three fields from every spec before spawning runners. It asks the user how
many tests to run in parallel, then schedules them so that no two parallel tests have overlapping `Mutates:` lists,
none names the other under `Conflicts with:`, and any `Serial: true` test runs alone. See
[`INTEGRATION.md`](./INTEGRATION.md) for the full scheduling rule.

## Where files land

OpenSpec drafts every artifact inside the change directory (`openspec/changes/<change-id>/`). For this schema, three
of the four artifacts also have a permanent home in the consumer project's `e2e/` tree. The agent writes to BOTH
locations because OpenSpec's `archive` command only auto-promotes `openspec/specs/` content; everything else needs an
explicit dual-write:

| Artifact         | Change-dir path (OpenSpec audit trail)                | Final home (working asset)                                              |
| ---------------- | ------------------------------------------------------ | ----------------------------------------------------------------------- |
| `proposal`       | `openspec/changes/<id>/proposal.md`                    | _none — proposal stays in the change dir_                               |
| `test-spec`      | `openspec/changes/<id>/test-spec.md`                   | `e2e/testing/{N}-{capability}-test.md`                                  |
| `tasks-template` | `openspec/changes/<id>/tasks-template.md`              | `e2e/testing/templates/{N}-{capability}-tasks.template.md`              |
| `run`            | `openspec/changes/<id>/run.md`                         | `e2e/testing/runs/{utc-timestamp}_{N}-{capability}-tasks.md` (gitignored)|

Each artifact's `instruction:` in [`schema.yaml`](./schema.yaml) tells the agent to do the dual-write. `{N}`,
`{capability}`, and `{utc-timestamp}` are filled by the agent from the proposal's content — OpenSpec itself does not
substitute schema placeholders in `generates:` paths.

## Install

This schema lives at `openspec/schemas/e2e-runbooks/` in the source repo — the same path it needs in your consumer
project. Install is a `git fetch` + `git checkout` from inside your project; only the schema's directory is written,
nothing else in your tree is touched.

Your consumer project must be a git repo and must have OpenSpec initialised (`openspec init`). Run from the project
root:

```bash
git fetch --depth 1 https://github.com/Lukk17/openspec-schemas v0.1.0
```

```bash
git checkout FETCH_HEAD -- openspec/schemas/e2e-runbooks
```

The same two commands work in PowerShell. The files land in your working tree AND staged — review with
`git diff --staged` and commit when ready. To upgrade later, re-run with the new tag.

Then either invoke per-change (the `change` subcommand is required; `--schema` is an option on it):

```bash
openspec new change "add-weather-mcp-test" --schema e2e-runbooks
```

Or set it as the default in your project's `openspec/config.yaml` and drive it with `/opsx:propose`:

```yaml
default_schema: e2e-runbooks
```

## Companion skill and subagent

This schema is one corner of a three-piece kit shipped together by
[Lukk17/agent-standards](https://github.com/Lukk17/agent-standards):

- **Skill** at `.agents/skills/e2e-runbooks/SKILL.md` — methodology source of truth. Behaviour-only assertions, canary
  fixtures, API client alternatives (Bruno, hurl, REST Client, curl, httpie), runs-directory contract, generic worked
  examples.
- **Subagent** at `.claude/agents/e2e-runner.md` and `.opencode/agents/e2e-runner.md` — the recommended delegate when
  driving a sweep end-to-end. Owns the runner contract (Start/End UTC, Duration, tokens, Verdict) and the change-dir /
  `e2e/testing/runs/` dual-write. The schema and skill also work without it; runs can be driven from the main session
  or a general runner.
- **Schema** (this folder) — operationalises the methodology for OpenSpec users via the artifact DAG above.

Each piece is independently installable: the skill works in projects without OpenSpec, the schema works in projects
without agent-standards. Together they reinforce each other.

## OpenSpec limitations to know

This schema is designed around two known OpenSpec limitations:

- [Fission-AI/OpenSpec#777](https://github.com/Fission-AI/OpenSpec/issues/777) — schema `instruction` fields can name
  external skills, but `openspec-continue-change` doesn't reliably delegate. We embed the runner contract directly in
  the `run` artifact's instruction prose, no mid-DAG skill delegation.
- [Fission-AI/OpenSpec#666](https://github.com/Fission-AI/OpenSpec/issues/666) — OpenSpec's spec format is partly
  hard-coded in package code. We name the spec artifact `test-spec` (not `spec`) to sidestep the hard-coded format.

## License

MIT.
