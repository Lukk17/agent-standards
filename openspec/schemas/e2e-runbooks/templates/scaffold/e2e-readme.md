# End-to-end capability tests

Manual / AI-runnable e2e suite for this project. Each test exercises one capability end-to-end against a live stack
and asserts only **observable behaviour**: HTTP status codes, response body content, persisted state in backing
services (databases, object stores, vector stores, caches). Logs are diagnostic, not pass criteria.

## What's here

```text
e2e/
├── README.md                            # this file
├── fixtures/                            # canary inputs the tests upload
│   └── README.md
└── testing/                             # numbered specs + templates/ + runs/
    ├── README.md
    ├── 1-<capability>-test.md           # immutable spec
    ├── 2-<capability>-test.md
    ├── templates/                       # immutable run-record templates, one per spec
    │   ├── README.md
    │   ├── 1-<capability>-tasks.template.md
    │   └── 2-<capability>-tasks.template.md
    └── runs/
        ├── README.md
        └── <UTC-timestamp>_<N>-<capability>-tasks.md   # one per executed test (gitignored)
```

Tests are number-prefixed by setup cost. `1` needs the least, higher numbers need more. Each spec under `testing/`
has a paired tasks-template in `testing/templates/` that the runner copies into `testing/runs/` with a sweep
timestamp, ticks off checkbox by checkbox as it executes, and fills with results, token usage, and wall-clock time.

## Flow

1. Read the spec at `testing/{N}-<capability>-test.md`.
2. Copy `testing/templates/{N}-<capability>-tasks.template.md` to
   `testing/runs/<UTC-timestamp>_{N}-<capability>-tasks.md`.
3. Record `Start (UTC)` as the very first action.
4. Execute prerequisites → reset state → run → expected. Tick boxes as you go.
5. Record `End (UTC)`, compute Duration as HH:MM:SS.
6. Fill the Result summary, Verdict, and any off-spec actions under "Additional tasks I did".

Full methodology in the `e2e-runbooks` skill in [Lukk17/agent-standards](https://github.com/Lukk17/agent-standards/tree/master/.agents/skills/e2e-runbooks).

## API client

Pick one client per project and use it consistently across all tests. Recommended defaults: Bruno CLI, hurl, or
plain curl for the simplest cases. Document the project's choice in the project's main README; this file is generic.

## Prerequisites before any test

Each individual spec lists its own concrete prerequisite checks. Common to all:

1. The service under test is reachable on its bound port.
2. Backing services (DB, cache, vector store, object store, MCP servers if any) are up.
3. The chosen API client is installed.

If the service emits a startup readiness banner (see the `coding-standards` skill canonical convention), inspect the
banner once at sweep start. Any `[FAILED]` row under external dependencies blocks the sweep.

## Adding a new test

Create the change with the e2e-runbooks schema:

```bash
openspec new change "add-<capability>-test" --schema e2e-runbooks
```

Then drive it with `/opsx:propose` (if `default_schema: e2e-runbooks` is set in `openspec/config.yaml`). The schema
walks through proposal → test-spec → tasks-template → run. Or, without OpenSpec, follow the methodology in the
`e2e-runbooks` skill and hand-write the three files in the conventional shape.
