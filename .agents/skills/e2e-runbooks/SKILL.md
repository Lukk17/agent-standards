---
name: e2e-runbooks
description: Capability testing against a live stack, one feature per immutable spec, with behaviour-only assertions, canary fixtures, setup-cost ordering, per-run token and duration accounting, and parallel subagent orchestration. Use when you say "add an e2e test for the upload flow", "run the e2e sweep", "test that the MCP tool actually fires", "smoke test against the staging stack", or "verify this capability end to end". Not for Playwright browser UI testing, use `e2e-testing`.
---

# E2E Runbooks

Verify that a deployed service actually does what it claims when poked from outside, one capability per spec, asserted
only on what the running system shows. Each spec has a paired immutable tasks-template, and every execution leaves a
timestamped run record with token and duration accounting.

---

### When to activate

- Adding, running, or refining an end-to-end capability test against a live or staging stack.
- Running a sweep across the whole capability suite and aggregating the verdicts.
- Verifying that an MCP tool, a background ingestion job, or a multi-service flow works end to end.
- Smoke testing a deployment before promoting it.
- Setting up the `e2e/` directory tree in a project that has none.

---

### When not to activate

- Browser and UI journeys. Use `e2e-testing`, which owns Playwright.
- Unit and integration tests inside the codebase. Use `tdd-workflow`, `python-patterns`, `golang-patterns`, or
  `springboot-patterns`.
- Sandbox-mode API regression tests that need no deployed stack. Use `ai-regression-testing`.
- Load, soak, or chaos testing. Out of scope: this skill is about correctness, not capacity or resilience.
- Designing the API being tested. Use `api-design`.

---

### Directory layout

Scaffold once per project. The OpenSpec schema does this automatically on first use. Without it, create the tree by
hand.

```text
e2e/
├── README.md
├── fixtures/
│   └── README.md
└── testing/
    ├── README.md
    ├── 1-<capability>-test.md
    ├── templates/
    │   └── 1-<capability>-tasks.template.md
    └── runs/
        ├── README.md
        └── <ts>_<N>-<capability>-tasks.md
```

Add this to the project root `.gitignore`, which drops the ephemeral run records and keeps the runs README tracked.

```text
e2e/testing/runs/*.md
!e2e/testing/runs/README.md
```

The four README files carry the conventions: what the suite covers, the canary content per fixture, the spec and
template format, and the runner contract. The OpenSpec schema ships canonical text for each, and the [scaffold templates
in the schema repo](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks/templates/scaffold) are the
source to copy from when scaffolding by hand.

---

### The three-file triple

Every capability test is three files, and the split is what makes a run auditable.

- `e2e/testing/{N}-{capability}-test.md`, the immutable spec. Seven fixed sections. Never edited between runs. When
  behaviour changes, write a new spec with a new `{N}`.
- `e2e/testing/templates/{N}-{capability}-tasks.template.md`, the immutable checklist. Mirrors the spec's Prerequisites,
  Reset, Run and Expected sections as checkboxes.
- `e2e/testing/runs/{utc-timestamp}_{N}-{capability}-tasks.md`, the execution record. Copied from the template at run
  start, ticked off as the run progresses, closed with a Result summary, a Verdict, and token counts. Gitignored by
  default.

Editing a spec to make a failing run pass destroys the record. Fix the system, or write a new spec.

---

### Spec sections, fixed and in order

Every spec has these seven sections, in this order, every time.

1. What this verifies. Bullet list of concrete, observable behaviours.
2. Prerequisites. Concrete check commands, one per fenced block, with the success criterion in the prose around the
   block. The runner executes each before starting and aborts on failure.
3. Reset state. One command per block, in execution order, wiping whatever the test will write so the run is
   reproducible. Use "None. This test does not write persisted state." when that is true.
4. Run. Numbered API-client invocations. Multi-step tests tell the runner to wait for success before continuing.
5. Expected. Observable assertions only, verified after each Run step.
6. Fixtures. Paths to local files the test reads, each with distinctive canary content. Use "None." if none.
7. Concurrency. The resources this test mutates, plus a `Serial:` flag.

The tasks-template mirrors it as checkboxes plus the accounting fields.

```text
### Prerequisites
- [ ] <one checkbox per prereq>

### Reset state
- [ ] <one checkbox per reset command>

### Run
- [ ] <one checkbox per numbered Run step>

### Expected
- [ ] <one checkbox per assertion>

### Verdict
- [ ] Verdict: PASS / FAIL (delete the wrong one)

Result summary: <one paragraph anchored to the Expected assertions>
Input tokens:
Output tokens:
Start (UTC):
End (UTC):
Duration:

Additional tasks I did: <anything off-spec>
```

---

### Behaviour-only assertions

Assert what the user-facing API or the persisted state shows. Never assert on a log substring: logs drift across
versions and are not visible from every runner's shell. When a behaviour assertion fails, a log tail is the next
diagnostic step, not a pass criterion.

Fail: passes or fails on a string the service may rename tomorrow.

```text
The agent log contains "MCP tool invoked: getCurrentWeather".
```

Pass: asserts the observable consequence, which is only possible if the tool ran.

```text
The response body's `content` field contains a numeric temperature for the requested city.
The response body's `content` does NOT contain "I cannot access live data".
```

Persisted state counts as observable when it is queried directly.

```text
A `docker exec postgres psql ... -c "SELECT count(*) FROM chat_history WHERE user_id='canary'"` returns 2.
A Qdrant scroll on `documents` filtered by `userId=canary` returns exactly 3 points.
A `mc ls local/uploads/canary/` shows the uploaded file with non-zero size.
```

---

### Number by setup cost

The `{N}` prefix is chosen at proposal time from what the test needs. Lower numbers run first in a sweep, so a cheap
failure stops the expensive tests from wasting a stack.

| N | Setup cost class | Examples |
| --- | --- | --- |
| 1 | No state to reset, no fixtures, single endpoint or tool call | Health check, MCP weather lookup, refusal probe |
| 2 | Single fixture upload, vision model, or document parsing | Image description, inline PDF summarisation |
| 3 | Single-service reset | Cache hit and miss probe |
| 4 | Multi-service reset | Full upload, ingest, retrieve round trip |
| 5+ | Seeded state plus an async background process to observe | Compaction, projection rebuild, event replay |

Pick the lowest unused N that matches the class.

---

### Canary fixtures

A fixture used by an upload test must contain content unique enough that the model could not have memorised it, so a
passing test proves retrieval rather than recall.

Fail: the model can answer from training data, so the test passes with retrieval broken.

```text
fixtures/facts.md: "The capital of France is Paris."
```

Pass: an invented proper noun and a specific number nothing else contains.

```text
fixtures/markdown-canary.md: "The HELENA-DEDUP-CANARY village holds the 17th annual pierogi festival every August 14th."
```

The same principle in other formats: short PDFs with invented product names and specific prices, DOCX recipes with
distinctive rest times (47 minutes, not an hour), small images of an uncommon but recognisable subject, audio clips
under 60 seconds containing an invented word. Keep every fixture small enough to upload in under two seconds, put them
in `e2e/fixtures/`, and record each one's distinctive content in a table in `e2e/README.md`.

---

### API client

The skill pins no client. Pick one per project and use it across every test.

| Client | When | Notes |
| --- | --- | --- |
| [Bruno CLI](https://www.usebruno.com/) | REST APIs, multi-step flows, mature collections | Single source of API truth, and the request file is the fixture |
| [Hurl](https://hurl.dev/) | Plain-text HTTP with assertions inside the request file | Lighter than Bruno, with assertions next to the request |
| [VS Code REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) | Human-only execution paths | `.http` files, no CLI runner |
| `curl` | Single-shot health checks and protocol probes | Use for prerequisite checks inside the spec |
| [httpie](https://httpie.io/) | Interactive debugging | Not a stored-test format |

For MCP tool tests, drive the request through the agent rather than the MCP server directly, so the assertion covers
discovery and routing rather than protocol mechanics alone.

---

### Runs directory contract

Name each run record with the sweep timestamp and the spec it came from. Use ISO-8601 with colons replaced by hyphens so
the filename is safe on Windows, macOS and Linux.

```text
2026-05-12T17-23-36_1-weather-mcp-tasks.md
2026-05-12T17-23-36_2-image-description-tasks.md
```

One timestamp equals one full sweep, so every record from a sweep shares a prefix and a mixed-timestamp directory reads
as partial sweeps. Promote runs to a committed audit trail by adding `runs/<YYYY-MM>/` subfolders when the team needs
traceability.

---

### Runner contract

The runner, human or agent, follows the same sequence every time.

1. Read the spec.
2. Copy the matching tasks-template into `e2e/testing/runs/` under the sweep timestamp.
3. Record `Start (UTC)` as the first action, before the prerequisite checks.
4. Execute each task in spec order, ticking on success and recording what went wrong on failure.
5. Record `End (UTC)` once the Verdict is decided.
6. Compute `Duration = End - Start` as `HH:MM:SS`, wall-clock for the whole test including prereqs and reset, not just
   the API call.
7. Fill `Input tokens` and `Output tokens` with the best available estimate. Leave blank when unavailable rather than
   inventing a number.
8. Write the Result summary and the Verdict.
9. Log anything done outside the spec under "Additional tasks I did".

---

### Sweeps

For more than one test, the main session delegates rather than executing. It orders the specs by `{N}`, picks one UTC
sweep timestamp, and fans out one [`e2e-runner`](../../../subagents/e2e-runner.md) subagent per spec, refilling the
in-flight slots as verdicts return. Isolated context per test, per-test token accounting, and failure isolation are what
the fan-out buys.

The default parallel cap is 5, confirmed with the user before each sweep, and conflicting tests serialise below it. The
reasoning behind the cap, the concurrency declaration format, and the scheduling algorithm are in
[references/orchestration.md](references/orchestration.md).

The main session never reads prerequisite output and ticks boxes itself, never invokes an API client directly during a
sweep, never edits a spec mid-sweep, and never exceeds the confirmed cap. A single test being debugged can be run
inline, since the subagent layer exists for fan-out.

---

### Startup readiness

When the service uses the startup-readiness banner from `observability-and-logging`, the banner's external dependency
section is the first stop when a prerequisite check fails. Check it once at sweep start: a `[FAILED]` row names the
dependency to fix, and there is no point running tests against a half-up stack.

---

### Reference map

| Task | Open |
| --- | --- |
| Write a spec from a worked example: curl, MCP tool round trip, fixture upload and retrieval | [references/examples.md](references/examples.md) |
| Set the parallel cap, declare what a test mutates, schedule a sweep around conflicts | [references/orchestration.md](references/orchestration.md) |
| Install the companion OpenSpec schema for slash-command lifecycle integration | [references/openspec-schema.md](references/openspec-schema.md) |

---

### Related skills

- `e2e-testing` owns browser and UI testing with Playwright, and the canonical flaky-test policy.
- `tdd-workflow` owns unit and integration tests inside the codebase, along with `python-patterns`,
  `golang-patterns` and `springboot-patterns`.
- `ai-regression-testing` owns sandbox-mode API regression tests that need no deployed stack.
- `observability-and-logging` owns the startup-readiness banner this skill reads at sweep start.
- `docker-patterns` owns the local stack the tests are pointed at.

---

### Checklist

- [ ] One capability per spec, one spec per file, seven sections in order.
- [ ] Every assertion is observable through the API or the persisted state, never a log line.
- [ ] The `{N}` prefix matches the test's real setup cost class.
- [ ] Every fixture carries canary content the model could not have memorised.
- [ ] The Reset section wipes everything the Run section writes.
- [ ] The Concurrency section names every resource the test mutates.
- [ ] The spec and template were not edited to make a run pass.
- [ ] Every run record carries Start, End, Duration, token counts, a Result summary, and a Verdict.
- [ ] A sweep used one timestamp across every run record.
- [ ] The parallel cap was confirmed with the user before fan-out.
