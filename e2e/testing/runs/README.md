# e2e test runs

Each e2e test run drops a filled-in copy of the matching `*-tasks.template.md` here, named
`<UTC-timestamp>_<N>-<capability>-tasks.md`. This README is tracked. The run files themselves are gitignored by
default.

---

### Contract

1. Specs, `../<N>-<capability>-test.md`, are immutable between runs. The runner never edits them.
2. Templates, `../templates/<N>-<capability>-tasks.template.md`, are also immutable. They define the checkbox list
   for that test.
3. Each run starts by copying the relevant template from `../templates/` into this directory with a UTC timestamp
   prefix. The runner ticks boxes as it completes each step and fills in Result summary and Additional tasks I did at
   the end.

---

### Naming

```text
2026-08-25T18-15-00_1-project-gate-decisions-tasks.md
2026-08-25T18-15-00_2-project-import-shape-tasks.md
2026-08-25T18-15-00_6-global-install-shape-tasks.md
```

Use ISO-8601 UTC with colons replaced by hyphens so the filename is filesystem-safe across Windows, macOS, and Linux.
Group every test from one sweep under the same timestamp: one timestamp is one full e2e sweep.

---

### Runner steps

1. Read the spec for the test.
2. Copy the template from `../templates/` into this directory with a timestamped filename.
3. Record `Start (UTC)` as the very first action, the wall-clock instant before the prerequisite checks begin.
4. Execute each task in order. Tick the box on success, record what went wrong on failure.
5. After the Verdict line is decided, record `End (UTC)`, the wall-clock instant after the last verification step.
6. Compute `Duration = End - Start` and record it as `HH:MM:SS`. This is wall-clock for the whole test, prerequisites
   and reset and run and verify together, not just the command under test.
7. Fill Input tokens and Output tokens with your best estimate of the model tokens consumed across the run. Leave
   blank if you cannot get exact numbers. Do not invent.
8. Write the Result summary paragraph and the Verdict, PASS or FAIL.
9. If any step was done outside the spec, extra diagnostics or retries or manual inspection, log it under Additional
   tasks I did.

---

### Record the versions

Every container run prints the resolved version of each of the five agent command-line tools before it does anything
else. Paste that table into the Additional tasks I did section of the run record. It is the line to quote when a
result needs reproducing, because the harness pins no versions and re-resolves every tool to its newest release on
container start.

---

### Gitignore policy

Run record files are ephemeral by default and gitignored. This README stays tracked. Promote individual runs to a
committed audit trail by moving them under `runs/<YYYY-MM>/` subfolders and adjusting the gitignore exception.
