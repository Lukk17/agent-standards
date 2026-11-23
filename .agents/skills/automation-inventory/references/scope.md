# Scope

Companion reference for the [automation-inventory](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- The user asks what automations exist, what is live, what is broken, or what overlaps
- Work spans more than one automation surface at once, for example cron plus CI plus local hooks
- Automation was ported from another system and nobody knows which parts survived the move
- Several mechanisms do the same job and the user wants one canonical lane
- Before any cleanup, consolidation or removal of automation
- The user says "what automations do I have", "what is actually running", "which of these jobs is broken", "audit our tooling" or "audit our tooling before we fix anything"

---

### When not to activate

- Operating a single CI provider, triaging its runs or preparing a release, use `github-ops`
- Designing the deployment pipeline itself rather than surveying what exists, use `deployment-patterns`
- Finding why a single CI job fails, use `github-ops`, then `ai-regression-testing` to add the regression test
- Reviewing the code an automation runs rather than the automation wiring, use `code-reviewer`
- Adding logging, metrics or alerting to automation you already trust, use `observability-and-logging`

---

### Related skills

- `github-ops` owns CI triage, issue and PR operations, and release preparation once the audit is done
- `deployment-patterns` owns designing the pipeline and rollout strategy for the automations you keep
- `observability-and-logging` owns the metrics, logs and alerts that keep a kept automation honest
- `docker-patterns` owns container and compose wiring when an automation runs in a container
- `application-security-review` owns the credential and permission review for any automation holding a secret
- `project-tracking` owns turning each fix-next call into a tracked work item
