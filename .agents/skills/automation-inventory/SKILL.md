---
name: automation-inventory
description: 'Evidence-first inventory of every live automation: scheduled jobs, hooks, CI workflows, connectors, MCP servers and wrapper scripts, each classified as configured, authenticated, verified, stale or missing, and each claim backed by a command and its output. Use when you say "what automations do I have", "what is actually running", "which of these jobs is broken", or "audit our tooling before we fix anything". Not for operating one CI system, use `github-ops`.'
---

# Automation Inventory

An audit method for answering what automation exists in a project, what state each piece is in, and which pieces
should be kept, merged, cut or fixed next. It produces an evidence table before it produces an opinion, so no
recommendation rests on a config file that merely mentions a tool.

---

### When to activate

- The user asks what automations exist, what is live, what is broken, or what overlaps
- Work spans more than one automation surface at once, for example cron plus CI plus local hooks
- Automation was ported from another system and nobody knows which parts survived the move
- Several mechanisms do the same job and the user wants one canonical lane
- Before any cleanup, consolidation or removal of automation

---

### When not to activate

- Operating a single CI provider, triaging its runs or preparing a release, use `github-ops`
- Designing the deployment pipeline itself rather than surveying what exists, use `deployment-patterns`
- Investigating a single failing test or job as a bug, use `ai-regression-testing` or the project test skill
- Reviewing the code an automation runs rather than the automation wiring, use `code-reviewer`
- Adding logging, metrics or alerting to automation you already trust, use `observability-and-logging`

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

Problem types: active breakage, authentication outage, stale status, overlap, missing capability.

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

### Report as one evidence table, then one recommendation per item

The table is the deliverable. Each row carries the automation, where it is defined, its live state, and the proof.
Recommendations come after the table and each one is a single word, so the user can act on the list without
interpreting a paragraph.

A filled example:

| Automation | Source | Live state | Proof | Call |
|---|---|---|---|---|
| Nightly backup timer | `/etc/systemd/system/backup.timer` | verified | `systemctl list-timers backup` shows next run in 6h, last run OK | keep |
| CI test workflow | `.github/workflows/ci.yml` | verified | `gh run list --workflow ci.yml` shows 5 of 5 success | keep |
| Pre-commit lint hook | `.git/hooks/pre-commit` | stale | Calls `npx eslint`, `npx eslint --version` exits 127, package removed | fix next |
| Legacy deploy script | `scripts/deploy.sh` | stale | No run in git log since the CI deploy job landed, same steps as `deploy.yml` | cut |
| Atlassian MCP server | `.mcp.json` | configured | Process starts, `atlassianUserInfo` returns 401, no token in environment | fix next |
| Secret scanning | none found | missing | No `gitleaks` config, no scanning workflow, no pre-push hook | fix next |

Every row ends in keep, merge, cut or fix next. No row ends in "investigate further" without a named next command.

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

---

### Related skills

- `github-ops` owns CI triage, issue and PR operations, and release preparation once the audit is done
- `deployment-patterns` owns designing the pipeline and rollout strategy for the automations you keep
- `observability-and-logging` owns the metrics, logs and alerts that keep a kept automation honest
- `docker-patterns` owns container and compose wiring when an automation runs in a container
- `security-review` owns the credential and permission review for any automation holding a secret
- `project-tracking` owns turning each fix-next call into a tracked work item

---

### Checklist

- [ ] The audit started read-only and changed nothing without a request
- [ ] Every automation surface was enumerated, not just the obvious one
- [ ] Each item carries exactly one live state and one problem type
- [ ] Each important claim cites a command and its output
- [ ] Presence in configuration was never reported as working
- [ ] The evidence table exists before any merge or delete recommendation
- [ ] Every row ends in keep, merge, cut or fix next
- [ ] Anything undetermined is named, with the command that would settle it
