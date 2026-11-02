# Deployment rules with examples

Open this for the strategy table, the Pass and Fail form, and the reasoning behind any rule in [SKILL.md](../SKILL.md).

---

### Contents

- [Choose the rollout strategy on purpose](#choose-the-rollout-strategy-on-purpose)
- [Merging to main never deploys to production](#merging-to-main-never-deploys-to-production)
- [Build the image through docker-patterns](#build-the-image-through-docker-patterns)
- [Least privilege in CI](#least-privilege-in-ci)
- [Health checks that answer different questions](#health-checks-that-answer-different-questions)
- [Configuration from the environment, validated at startup](#configuration-from-the-environment-validated-at-startup)
- [Rollback is a rehearsed path](#rollback-is-a-rehearsed-path)
- [Kubernetes defaults](#kubernetes-defaults)

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
every job. A compromised third-party action inherits whatever the job holds, and a tag pin lets a moved tag swap the
code under you, so pin every action to a commit SHA.

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
automation are in [references/github-actions.md](github-actions.md).

---

### Health checks that answer different questions

Expose a liveness endpoint that touches nothing and a readiness endpoint that reports what this instance needs to
serve, as the readiness rule in `observability-and-logging` defines it, so a shared dependency stays out of it. Then
wire three probes to them. The paths are the ones `api-design` defines, `/health` and `/ready`, so use them rather than a local
variant. Pointing liveness at a dependency-checking endpoint turns a database blip into a cluster-wide restart storm.

Pass:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 3000
readinessProbe:
  httpGet:
    path: /ready
    port: 3000
```

Fail:

```yaml
livenessProbe:
  httpGet:
    path: /health/detailed
    port: 3000
```

This skill owns the probe manifests. Probe timings, the `startupProbe`, and what each one does to a pod are in
[references/kubernetes.md](kubernetes.md). What the endpoints should report is owned by
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
  DATABASE_URL: z.url(),
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
[references/kubernetes.md](kubernetes.md).
