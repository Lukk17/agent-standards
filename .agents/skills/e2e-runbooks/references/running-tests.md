# Running Tests

Contents:

- [Runs directory contract](#runs-directory-contract)
- [Runner contract](#runner-contract)
- [Sweeps](#sweeps)
- [Startup readiness](#startup-readiness)

Companion reference for the [e2e-runbooks](../SKILL.md) skill. Load it when naming a run record, executing a spec as the runner, delegating a sweep to subagents, or checking the startup readiness banner at sweep start.

---

### Runs directory contract

Name each run record with the sweep timestamp and the spec it came from. Use ISO-8601 with colons replaced by hyphens so
the filename is safe on Windows, macOS and Linux.

```text
YYYY-MM-DDTHH-MM-SS_1-weather-mcp-tasks.md
YYYY-MM-DDTHH-MM-SS_2-image-description-tasks.md
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
sweep timestamp, and fans out one `e2e-runner` subagent per spec, refilling the
in-flight slots as verdicts return. Isolated context per test, per-test token accounting, and failure isolation are what
the fan-out buys.

The default parallel cap is 5, confirmed with the user before each sweep, and conflicting tests serialise below it. The
reasoning behind the cap, the concurrency declaration format, and the scheduling algorithm are in
[orchestration.md](orchestration.md).

The main session never reads prerequisite output and ticks boxes itself, never invokes an API client directly during a
sweep, never edits a spec mid-sweep, and never exceeds the confirmed cap. A single test being debugged can be run
inline, since the subagent layer exists for fan-out.

---

### Startup readiness

When the service uses the startup-readiness banner from `observability-and-logging`, the banner's external dependency
section is the first stop when a prerequisite check fails. Check it once at sweep start: a `[FAILED]` row names the
dependency to fix, and there is no point running tests against a half-up stack.
