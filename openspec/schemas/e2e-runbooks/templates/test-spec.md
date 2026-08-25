# {capability}: e2e test

## What this verifies

<!-- Bullet list. Copy from the proposal, verbatim. Behaviour-only
assertions. -->

-
-

## Prerequisites

<!-- Concrete check commands the runner executes before starting. Each command
in its own fenced block. Prose around the block states what success looks
like. -->

Check the API client tool is installed.

```bash
<command>
```

Expect <success criterion>.

<repeat per prereq>

## Reset state

<!-- One command per code block, in order, to wipe state so the test is
reproducible. Use "None. This test does not write persisted state." if so. -->

```bash
<command>
```

## Run

<!-- One or more numbered API-client CLI invocations. Multi-step tests
instruct the runner to wait for a success response (HTTP 200 or equivalent)
before continuing. -->

Send the request and wait for the response before moving to the Expected
section.

```bash
<command>
```

## Expected

<!-- Observable assertions only. HTTP status, response body content,
persisted state in backing services. No log substrings. -->

The output shows HTTP 200.

The response body's `<field>` contains <expected content>.

## Fixtures

<!-- Paths to local files the test reads. Each must have distinctive canary
content the model can't have memorised. "None." if none. -->

- `<path>` — <one-line description of the canary content>

## Concurrency

- **Mutates:** <copy the Mutates line verbatim from the proposal's Concurrency profile.>
- **Conflicts with:** <copy the Conflicts with line verbatim from the proposal's Concurrency profile.>
- **Serial:** <copy the Serial value verbatim from the proposal's Concurrency profile.>
