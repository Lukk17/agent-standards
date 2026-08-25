# Integration notes for `e2e-runbooks`

## Lifecycle: change directory plus `e2e/` tree

OpenSpec assumes every artifact lives under `openspec/changes/<change-id>/` during the proposal cycle and that
`archive` promotes finished content to `openspec/specs/`. This schema's artifacts have a different final home —
specs under `e2e/testing/`, their run-record templates under `e2e/testing/templates/`, and execution records under
`e2e/testing/runs/` — so the schema instructs a **dual write** rather than relying on archive.

```text
change-dir artifact                         copy kind          working-tree destination
─────────────────────────────────────────────────────────────────────────────────────────────────
openspec/changes/<id>/proposal.md           (none)             stays in the change dir only
openspec/changes/<id>/test-spec.md          identical     ──►  e2e/testing/{N}-{capability}-test.md
openspec/changes/<id>/tasks-template.md     identical     ──►  e2e/testing/templates/{N}-{capability}-tasks.template.md
openspec/changes/<id>/run.md                timestamped   ──►  e2e/testing/runs/<UTC-ts>_{N}-{capability}-tasks.md  (gitignored)
```

Resulting `e2e/` tree in the consumer project:

```text
e2e/
├── fixtures/
└── testing/
    ├── {N}-{capability}-test.md              # spec
    ├── templates/
    │   └── {N}-{capability}-tasks.template.md
    └── runs/
        └── <UTC-ts>_{N}-{capability}-tasks.md   # gitignored
```

Why two copies:

- The **change-dir copy** is the proposal's audit trail. It pins the artifact to the change that introduced (or
  modified) it, and travels with the change through review and archive.
- The **`e2e/testing/` copy** is the working asset that runs consume. It is what `e2e/testing/runs/` records point
  back to. Sweeps walk `e2e/testing/*-test.md`, not the change directories.

Drift between the two copies is the most likely defect class. When you modify a spec, do the same edit in the
change-dir copy in the same commit — never let them diverge silently.

Proposal stays in the change directory only. There is no `e2e/proposals/` mirror.

## Pairing with the agent-standards skill and subagent

The methodology lives in three places that ship together via
[Lukk17/agent-standards](https://github.com/Lukk17/agent-standards):

- `.agents/skills/e2e-runbooks/SKILL.md` is the methodology source of truth.
- `.claude/agents/e2e-runner.md` and `.opencode/agents/e2e-runner.md` are the runner subagent — the recommended
  delegate when driving a sweep. It enforces the runner contract (Start/End UTC, Duration, tokens, Verdict) and the
  dual-write into `e2e/testing/runs/`.
- This schema is the operational shape for OpenSpec users.

When you edit one, audit the others in the same change. Drift between methodology, subagent behaviour, and schema
templates is the most likely defect class.

Each piece is independently installable. Skill alone works without OpenSpec. Schema alone works without
agent-standards. Together they reinforce each other.

## Sweep orchestration

The main agent owns the sweep, not a runner. It reads `e2e/testing/*-test.md` in numeric order, picks one UTC
timestamp that all runners share, and spawns one `e2e-runner` subagent per test. Before spawning, the main agent asks
the user how many runners to spawn in parallel — there is no preset ceiling. The right number depends on the test
environment (a dedicated stack tolerates more parallelism than a shared dev stack, and external dependencies like
license servers or paid APIs may dictate a low number).

As each runner returns its verdict, the main agent spawns the next pending test until every spec has run. Then it
aggregates: pass/fail counts, total token usage, total wall-clock time (the longest single run, not the sum), and a
short list of failures with one-line causes copied from each failing runner's report.

The user-chosen parallel count can be saved as `e2e-runner-max-parallel: <N>` in the consumer project's `AGENTS.md`
so future sweeps reuse the same number without re-asking.

## Concurrency analysis

Each spec's `Concurrency` section tells the main agent which tests can run at the same time as which others. The main
agent reads every spec before spawning, then groups tests by the resources they touch:

- Two tests whose `Mutates:` lists do not overlap can run in the same batch.
- Two tests whose `Mutates:` lists overlap (same store, same collection/table/bucket, same partition) must run one
  after the other.
- A test with `Serial: true` waits for all in-flight runners to finish, runs alone, then the rest of the queue
  resumes.

The user-chosen parallel number is the upper limit; the `Concurrency` rules can only reduce parallelism below it,
never raise it above. Eight tests with fully disjoint `Mutates:` lists and a user-chosen limit of three will still
run three at a time.

Field semantics (the agent-standards skill carries the authoritative definitions; this is a quick reference):

- `Mutates:` — every backing-service resource the test writes to, deletes from, or invalidates. Name the store and
  the collection / table / bucket; add a partition (user id, tenant id) when the test only touches one. Read-only
  probes do not count — write `none`.
- `Conflicts with:` — tests this one cannot run alongside even when the `Mutates:` lists do not overlap. Typical
  entries: "any test that restarts the stack", "any test that talks to the license server". Leave blank if the only
  conflicts are obvious from `Mutates:` overlap.
- `Serial:` — literal `true` or `false`. `true` means schema migrations, full-stack restarts, license-server
  interactions, anything touching global config. Default `false`.

A test that passes when run alone but fails when run in a sweep is almost always a missing entry in some spec's
`Mutates:` list. The fix is to add the missing resource to the spec, not to insert a sleep.

## API client choice

The schema does not pin a client. Pick one per project and use it consistently across all tests. Recommended defaults:

| Client | When | Notes |
| --- | --- | --- |
| [Bruno CLI](https://www.usebruno.com/) | REST APIs, multi-step flows, mature collections | Single source of API truth; request file = test fixture. Pin requests to `X-User-Id` or similar per-project header. |
| [Hurl](https://hurl.dev/) | Plain-text HTTP, assertions embedded in the request file | Lighter than Bruno; assertions live next to the request. |
| `curl` | Single-shot health checks, MCP HTTP probes | Use for prereq probes inside the spec; not for the main Run step unless the test is trivially small. |
| [httpie](https://httpie.io/) | Interactive debugging | Avoid for stored test definitions; it's an ergonomic CLI, not a fixture format. |
| VS Code REST Client | Non-CLI workflows | `.http` files; OK for human-only execution paths. |

For MCP tool tests, drive through the agent (not the MCP server directly) so you assert end-to-end discovery and
routing, not just MCP-protocol mechanics.

## CI integration sketch

```yaml
# .github/workflows/e2e-sweep.yml
name: e2e-sweep
on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * *"   # daily sweep
jobs:
  sweep:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d --build
      - run: npm install -g @usebruno/cli   # or hurl / etc.
      - run: |
          for spec in e2e/testing/*-test.md; do
            N="${spec##*/}"
            # Open the matching run record from the template, drive through the
            # API client, tick the boxes from CI output, commit the record
            # under runs/.
          done
```

The runner contract is the same whether human or AI is executing. CI just automates the runner role.

## Recording runs in git

Defaults assume `e2e/testing/runs/` is gitignored — runs are ephemeral, useful as audit when reviewed, noise when
committed. For an audit trail, commit under `runs/<YYYY-MM>/` subfolders so a sweep's records cluster together.
