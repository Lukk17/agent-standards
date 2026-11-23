---
name: deployment-patterns
description: 'Deployment and CI/CD: rolling, blue-green and canary rollouts, a production gate, rollback. Use when the user says "set up a CI/CD pipeline" or "how do we roll this back". Not for Dockerfiles, use `docker-patterns`.'
metadata:
  version: "1.1.0"
---

# Deployment Patterns

How a change reaches production without a surprise: a rollout strategy chosen on purpose, an explicit human gate in front of production, config validated before the process serves traffic, and a rehearsed rollback.

Written for GitHub Actions, Kubernetes 1.37 and Helm 4.

| Task | Open |
|---|---|
| The strategy table or the reasoning behind a rule | [rules-and-examples.md](references/rules-and-examples.md) |
| The pipeline is GitHub Actions | [github-actions.md](references/github-actions.md) |
| The workload runs on Kubernetes or Helm | [kubernetes.md](references/kubernetes.md) |
| A TypeScript service validates its environment with Zod | [zod.md](references/zod.md) |
| Cloud accounts: IAM, networks, Terraform state, tagging, cost, audit, disaster recovery, production readiness | [cloud-and-operations.md](references/cloud-and-operations.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a change done, and before a release | [checklist.md](references/checklist.md) |

---

### When not to activate

- Writing the Dockerfile or the Compose file, use `docker-patterns`.
- Planning a schema change that has to survive the rollout, use `database-migrations`.
- Secret and dependency scanning inside the pipeline, or the application's own auth and input handling, use `application-security-review`.

---

### Rules

1. Choose the rollout on purpose. Rolling, the default, replaces instances in batches, adding a new one before removing an old one. It runs two versions at once, so the change must be backward compatible with the previous version and its database schema.
2. Use blue-green, an atomic traffic switch between two identical environments, when the change is not backward compatible or rollback must be instant.
3. Use canary, a small traffic share widened on healthy metrics, for high traffic or a change you do not fully trust.
4. A merge to `main` never deploys to production. A pull request runs lint, typecheck, tests and a preview deploy, and a merge adds the image build, a staging deploy and smoke tests. Production is a separate approved step, a protected environment with required reviewers or a manually triggered run, and it gates nothing until its protection rule exists.
5. The image build and its scan, bill-of-materials and signature gate belong to `docker-patterns`. The pipeline invokes them and fails on their findings, never with `|| true`.
6. Authenticate to a cloud with OIDC, never a stored long-lived key, and declare minimum permissions on every job, because a compromised pipeline step inherits what the job holds.
7. Pin every third-party pipeline step to a full commit SHA, the runner to a fixed label and every image to a tag plus digest, since a moved tag or image swaps the code. Bumps are manual pull requests, not a bot's.
8. Liveness touches nothing and readiness reports what this instance needs to serve, per `observability-and-logging`, keeping shared dependencies out. Use the `api-design` paths `/health` and `/ready`. Liveness on a dependency-checking endpoint turns a database blip into a restart storm. This skill owns the probe manifests.
9. Every environment-varying value comes from an environment variable, and the process validates the whole set against a schema before serving, so a missing value kills it at boot.
10. Secrets are injected by a secrets manager at runtime, never committed and never baked into an image.
11. Rollback is a rehearsed pipeline path that takes seconds. Revert-and-rebuild is another deployment, with the same lead time.
12. Before a release, confirm every item of the list under [Rollback is a rehearsed path](references/rules-and-examples.md#rollback-is-a-rehearsed-path).
13. Every production workload runs non-root, read-only, with no privilege escalation and no capabilities, and carries a disruption budget, a default-deny network policy, requests and limits, and autoscaling with at least two replicas, enforced at admission.
