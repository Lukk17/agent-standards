# The Audit Steps in Full

Contents:

- [Start read-only](#start-read-only)
- [Inventory every surface before judging any of it](#inventory-every-surface-before-judging-any-of-it)
- [Classify each item by live state, not by presence](#classify-each-item-by-live-state-not-by-presence)
- [Prove every claim with a command and its output](#prove-every-claim-with-a-command-and-its-output)
- [Say what is ambiguous](#say-what-is-ambiguous)

Companion reference for the [automation-inventory](../SKILL.md) skill. Load it when a step needs its reasoning or its pass and fail example. The report step is in [evidence-table.md](evidence-table.md).

---

### Start read-only

Begin every audit in read-only mode and stay there until the user asks for fixes. An audit that repairs things as it
goes destroys the evidence of what the original state was, and the user loses the ability to decide whether a broken
job was worth keeping at all.

Pass:

```text
Read .github/workflows/, .git/hooks/, the MCP config files and the cron table. Report state. Ask before changing.
```

Fail:

```text
Found a broken workflow while listing them, fixed the YAML, carried on listing.
```

---

### Inventory every surface before judging any of it

List the whole surface first. A partial list makes overlap invisible, because the second mechanism that does the same
job is usually on the surface you skipped.

Cover at minimum: scheduled jobs and timers, git hooks and agent hooks, CI and CD workflows, MCP servers, external
connectors and app integrations, wrapper scripts and repository entry points, and notification routes.

Pass:

```text
Surfaces enumerated: cron, systemd timers, .git/hooks, agent hook config, CI workflows, MCP configs, wrapper scripts.
```

Fail:

```text
Listed the CI workflows, concluded the project has three automations.
```

---

### Classify each item by live state, not by presence

Presence in a config file is not evidence that anything runs. Give every item exactly one live state, then one
problem type, so the reader can sort the table without rereading the prose.

Live states: configured, authenticated, verified, stale, missing.

Problem types: active breakage, authentication outage, stale status, overlap, missing capability, or none for a
verified item with nothing wrong.

Pass:

```text
context7 MCP: configured, not authenticated. No API key in the process environment, server falls back to free tier.
```

Fail:

```text
context7 MCP: live. It is declared in the MCP config file.
```

---

### Prove every claim with a command and its output

A claim without a measurement is a guess. Name the exact thing the claim is about, run something that touches it, and
paste what came back. If the tool that would prove it is unavailable, say the claim is unverified and state your
confidence rather than presenting it as fact.

Pass:

```bash
gh run list --workflow ci.yml --limit 5 --json conclusion,createdAt
```

Fail:

```text
CI looks healthy, the workflow file has not changed in a while.
```

---

### Say what is ambiguous

An audit that hides its gaps is worse than a short one, because the reader treats the silence as a clean bill of
health. Name what you could not determine and what would settle it.

Pass:

```text
Unresolved: whether the staging deploy hook still fires. No run log is readable from here. Check with: gh run list --workflow deploy-staging.yml
```

Fail:

```text
Everything else appears to be working normally.
```
