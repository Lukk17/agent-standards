# e2e testing guide

Self-contained walkthroughs that an AI agent (or a human) can execute end-to-end against a live stack. Each
`<N>-<capability>-test.md` spec in this directory drives one capability through its API client invocation, with
explicit prerequisite checks, reset commands, run steps, and expected outcomes. The paired run-record templates live
in the `templates/` subdirectory; executed run records land in `runs/`.

## Format

Every `<N>-<capability>-test.md` file is the **immutable spec** for one test and uses the same fixed template.

1. **What this verifies.** Bullet list of behaviours.
2. **Prerequisites.** Concrete check commands the runner executes before starting. Each command is its own code
   block; the prose around it states what success looks like.
3. **Reset state.** One command per code block, executed in order, to wipe state so the test is reproducible. Use
   "None. This test does not write persisted state." if applicable.
4. **Run.** One or more numbered steps. Each step is a single API client invocation. Steps wait for a success
   response before continuing.
5. **Expected.** Observable-behaviour assertions verified after each step: HTTP status codes, response body shape
   and content, persisted state. NOT log substrings.
6. **Fixtures.** Paths to local files the test reads.

Each spec has a matching `<N>-<capability>-tasks.template.md` in the `templates/` subdirectory — the **checkbox
template** for a run. The runner never edits the spec or the template directly. Before starting a run, it copies the
template from `templates/` into `runs/` with a timestamped filename, ticks boxes as it progresses, fills in Result
summary and Verdict, and logs anything done outside the spec under "Additional tasks I did". See
[runs/README.md](runs/README.md) for the full runner contract.

## Test order

Numbered by setup cost (lowest first). Run earliest first when stepping through; each is self-contained so any can
be run on its own.

## Cross-cutting conventions

Pass criteria are observable behaviour only: HTTP status, response body content, persisted state in backing
services. Logs are diagnostic, not authoritative. Log lines drift across versions and aren't visible from every
runner's shell. If a behaviour assertion fails, a tail of the service log is the next diagnostic step, not a pass
criterion.

## Adding a new test

If OpenSpec is set up, run `openspec new change "add-<capability>-test" --schema e2e-runbooks` (or `/opsx:propose`
when `default_schema: e2e-runbooks` is configured). Otherwise hand-write the spec + tasks-template pair following the
methodology in the companion skill.
