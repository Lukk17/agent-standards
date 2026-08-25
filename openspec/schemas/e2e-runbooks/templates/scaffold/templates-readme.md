# e2e run-record templates

One `<N>-<capability>-tasks.template.md` per spec. Each is the **checkbox template** the runner copies into `../runs/`
at the start of every execution.

## Relationship to the specs

The specs themselves (`../<N>-<capability>-test.md`) live one level up, directly under `testing/`. This `templates/`
directory holds only the run-record templates that mirror them — one template per spec, sharing the same `{N}` prefix
and `{capability}` name.

## Contract

1. Templates are **immutable** between runs. The runner never edits them in place.
2. Each template mirrors its spec's Prerequisites, Reset, Run, and Expected items as checkboxes, plus a Verdict
   checkbox, a Result summary block (Input tokens, Output tokens, Start (UTC), End (UTC), Duration), and an
   "Additional tasks I did" section.
3. To run a test, copy the matching template into `../runs/` with a UTC-timestamp prefix
   (`<UTC-timestamp>_<N>-<capability>-tasks.md`), then tick boxes and fill results in that copy — never here.

See [../runs/README.md](../runs/README.md) for the full runner contract.
