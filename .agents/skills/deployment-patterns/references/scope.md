# Scope

Companion reference for the [deployment-patterns](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Setting up or reviewing a CI/CD pipeline.
- Choosing a rollout strategy, or adding a canary or blue-green path.
- Adding health checks, probes, or a readiness gate to a deployment.
- Finding out why a merge to `main` deployed straight to production.
- Handling environment configuration and validating it at startup.
- Planning or rehearsing a rollback.
- Preparing a service for its first production release.
- The user says "set up a CI/CD pipeline", "add a canary rollout" or "how do we roll this back".

---

### When not to activate

- Writing the Dockerfile or the Compose file, use `docker-patterns`.
- Configuring the hosts underneath, use `ansible`.
- Instrumenting the application with logs, metrics, and traces, use `observability-and-logging`.
- Planning a schema change that has to survive the rollout, use `database-migrations`.
- Reviewing the application's own auth and input handling, use `application-security-review`.
- Secret scanning and dependency scanning inside the pipeline, use `application-security-review`.

---

### Related skills

- `docker-patterns` for the image this pipeline builds, scans, and signs.
- `observability-and-logging` for the health, metrics, and readiness signals the probes read.
- `database-migrations` for schema changes that must survive a rolling deployment.
- `ansible` for configuring the hosts under the cluster.
- `application-security-review` before a release touching auth, payments, or personal data.
