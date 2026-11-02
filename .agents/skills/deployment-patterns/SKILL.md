---
name: deployment-patterns
description: Deployment and CI/CD standards for rolling, blue-green and canary rollouts, a production approval gate, GitHub Actions with OIDC and least privilege, health probes, config validation, rollback and Kubernetes defaults. Use when the user says "set up a CI/CD pipeline", "add a canary rollout" or "how do we roll this back". Not for writing the Dockerfile itself, use `docker-patterns`.
---

# Deployment Patterns

How a change reaches production without a surprise: a rollout strategy chosen on purpose, an explicit human gate in front of production, config validated before the process serves traffic, and a rehearsed rollback. The pipeline is the control, not the documentation around it.

Written for GitHub Actions on `ubuntu-latest`, Kubernetes 1.37 and Helm 4. Every GitHub Action a project runs is pinned to a full commit SHA with its version tag in a trailing comment, such as `uses: actions/checkout@<commit-sha> # v5`, and every image to a tag plus digest. The examples use placeholders rather than real values, and [references/github-actions.md](references/github-actions.md) shows how to resolve them.

| Task | Open |
|---|---|
| The strategy table, the Pass and Fail form, and the reasoning behind any rule below | [references/rules-and-examples.md](references/rules-and-examples.md) |
| The full reference pipeline, OIDC, job permissions, actionlint, failure alerts, matrix builds, and canary automation | [references/github-actions.md](references/github-actions.md) |
| Probes, pod security context, PDB, NetworkPolicy, HPA, ResourceQuota and LimitRange, ServiceMonitor, policy enforcement, and Helm | [references/kubernetes.md](references/kubernetes.md) |
| IAM, network isolation, Terraform state, tagging, cost controls, audit posture, disaster recovery, and the production readiness checklist | [references/cloud-and-operations.md](references/cloud-and-operations.md) |

---

### When to activate

- Setting up or reviewing a CI/CD pipeline.
- Choosing a rollout strategy, or adding a canary or blue-green path.
- Adding health checks, probes, or a readiness gate to a deployment.
- Finding out why a merge to `main` deployed straight to production.
- Handling environment configuration and validating it at startup.
- Planning or rehearsing a rollback.
- Preparing a service for its first production release.

---

### When not to activate

- Writing the Dockerfile or the Compose file, use `docker-patterns`.
- Configuring the hosts underneath, use `ansible`.
- Instrumenting the application with logs, metrics, and traces, use `observability-and-logging`.
- Planning a schema change that has to survive the rollout, use `database-migrations`.
- Reviewing the application's own auth and input handling, use `security-review`.
- Secret scanning and dependency scanning inside the pipeline, use `security-review`.

---

### Rules

1. Choose the rollout on purpose. Rolling replaces instances in batches and is the default for a backward-compatible change, with `maxUnavailable: 0` and `maxSurge: 1`, never `Recreate`.
2. Rolling runs two versions at once, so the change must be backward compatible with the previous version and its database schema. If not, use blue-green: two identical environments, traffic switched atomically, for critical services needing instant rollback.
3. Canary puts a small traffic share on the new version first and widens it on healthy metrics, for high traffic or a change you do not fully trust. It costs traffic splitting plus real metric gating.
4. A merge to `main` never deploys to production. It may build, deploy to staging and run smoke tests, then production is a separate approved step: an `environment: production` with a required-reviewer protection rule, or a manual `workflow_dispatch`. The `environment:` key gates nothing until that rule exists.
5. Pipeline shape: a pull request runs lint, typecheck, unit and integration tests and a preview deploy. Merge runs the same plus image build, staging deploy and smoke tests. Then the gate, then production.
6. Image build, base pinning, the non-root user and the Trivy, SBOM and cosign gate belong to `docker-patterns`. The pipeline invokes them and fails on their findings, never with `|| true`.
7. Authenticate to a cloud with OIDC, never a stored long-lived key, and declare minimum `permissions` on every job, never `write-all`, because a compromised action inherits what the job holds. Pin every action to a commit SHA, since a moved tag swaps the code.
8. Liveness touches nothing and readiness reports what this instance needs to serve, per `observability-and-logging`, keeping shared dependencies out. Use the `api-design` paths `/health` and `/ready`. Liveness on a dependency-checking endpoint turns a database blip into a restart storm.
9. This skill owns the probe manifests. Probe timings and the `startupProbe` are in the Kubernetes reference, and what the endpoints report is owned by `observability-and-logging`.
10. Every environment-varying value comes from an environment variable, and the process validates the whole set against a schema before serving, so a missing value kills it at boot rather than surfacing as a 500 later.
11. Secrets are injected by a secrets manager at runtime, never committed and never baked into an image.
12. Rollback is a rehearsed pipeline path such as `kubectl rollout undo`. Revert-and-rebuild is another deployment with the same lead time as the one that broke.
13. Before a release confirm: the previous artefact is still available and tagged, the migration is backward compatible with no destructive change, new behaviour is behind a flag that turns off without a deploy, error-rate alerts fire before a user reports, and the rollback ran in staging.
14. Every production workload carries a non-root, read-only, no-escalation, `drop: [ALL]` security context, a PodDisruptionBudget, a default-deny NetworkPolicy in its namespace, requests and limits, and an HPA with at least two replicas, enforced at admission with Kyverno or OPA Gatekeeper.

---

### Related skills

- `docker-patterns` for the image this pipeline builds, scans, and signs.
- `observability-and-logging` for the health, metrics, and readiness signals the probes read.
- `database-migrations` for schema changes that must survive a rolling deployment.
- `ansible` for configuring the hosts under the cluster.
- `security-review` before a release touching auth, payments, or personal data.

---

### Checklist

- [ ] The rollout strategy is chosen deliberately and the change is compatible with it.
- [ ] Nothing promotes to production without an explicit approval gate.
- [ ] The image is built, scanned, and signed through `docker-patterns`, and the pipeline fails on findings.
- [ ] Cloud authentication uses OIDC, no long-lived key in CI secrets.
- [ ] Every job declares minimum permissions, no `write-all`.
- [ ] Liveness and readiness are separate endpoints, liveness touches no dependency.
- [ ] All configuration comes from the environment and is validated at startup.
- [ ] Secrets are injected at runtime by a secrets manager.
- [ ] The rollback path has been executed in staging.
- [ ] Migrations in the release are backward compatible with the previous version.
- [ ] Production workloads carry a security context, a PDB, a NetworkPolicy, limits, and an HPA.
- [ ] The production readiness checklist in the cloud reference has been walked.
