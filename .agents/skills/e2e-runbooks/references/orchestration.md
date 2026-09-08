# Sweep orchestration and concurrency

How a main session fans a sweep out across `e2e-runner` subagents, how many run at once, and how tests that touch the
same state are kept apart. Depth behind the Sweeps section of [SKILL.md](../SKILL.md).

---

### Why one subagent per test

The main session picks specs, watches for completion, and aggregates. It never executes a test itself. Delegating each
spec to one [`e2e-runner`](../../../../subagents/e2e-runner.md) buys four things:

- Isolated context per test, so no runner carries "I already saw endpoint X" reasoning into an unrelated spec.
- Per-test token accounting, since each runner reports its own input and output estimate and the sweep sums them.
- Failure isolation, so a runner that crashes or goes off-spec cannot taint another test's verdict.
- Real parallelism against the live stack rather than a serial walk through the suite.

---

### The parallel cap

Default 5, confirmed with the user before each sweep. Spawn up to 5 runners at once and dispatch the next pending spec
as each verdict returns.

Five is the default for four reasons that all bite at around the same point. Most provider rate limits handle 5
concurrent sessions per key comfortably, while 10 or more starts hitting per-minute caps mid-sweep once every runner is
making several calls. A typical dev stack of a database, a cache, a vector store, object storage and a couple of MCP
servers handles 5 concurrent test cells without contention, and past that you are fighting your own infrastructure. Five
concurrent reports is something a main session can actually aggregate, where ten produces a wall of intermediate replies
to sift. And most capability suites are 5 to 20 tests, so 5 parallel means one to four batches and a total wall-clock
close to a single batch.

Adjust to the situation before fanning out, naming the default and the alternatives:

- 3 when the test environment is shared with other developers, or the API budget is tight.
- 5 for a typical dedicated dev stack on a normal provider tier.
- 8 to 10 only with a dedicated test environment and a provider tier that supports the load.

The user's answer wins. When the project has already saved an override such as `e2e-runner-max-parallel: <N>` in its
AGENTS.md, use that value and skip the question, because the saved value is the user's prior answer.

---

### Sweep flow

1. Read `e2e/testing/*-test.md` and order the specs by their numeric `{N}` prefix.
2. Pick one UTC sweep timestamp, ISO-8601 with colons replaced by hyphens, so every run record from this sweep shares a
   prefix.
3. Spawn up to N runners in parallel, each given one spec path and the sweep timestamp.
4. As each runner returns its structured report, record the Verdict and the token counts, then dispatch the next pending
   spec to keep the in-flight count at N.
5. Once every spec has returned, compile the summary: pass and fail counts, total tokens summed across runners, total
   wall-clock as the maximum end time minus the sweep start (not the sum), and each failure with its one-line cause.
6. Report the summary. Run records stay in `e2e/testing/runs/` under the runs contract.

Debugging a single test needs no fan-out. Run it inline or spawn one runner, and both paths follow the same runner
contract.

---

### Declaring what a test mutates

The cap is a ceiling, not a target. Tests against shared infrastructure frequently cannot run side by side because they
write the same state, and two tests that both wipe `chat_history` for user `canary` will corrupt each other if they
overlap by a second. Every spec therefore declares its concurrency profile, right after Fixtures.

```markdown
## Concurrency

- Mutates: Postgres `chat_history` (user_id=canary), Redis `chat:canary:*`, vector collection `documents` (filter user_id=canary), object bucket `local/uploads/canary/`.
- Conflicts with: any other test that mutates the same resources for the same user or partition.
- Serial: false
```

Field semantics:

- `Mutates:` every backing-service resource the test writes, deletes, or invalidates. Name the table, collection, bucket
  or key prefix, and the partition (user id, tenant id) where one applies. Read-only probes do not count.
- `Conflicts with:` usually derived from `Mutates:` overlap. Name an explicit conflict when it is not visible from
  resources alone, such as "any test that triggers a process restart". Most specs leave this as the generic overlap
  sentence.
- `Serial:` set `true` when the test cannot run alongside any other test at all: schema migrations, full-stack restarts,
  licence-server interactions, anything touching global config.

---

### Scheduling around conflicts

1. Read each spec's `Mutates:` set and `Serial:` flag.
2. Build a conflict graph. Two tests conflict when their `Mutates:` sets intersect, when either names the other under
   `Conflicts with:`, or when either is `Serial: true`.
3. Schedule. Tests with no edge to a running test start immediately, up to the confirmed cap. Tests with an edge queue
   until their conflicting tests finish. A `Serial: true` test drains all in-flight runners, runs alone, and then
   parallel scheduling resumes.
4. Aggregate normally once everything completes.

Conflict analysis only ever lowers concurrency. The confirmed cap remains the ceiling.

---

### Mark conservatively

False-positive serialisation costs minutes. False-negative parallelism corrupts results, forces a re-run, and opens a
debugging session to work out which test wrote the wrong byte. The asymmetry favours over-declaring `Mutates:` and
accepting the occasional unnecessary wait.

A test that "passes locally but fails in the sweep" is almost always a missing `Mutates:` declaration, in that test or
in a neighbour scheduled alongside it. The fix is to add the resource to the spec's Concurrency section, never to add a
sleep to the test.

Declaring `Mutates:` does not relieve a test of its own Reset responsibility. The Concurrency section tells the
orchestrator how to schedule. The Reset section still owns clearing the state before the Run step.

---

### What the main session never does

- Read prerequisite output and tick boxes itself. That is the runner's job.
- Invoke an API client directly during a sweep.
- Edit a spec or a tasks-template mid-sweep, even after a failure. Specs are immutable.
- Exceed the confirmed cap because the sweep is taking a while. Queue the overflow.
