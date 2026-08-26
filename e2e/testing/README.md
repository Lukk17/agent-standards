# e2e testing guide

Self-contained walkthroughs that an AI agent or a human executes end-to-end against the container sandbox. Each
`<N>-<capability>-test.md` spec in this directory drives one capability, with explicit prerequisite checks, reset
commands, run steps, and expected outcomes. The paired run-record templates live in [templates/](templates/README.md),
and executed run records land in [runs/](runs/README.md).

---

### Format

Every `<N>-<capability>-test.md` file is the immutable spec for one test and uses the same seven sections, in this
order, every time.

1. What this verifies. Bullet list of behaviours.
2. Prerequisites. Concrete check commands the runner executes before starting. Each command is its own code block,
   and the prose around it states what success looks like.
3. Reset state. One command per code block, executed in order, so the run is reproducible. "None." when the test
   writes no state.
4. Run. Numbered steps, one invocation each. A step waits for the previous one to succeed before it starts.
5. Expected. Observable-behaviour assertions verified after the run steps. Exit codes, listing output, gate
   decisions. Never log substrings.
6. Fixtures. Paths to the files the test reads.
7. Concurrency. `Mutates`, `Conflicts with`, and `Serial`, read by the orchestrator before it decides what runs in
   parallel.

Each spec has a matching `<N>-<capability>-tasks.template.md` in [templates/](templates/README.md), which is the
checkbox template for a run. The runner never edits the spec or the template. It copies the template into
[runs/](runs/README.md) with a timestamped filename, ticks boxes as it progresses, fills in Result summary and
Verdict, and logs anything done outside the spec under "Additional tasks I did".

---

### Local convention: assertions carry their command

The generic methodology puts prose in Expected and commands in Run. These suites put a fenced command block under
each Expected assertion as well, with the prose above it stating the success criterion. There are two reasons. Every
assertion here is a shell exit code rather than a field in an HTTP response, so the assertion is only unambiguous
when the exact command is written down. And the repository style rule gives every runnable command its own fenced
block on one physical line, which rules out burying a long check inside a sentence.

Read it as: run the block, then read `echo $?`, then compare against the criterion in the prose above the block.

---

### Test order

Numbered by setup cost, lowest first. Suite A, the per-project setup, is 1 to 5. Suite B, the global setup, is 6 to
9. They share one sequence because they share one runner and one container, and the second word of each filename says
which suite the spec belongs to.

| Spec | Suite | Setup cost class | What it costs |
| --- | --- | --- | --- |
| 1 | project | 1 | Container only. No import, no agent tool invoked |
| 2 | project | 2 | Container plus the full project import. Filesystem and config assertions only |
| 3 | project | 3 | Import plus four agent listing commands, each of which can take minutes |
| 4 | project | 3 | Import plus five MCP listings, plus a Codex trust record written into the container home |
| 5 | project | 4 | Import plus a probe subagent written into the imported project and deleted again |
| 6 | global | 4 | The whole documented global install into the container home, plus a second bare directory |
| 7 | global | 5 | Global install plus agent listing commands run from the bare directory |
| 8 | global | 5 | Global install plus five MCP listings run from the bare directory |
| 9 | global | 5 | Global install plus a probe subagent written into the global agent directory |

Each spec is self-contained: any one of them can be run on its own in a fresh container. Suite B specs 7, 8, and 9
reuse the install command list from spec 6 by reference rather than repeating it, so there is one copy of it to keep
correct.

---

### Cross-cutting conventions

Pass criteria are observable behaviour only: the exit code of a command, the names an agent's own listing command
prints, and the decision the preflight gate returns on stdout or through its exit status. Logs are diagnostic. Log
lines drift across versions and are not visible from every runner's shell, so no assertion reads one. When an
assertion fails, the next diagnostic step is a log tail, not a pass criterion.

Counts are never hard-coded. Where a spec compares a count, it compares against the same count derived from the
mounted repository at run time, so adding a skill or a subagent upstream never turns a spec stale.

Live model sessions need provider credentials, which the container never receives. Every spec restates this in its
own What this verifies section, because it bounds what a PASS verdict means.

---

### Adding a new test

With OpenSpec initialised, run `openspec new change "add-<capability>-test" --schema e2e-runbooks`, or `/opsx:propose`
when `default_schema: e2e-runbooks` is configured. Otherwise hand-write the spec and tasks-template pair following the
methodology in the [e2e-runbooks skill](../../.agents/skills/e2e-runbooks/SKILL.md).
