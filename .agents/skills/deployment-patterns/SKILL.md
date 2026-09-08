---
name: deployment-patterns
description: Deployment and CI/CD standards covering rolling, blue-green and canary rollouts, an approval gate before production, GitHub Actions with OIDC and least-privilege permissions, health probes, config validation, rollback, and Kubernetes defaults. Use when you say "set up a CI/CD pipeline", "add a canary rollout", "why did merging to main deploy to prod", "add readiness and liveness probes", or "how do we roll this back". Not for writing the Dockerfile itself, use `docker-patterns`.
---

# Deployment Patterns

How a change reaches production without a surprise: a rollout strategy chosen on purpose, an explicit human gate in
front of production, config validated before the process serves traffic, and a rollback that has been rehearsed. The
pipeline is the control, not the documentation around it.

Baseline: GitHub Actions on `ubuntu-latest`, Kubernetes 1.34, and Helm 4 (both verified locally). Every GitHub
Action referenced here is pinned to its current major.

---

### When to activate

- Setting up or reviewing a CI/CD pipeline.
- Choosing a rollout strategy, or adding a canary or blue-green path.
- Adding health checks, probes, or a readiness gate to a deployment.
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

---

### Choose the rollout strategy on purpose

| Strategy | How it works | Cost | Use when |
|---|---|---|---|
| Rolling | Replace instances in batches, both versions live during the rollout | Requires backward-compatible changes | The default, for a backward-compatible change |
| Blue-green | Two identical environments, traffic switched atomically | Double the infrastructure during the switch | Critical services where rollback must be instant |
| Canary | A small traffic share on the new version first, widened on healthy metrics | Traffic splitting plus real metric gating | High traffic, or a change you do not fully trust |

Pass, a rolling update that cannot take the service below capacity:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0
    maxSurge: 1
```

Fail:

```yaml
strategy:
  type: Recreate
```

Rolling means two versions run at once, so the change has to be backward compatible with the previous version and
with the database schema it is running against. If it is not, the strategy is blue-green, not rolling.

---

### Merging to main never deploys to production

A merge may build the image, deploy to staging, and run smoke tests automatically. Promotion to production is a
separate, explicitly approved step: a GitHub environment protection rule with required reviewers, or a manually
triggered `workflow_dispatch` run.

Pass:

```yaml
deploy-production:
  needs: smoke-test
  environment: production
```

Fail:

```yaml
deploy-production:
  needs: build
  if: github.ref == 'refs/heads/main'
```

The failing version has no gate at all. The passing version only gates once the `production` environment carries a
required-reviewer protection rule, so configure that rule and treat the `environment:` key as the hook into it.

The pipeline shape is: pull request runs lint, typecheck, unit tests, integration tests, and a preview deploy. Merge
runs the same set plus image build, staging deploy, and smoke tests. Then the gate. Then production.

---

### Build the image through docker-patterns

Image construction, base image pinning, the non-root user, and the Trivy, SBOM, and cosign supply-chain gate are
owned by `docker-patterns` and are not restated here. The pipeline's job is to invoke them and to fail on their
findings.

Pass:

```bash
trivy image --exit-code 1 --severity CRITICAL,HIGH "ghcr.io/org/app:${GITHUB_SHA}"
```

Fail:

```bash
trivy image "ghcr.io/org/app:${GITHUB_SHA}" || true
```

---

### Least privilege in CI

Authenticate to a cloud provider with OIDC, never a stored long-lived key, and declare the minimum permissions on
every job. A compromised third-party action inherits whatever the job holds.

Pass:

```yaml
permissions:
  contents: read
  id-token: write
```

Fail:

```yaml
permissions: write-all
```

The full reference pipeline, the OIDC exchange, `actionlint`, failure notifications, matrix rules, and the canary
automation are in [references/github-actions.md](references/github-actions.md).

---

### Health checks that answer different questions

Expose a liveness endpoint that touches nothing and a readiness endpoint that verifies dependencies, then wire three
probes to them. Pointing liveness at a dependency-checking endpoint turns a database blip into a cluster-wide
restart storm.

Pass:

```yaml
livenessProbe:
  httpGet:
    path: /health/liveness
    port: 3000
readinessProbe:
  httpGet:
    path: /health/readiness
    port: 3000
```

Fail:

```yaml
livenessProbe:
  httpGet:
    path: /health/detailed
    port: 3000
```

Probe timings, the `startupProbe`, and what each one does to a pod are in
[references/kubernetes.md](references/kubernetes.md). What the endpoints should report is in
`observability-and-logging`.

---

### Configuration from the environment, validated at startup

Every environment-varying value comes from an environment variable, and the process validates the whole set before
it serves a request. A missing or malformed value should kill the process at boot, not surface as a 500 an hour
later.

Pass:

```typescript
const envSchema = z.object({
  NODE_ENV: z.enum(["development", "staging", "production"]),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
});

export const env = envSchema.parse(process.env);
```

Fail:

```typescript
const port = Number(process.env.PORT) || 3000;
const dbUrl = process.env.DATABASE_URL!;
```

Secrets are injected by a secrets manager at runtime, never committed and never baked into an image.

---

### Rollback is a rehearsed path

Every release has a way back that someone has actually executed. The pipeline owns it so it takes seconds and leaves
a record.

Pass:

```bash
kubectl rollout undo deployment/app
```

Fail:

```bash
git revert HEAD && git push
```

Reverting and rebuilding is not a rollback, it is another deployment with the same lead time as the one that broke.
Before a release, confirm all of it:

- The previous image or artefact is still available and tagged.
- The database migration is backward compatible, with no destructive change, so the previous version still runs.
- New behaviour is behind a feature flag that can be turned off without a deploy.
- Alerts on error rate will fire before a user reports it.
- The rollback has been executed in staging, not just written down.

---

### Kubernetes defaults

Every production workload carries a non-root security context, a PodDisruptionBudget, a default-deny NetworkPolicy
in its namespace, resource requests and limits, and an HPA with a minimum of two replicas. Enforce them at admission
with Kyverno or OPA Gatekeeper rather than at review time.

Pass:

```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]
```

Fail:

```yaml
securityContext: {}
```

The manifests for each of those, plus Helm chart standards, are in
[references/kubernetes.md](references/kubernetes.md).

---

### Reference files

| Open this | For |
|---|---|
| [references/github-actions.md](references/github-actions.md) | The full reference pipeline, OIDC, job permissions, actionlint, failure alerts, matrix builds, and canary automation |
| [references/kubernetes.md](references/kubernetes.md) | Probes, pod security context, PDB, NetworkPolicy, HPA, ResourceQuota and LimitRange, ServiceMonitor, policy enforcement, and Helm |
| [references/cloud-and-operations.md](references/cloud-and-operations.md) | IAM, network isolation, Terraform state, tagging, cost controls, audit posture, disaster recovery, and the production readiness checklist |

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
