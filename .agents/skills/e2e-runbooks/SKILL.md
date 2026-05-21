---
name: e2e-runbooks
description: Use whenever the user wants to add, run, or refine an end-to-end capability test (one feature exercised against a live stack, behaviour-only assertions, manual or AI-runnable). Triggers on phrases like "add an e2e test for X", "verify the upload flow end-to-end", "run the e2e sweep", "test that the MCP tool actually fires", "smoke test against the staging stack", "build a capability test for the auth flow". Methodology covers spec / tasks-template / runs triple, behaviour-only assertions, canary fixtures, number-by-setup-cost ordering, per-run token + duration accounting, and API client alternatives (Bruno / hurl / curl / VS Code REST Client / httpie). Distinct from the `e2e-testing` skill (Playwright UI testing); this one is for backend capability sweeps. Pairs with the `e2e-runbooks` OpenSpec schema at [Lukk17/openspec-schemas](https://github.com/Lukk17/openspec-schemas) for projects using OpenSpec.
---

### When to use this skill

---

I trigger whenever someone wants to verify a backend capability end-to-end against a live stack. The shape of the work:
one capability per spec, one spec per file, behaviour-only assertions against the running system. Each spec has a
paired immutable tasks-template, and every execution produces a timestamped run record with token and duration
accounting.

Not for Playwright / browser UI testing. Use the `e2e-testing` skill instead for that.

Not for unit tests or integration tests inside the codebase. Use `tdd-workflow` or the language-specific testing
skills (`python-testing`, `golang-testing`, `springboot-tdd`).

This skill is for: "does the deployed service actually do X when you poke it from outside".

---

### Directory layout (scaffold once per project)

---

Before adding the first test, the project needs the directory tree set up. Done once per project; the OpenSpec
schema does it automatically on first `/opsx:new`. Without the schema, scaffold by hand:

```text
e2e/
├── README.md                            # describes the suite (this skill's methodology, project's API client)
├── fixtures/
│   └── README.md                        # canary content conventions per fixture file
└── testing/
    ├── README.md                        # spec / template format reference
    ├── 1-<capability>-test.md           # one immutable spec per test
    ├── 1-<capability>-tasks.template.md # one immutable tasks-template per test
    └── runs/
        ├── README.md                    # runner contract, kept tracked
        └── <ts>_<N>-<capability>-tasks.md  # gitignored, one per execution
```

Add this snippet to the project root `.gitignore` (ignores run files but keeps the runs README tracked):

```text
# e2e capability test run records (kept ephemeral; README stays tracked).
e2e/testing/runs/*.md
!e2e/testing/runs/README.md
```

The four README files (`e2e/README.md`, `e2e/fixtures/README.md`, `e2e/testing/README.md`,
`e2e/testing/runs/README.md`) carry the conventions. The OpenSpec schema ships canonical text for each; for hand
scaffolding, the
[scaffold templates in the schema repo](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks/templates/scaffold)
are the source to copy from.

---

### Methodology overview

---

Three files per capability test:

- **`e2e/testing/{N}-{capability}-test.md`** — the **immutable spec**. Six fixed sections. Never edited between runs;
  if behaviour changes, write a new spec with a new N.
- **`e2e/testing/{N}-{capability}-tasks.template.md`** — the **immutable checklist template**. Mirrors the spec's
  Prerequisites / Reset / Run / Expected sections as checkboxes. Never edited between runs.
- **`e2e/testing/runs/{utc-timestamp}_{N}-{capability}-tasks.md`** — the **execution record**. One per run. Copied from
  the tasks-template at run start, ticked off as the run progresses, filled with Result summary + Verdict + token
  counts at the end. Default-gitignored.

`{N}` is a numeric prefix ordered by setup cost. 1 runs first (cheapest), higher N runs last (needs more state). A
sweep walks the directory in numeric order.

Behaviour-only assertions: HTTP status codes, response body content, persisted state in backing services (MinIO
listings, Qdrant scrolls, Postgres rows, Redis keys). Never assert on log substrings; logs drift across versions and
aren't visible from every runner's shell. If a behaviour assertion fails, a log tail is the next diagnostic step, not
a pass criterion.

---

### Spec sections (fixed, in order)

---

Every spec file has these six sections, in this order, every time:

1. **What this verifies.** Bullet list of behaviours. Concrete and observable.
2. **Prerequisites.** Concrete check commands (curl on a health endpoint, `docker exec redis redis-cli ping`,
   `bru --version`, etc.). Each command in its own fenced code block; prose around the block states the success
   criterion. The runner executes each one before starting and aborts on failure.
3. **Reset state.** One command per code block, in execution order. Wipes whatever the test will write so the run is
   reproducible. Use "None. This test does not write persisted state." if applicable.
4. **Run.** One or more numbered API-client CLI invocations. Multi-step tests tell the runner to wait for a success
   response before continuing to the next step.
5. **Expected.** Observable assertions only. HTTP status, response-body shape and content, persisted state. The runner
   verifies each one after each Run step.
6. **Fixtures.** Paths to local files the test reads. Each fixture must have distinctive canary content (see Fixtures
   section below). Use "None." if none.

---

### Tasks-template sections (fixed)

---

The tasks-template mirrors the spec as checkboxes, plus the execution-accounting fields:

```text
## Tasks

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

## Result summary

<one-paragraph narrative anchored to the Expected assertions>

Input tokens:

Output tokens:

Start (UTC):

End (UTC):

Duration:

---

## Additional tasks I did

<anything off-spec the runner did>
```

---

### Number-by-setup-cost ordering

---

`{N}` prefix is chosen at proposal time based on what the test needs. Lower numbers run first in a sweep.

| N range | Setup cost class                                                                  | Examples                                          |
| ------- | --------------------------------------------------------------------------------- | ------------------------------------------------- |
| 1       | No state to reset, no fixtures, single endpoint or MCP tool                       | Health check, MCP weather lookup, refusal probe   |
| 2       | Single fixture upload OR vision-capable model OR PDF parsing                      | Image description, inline PDF summarization       |
| 3       | Single-service reset (e.g. Redis only)                                            | Cache hit / miss probe                            |
| 4       | Multi-service reset (DB + Redis + Qdrant + MinIO)                                 | Full RAG upload → ingest → retrieve               |
| 5+      | Seeded state + observation of an async background process                         | Compaction, projection rebuild, event replay      |

Pick the lowest unused N that matches the class. A sweep typically runs 1 through N sequentially; CI may parallelise
across classes if isolation allows.

---

### Behaviour-only assertions

---

The Expected section asserts only what the user-facing API or persisted state shows. Examples by category:

**HTTP status.**

```text
The output shows HTTP 200.
The output shows HTTP 422 with a `validation_errors[]` array of length 1.
```

**Response body content (concrete, not "should be valid").**

```text
The response body's `content` field contains a numeric temperature value for the requested city.
The response body's `content` field does NOT contain the phrase "I cannot access live data" (which would indicate the MCP tool was not invoked).
The response body's `sources[]` array has length 2, one entry per fixture file.
```

**Persisted state (queried directly).**

```text
A `docker exec postgres psql ... -c "SELECT count(*) FROM chat_history WHERE user_id='canary'"` returns 2.
A `docker exec redis redis-cli ZCARD chat:canary` returns 0 (cache wiped after compaction).
A Qdrant `scroll` on the `documents` collection filtered by `userId=canary` returns exactly 3 points.
A MinIO `mc ls local/uploads/canary/` shows the uploaded file with non-zero size.
```

**Never logs.**

```text
WRONG: The AscendAgent log contains "MCP tool invoked: getCurrentWeather".
RIGHT: The response body contains a temperature value (which is only possible if the MCP tool was invoked).
```

---

### Canary fixtures

---

Fixtures used by upload-style tests must contain content unique enough that the model couldn't have memorised it. A
passing test then proves retrieval, not recall.

Conventions:

- One-line canary phrase in a `.md` file: invented place name + unique numeric ID. Example: `The HELENA-DEDUP-CANARY
  village holds the 17th annual pierogi festival every August 14th.`
- Short PDFs with invented proper nouns and specific recent retail prices.
- DOCX recipes with distinctive rest times (`Rest the dough for 47 minutes`, not `Rest for an hour`).
- Small images (~100 KB) with a recognisable but uncommon subject (vintage typewriter, hand-knitted scarf with a
  specific pattern).
- Audio clips ≤ 60 seconds with one or two clearly enunciated invented words.

Put fixtures under `e2e/fixtures/`. Each fixture's distinctive content goes in a table in `e2e/README.md`:

```text
| File                     | Used by              | Distinctive content                                                       |
| ------------------------ | -------------------- | ------------------------------------------------------------------------- |
| markdown-canary.md       | RAG (test 5)         | HELENA-DEDUP-CANARY village + 17th annual pierogi festival, August 14.    |
| banana-price-poland.pdf  | RAG (test 5)         | Specific retail price (5.79 PLN/kg on 2026-03-04 in Biedronka Krakow).    |
```

Keep fixtures small. A test should be able to upload them in under 2 seconds.

---

### API client alternatives

---

The skill does not pin a client. Pick one per project and use it consistently across all tests.

| Client                                                                                                | When                                                                | Notes                                                              |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [Bruno CLI](https://www.usebruno.com/)                                                                | REST APIs, multi-step flows, mature collections                     | Single source of API truth; request file is the test fixture.      |
| [Hurl](https://hurl.dev/)                                                                             | Plain-text HTTP, assertions inside the request file                 | Lighter than Bruno; assertions live next to the request.           |
| [VS Code REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client)          | Non-CLI workflows                                                   | `.http` files; OK for human-only execution paths.                  |
| `curl`                                                                                                | Single-shot health checks, MCP HTTP probes                          | Use for prereq probes inside the spec.                             |
| [httpie](https://httpie.io/)                                                                          | Interactive debugging                                               | Avoid for stored test definitions; not a fixture format.           |

For MCP tool tests: drive the request through the agent (not the MCP server directly) so you assert end-to-end
discovery and routing, not just MCP-protocol mechanics.

---

### Generic examples

---

#### Example 1: pure curl (`1-hello-api-test.md`)

```markdown
# Hello API: e2e test

## What this verifies

- The `/hello` endpoint returns HTTP 200 with the expected greeting.
- The endpoint echoes the `name` query parameter into the response.

## Prerequisites

Check the service is reachable.

```bash
curl -fsS http://localhost:8080/actuator/health
```

Expect HTTP 200 with `{"status":"UP"}`.

## Reset state

None. This test does not write persisted state.

## Run

```bash
curl -sS -o /tmp/hello.json -w "%{http_code}" http://localhost:8080/hello?name=canary
```

## Expected

The exit body `/tmp/hello.json` contains `{"greeting":"Hello, canary!"}`.

The HTTP status code written by `-w` is `200`.

## Fixtures

None.
```

#### Example 2: MCP tool round-trip (`2-mcp-tool-test.md`)

```markdown
# Weather MCP: e2e test

## What this verifies

- The agent discovers and invokes the WeatherMCP tool for a weather prompt.
- The response contains concrete weather data, not a refusal.

## Prerequisites

Check the agent health.

```bash
curl -fsS http://localhost:9917/actuator/health
```

Expect HTTP 200 with `{"status":"UP"}`.

Check the WeatherMCP server.

```bash
curl -fsS http://localhost:9998/actuator/health
```

Expect HTTP 200 with `{"status":"UP"}`.

## Reset state

None.

## Run

Send the weather prompt and wait for the response.

```bash
bru run "ascend-agent/testing/weather-mcp-prompt.yml" --env ascend-local
```

## Expected

The Bruno output shows HTTP 200.

The response body's `content` field contains a numeric temperature value.

The response body's `content` does NOT contain the phrases "I cannot access live data" or "I don't have real-time
data" (which would mean the MCP tool was not invoked).

## Fixtures

None.
```

#### Example 3: fixture upload + retrieval (`5-rag-canary-test.md`)

```markdown
# RAG canary: e2e test

## What this verifies

- An uploaded markdown file ingests into the vector store.
- A later prompt mentioning the canary phrase returns the file as a source.

## Prerequisites

Check MinIO, Qdrant, agent are up (one curl block each).

## Reset state

Drop the canary user's vector points.

```bash
curl -X POST "http://localhost:6333/collections/documents/points/delete" -H "Content-Type: application/json" -d '{"filter":{"must":[{"key":"userId","match":{"value":"canary"}}]}}'
```

Drop the canary user's MinIO objects.

```bash
mc rm --recursive --force local/uploads/canary/
```

## Run

1. Upload the canary fixture.

```bash
bru run "ascend-agent/testing/rag-upload-canary.yml" --env ascend-local
```

2. Wait for ingestion (poll the agent's `/ingestion/status` until `READY`).

3. Send a retrieval prompt that mentions the canary phrase.

```bash
bru run "ascend-agent/testing/rag-retrieve-canary.yml" --env ascend-local
```

## Expected

The upload response shows HTTP 200 with a non-empty `documentId`.

After ingestion, a Qdrant `scroll` filtered by `userId=canary` returns at least 1 point.

The retrieval response body's `sources[]` array contains exactly 1 entry whose `key` ends in `markdown-canary.md`.

The retrieval response's `content` field references the canary phrase from the fixture.

## Fixtures

- `e2e/fixtures/markdown-canary.md` — single-line canary phrase with HELENA-DEDUP-CANARY village + invented festival
  date.
```

---

### Runs directory contract

---

Each run record is named:

```text
e2e/testing/runs/<UTC-timestamp>_<N>-<capability>-tasks.md
```

UTC timestamp uses ISO-8601 with colons replaced by hyphens so the filename is filesystem-safe across Windows, macOS,
Linux:

```text
2026-05-12T17-23-36_1-weather-mcp-tasks.md
2026-05-12T17-23-36_2-image-description-tasks.md
2026-05-12T17-23-36_3-summarization-tasks.md
```

Group all tests from one sweep under the same timestamp; one timestamp equals one full e2e sweep. Mixed-timestamp
runs imply partial sweeps, useful when iterating on one test.

Default-gitignore `e2e/testing/runs/`. Promote to committed audit trail by adding `runs/<YYYY-MM>/` subfolders when
the team needs traceability.

---

### Runner contract (AI or human)

---

The runner, whether AI agent or human, follows this sequence for every run:

1. Read the spec `e2e/testing/{N}-{capability}-test.md`.
2. Copy the matching tasks-template to `e2e/testing/runs/<UTC-timestamp>_{N}-{capability}-tasks.md`.
3. **Record `Start (UTC)` as the very first action.** Wall-clock instant before the prerequisite checks begin.
4. Execute each task in spec order. Tick the box on success; record what went wrong on failure under "Additional tasks
   I did".
5. After the Verdict line is decided, **record `End (UTC)`.** Wall-clock instant after the last verification step.
6. Compute `Duration = End - Start` as `HH:MM:SS`. **Wall-clock for the whole test** (prereqs + reset + run + verify),
   NOT just the API client invocation. A Bruno call may take 5 s while the full test takes 2 minutes; the field
   captures the latter.
7. Fill `Input tokens` and `Output tokens` with best estimate of LLM tokens consumed. Leave blank if exact numbers
   aren't available. **Do not invent.**
8. Write the Result summary paragraph and the Verdict (PASS or FAIL).
9. Log anything done outside the spec under "Additional tasks I did" (extra diagnostics, retries, manual log
   inspection).

---

### Integration with the startup-readiness banner

---

If your service uses the startup-readiness banner from the [coding-standards](../coding-standards/SKILL.md) skill,
the banner's `External dependencies` section is the first stop when an e2e prereq fails. A `[FAILED]` row tells you
which dependency to fix before re-running.

The runner should check the banner once at sweep start. If any backend dependency shows `[FAILED]`, fix that first;
don't bother running tests against a half-up stack.

---

### Companion OpenSpec schema

---

Projects using [OpenSpec](https://github.com/Fission-AI/OpenSpec) can install the matching
[`e2e-runbooks` schema](https://github.com/Lukk17/openspec-schemas/tree/master/e2e-runbooks) for full
lifecycle integration via `/opsx:new --schema e2e-runbooks`. The schema artifact DAG matches the
methodology in this skill: proposal → test-spec → tasks-template → run.

Install from the consumer project root:

```bash
git clone --depth 1 https://github.com/Lukk17/openspec-schemas /tmp/lukk17-schemas
```

```bash
cp -r /tmp/lukk17-schemas/e2e-runbooks openspec/schemas/
```

```bash
rm -rf /tmp/lukk17-schemas
```

```powershell
git clone --depth 1 https://github.com/Lukk17/openspec-schemas $env:TEMP\lukk17-schemas
```

```powershell
Copy-Item -Recurse $env:TEMP\lukk17-schemas\e2e-runbooks openspec\schemas\
```

```powershell
Remove-Item -Recurse -Force $env:TEMP\lukk17-schemas
```

Then either pass `--schema e2e-runbooks` to `/opsx:new`, or set `default_schema: e2e-runbooks` in
`openspec/config.yaml`.

The skill works without the schema. The schema gives projects on OpenSpec the slash-command lifecycle on top of the
same methodology.

---

### What this skill is NOT for

---

- **UI / browser tests.** Use [e2e-testing](../e2e-testing/SKILL.md) (Playwright).
- **Unit tests.** Use [tdd-workflow](../tdd-workflow/SKILL.md), [python-testing](../python-testing/SKILL.md),
  [golang-testing](../golang-testing/SKILL.md), [springboot-tdd](../springboot-tdd/SKILL.md).
- **Sandbox-mode API regression tests** without DB dependencies. Use
  [ai-regression-testing](../ai-regression-testing/SKILL.md).
- **Load / soak / chaos testing.** Out of scope; this skill is about correctness, not capacity or resilience.
