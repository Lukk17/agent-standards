# Deployment rules with examples

Open this for the strategy table and the reasoning behind any rule in [SKILL.md](../SKILL.md). The pipeline is the control, not the documentation around it. The Pass and Fail code for each rule is in the file for its technology: [github-actions.md](github-actions.md) for the pipeline, [kubernetes.md](kubernetes.md) for the workload, and [zod.md](zod.md) for environment validation in a TypeScript service.

---

### Contents

- [Choose the rollout strategy on purpose](#choose-the-rollout-strategy-on-purpose)
- [Merging to main never deploys to production](#merging-to-main-never-deploys-to-production)
- [Build the image through docker-patterns](#build-the-image-through-docker-patterns)
- [Least privilege in CI](#least-privilege-in-ci)
- [Health checks that answer different questions](#health-checks-that-answer-different-questions)
- [Configuration from the environment, validated at startup](#configuration-from-the-environment-validated-at-startup)
- [Rollback is a rehearsed path](#rollback-is-a-rehearsed-path)
- [Workload defaults](#workload-defaults)

---

### Choose the rollout strategy on purpose

| Strategy | How it works | Cost | Use when |
|---|---|---|---|
| Rolling | Replace instances in batches, both versions live during the rollout | Requires backward-compatible changes | The default, for a backward-compatible change |
| Blue-green | Two identical environments, traffic switched atomically | Double the infrastructure during the switch | Critical services where rollback must be instant |
| Canary | A small traffic share on the new version first, widened on healthy metrics | Traffic splitting plus real metric gating | High traffic, or a change you do not fully trust |

Pass: a rolling update that cannot take the service below capacity, adding one new instance before it removes an old one.

Fail: a rollout that stops every old instance before it starts the new ones.

Rolling means two versions run at once, so the change has to be backward compatible with the previous version and with the database schema it is running against. If it is not, the strategy is blue-green, not rolling.

The Kubernetes form, `maxUnavailable: 0` and `maxSurge: 1` and never `Recreate`, is in [kubernetes.md](kubernetes.md#rolling-update-strategy).

---

### Merging to main never deploys to production

A merge may build the image, deploy to staging, and run smoke tests automatically. Promotion to production is a separate, explicitly approved step: a protected environment with required reviewers, or a manually triggered run.

A gate that is only named in the pipeline gates nothing. It gates once the environment carries its required-reviewer protection rule, so configure that rule first.

The pipeline shape is: pull request runs lint, typecheck, unit tests, integration tests, and a preview deploy. Merge runs the same set plus image build, staging deploy, and smoke tests. Then the gate. Then production.

The GitHub Actions form, `environment: production` with a protection rule or a manual `workflow_dispatch`, is in [github-actions.md](github-actions.md#the-production-gate).

---

### Build the image through docker-patterns

Image construction, base image pinning, the non-root user, and the Trivy, SBOM, and cosign supply-chain gate are owned by `docker-patterns` and are not restated here. The pipeline's job is to invoke them and to fail on their findings.

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

Authenticate to a cloud provider with OIDC, never a stored long-lived key, and declare the minimum permissions on every job. A compromised third-party pipeline step inherits whatever the job holds, and a tag pin lets a moved tag swap the code under you, so pin every third-party step to a commit SHA, with its exact release tag in a trailing comment.

Pin the rest the same way: the runner to a fixed label, because a moving label swaps the image and the toolchain without a commit in your repository, and every image to a tag plus digest. Bumps are manual pull requests, not a bot's.

The GitHub Actions form of each, with the command that resolves a SHA, the full reference pipeline, the OIDC exchange, `actionlint`, failure notifications, matrix rules, and the canary automation, is in [github-actions.md](github-actions.md).

---

### Health checks that answer different questions

Expose a liveness endpoint that touches nothing and a readiness endpoint that reports what this instance needs to serve, as the readiness rule in `observability-and-logging` defines it, so a shared dependency stays out of it. Then wire three probes to them. The paths are the ones `api-design` defines, `/health` and `/ready`, so use them rather than a local variant. Pointing liveness at a dependency-checking endpoint turns a database blip into a cluster-wide restart storm.

This skill owns the probe manifests. The Pass and Fail manifests, probe timings, the `startupProbe`, and what each one does to a pod are in [kubernetes.md](kubernetes.md#probes). What the endpoints should report is owned by `observability-and-logging`.

---

### Configuration from the environment, validated at startup

Every environment-varying value comes from an environment variable, and the process validates the whole set before it serves a request. A missing or malformed value should kill the process at boot, not surface as a 500 an hour later.

Pass: one schema parses the whole environment at startup, and a missing or malformed value kills the process at boot.

Fail: each value is read where it is used, with a silent fallback or an unchecked assertion.

The TypeScript form is in [zod.md](zod.md).

Secrets are injected by a secrets manager at runtime, never committed and never baked into an image.

---

### Rollback is a rehearsed path

Every release has a way back that someone has actually executed. The pipeline owns it so it takes seconds and leaves a record.

Fail:

```bash
git revert HEAD && git push
```

Reverting and rebuilding is not a rollback, it is another deployment with the same lead time as the one that broke. The Kubernetes rollback command is in [kubernetes.md](kubernetes.md#rollback). Before a release, confirm all of it:

- The previous image or artefact is still available and tagged.
- The database migration is backward compatible, with no destructive change, so the previous version still runs.
- New behaviour is behind a feature flag that can be turned off without a deploy.
- Alerts on error rate will fire before a user reports it.
- The rollback has been executed in staging, not just written down.

---

### Workload defaults

Every production workload runs as a non-root user on a read-only root filesystem, with no privilege escalation and every capability dropped. It carries a disruption budget, a default-deny network policy, resource requests and limits, and autoscaling with a minimum of two replicas. Enforce them when the workload is admitted to the cluster rather than at review time.

The manifests for each of those, the policy engines that enforce them, and the Helm chart standards are in [kubernetes.md](kubernetes.md).
