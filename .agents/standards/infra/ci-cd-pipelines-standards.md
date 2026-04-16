### AI CI/CD Pipelines Development Standards

---

### Core Execution Directives

- Treat all LLM generated pipeline YAML, caching strategies, and secret scopes as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every pipeline task.
- Append a Zero-Trust directive demanding mandatory web searches for current GitHub Actions or GitLab CI documentation.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every syntax element, workflow trigger, and parameter provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Secret Management and Security

- Never hardcode secrets or tokens in the pipeline YAML. [Confidence: 100%]
- Mandate the use of OpenID Connect (OIDC) instead of static, long-lived credentials for authenticating with cloud providers. [Confidence: 100%]
  - Link: https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect
  - Quote: "claims"
- Restrict job permissions in GitHub Actions to the absolute minimum using the permissions block at the job level. Do not use global repository write permissions. [Confidence: 100%]
- For GitLab CI, restrict the availability of CI/CD variables by marking them as Protected and Masked, ensuring they are only exposed to protected branches and tags. [Confidence: 100%]

---

### Caching Dependencies

- Explicitly configure caching to avoid redownloading dependencies on every pipeline run. [Confidence: 100%]
- In GitHub Actions, use actions/cache or native package manager caching. Define cache keys using hashes of the lockfiles. [Confidence: 100%]
  - Link: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manage-caches
  - Quote: "caches"
- In GitLab CI, define the cache keyword globally or per-job. Use cache:key tied to a lockfile or branch slug to prevent accidental overwrites across branches. [Confidence: 100%]
  - Link: https://docs.gitlab.com/ci/caching/
  - Quote: "from"
- Do not use caching for artifacts that must be passed between stages. Caches are not guaranteed to be present; artifacts are explicitly passed. [Confidence: 100%]

---

### Artifact Management

- Use artifacts strictly for passing compiled binaries, test reports, or build outputs between separate stages/jobs in the same pipeline. [Confidence: 100%]
- Set explicit expiration/retention policies for all generated artifacts to prevent storage bloat. [Confidence: 100%]

---

### Workflow Architecture and Triggers

- Limit workflow triggers to specific branches or paths to prevent running the entire pipeline on irrelevant changes. [Confidence: 100%]
- Structure complex pipelines into reusable workflows or include templates to avoid monolithic YAML files. [Confidence: 100%]

---

### Environment Protection Rules

- Require **manual approval** from at least one designated reviewer before any deployment to `staging` or `production` environments. [Confidence: 100%]
- Configure environment protection rules in GitHub (`Settings → Environments`) or GitLab (`Protected Environments`) to enforce this gate.
- Restrict which branches can deploy to production: only `main` / `master` or release tags.
- Log every deployment with the deployer identity, commit SHA, and timestamp for audit purposes.

---

### Deployment Strategies

Choose the deployment strategy based on risk and downtime tolerance:

| Strategy | When to Use | Rollback Speed |
|---|---|---|
| Rolling update | Standard services, tolerate brief mixed-version traffic | Fast (redeploy previous image) |
| Blue/Green | Zero-downtime releases, easy full rollback needed | Instant (flip load balancer) |
| Canary | High-risk changes, gradual traffic shift needed | Fast (set canary weight to 0%) |

- Run automated smoke tests against the new deployment **before** shifting traffic (Blue/Green and Canary). [Confidence: 100%]
- Define a clear traffic-shift schedule for Canary deployments (e.g., 5% → 25% → 100% over 30 minutes).

---

### Rollback Pipeline

- Every deployment job must have a corresponding **rollback job** that can be triggered manually or automatically on failure. [Confidence: 100%]
- Automated rollback must trigger when: post-deploy smoke tests fail, health check returns non-200 for more than 60 seconds after deployment, or error rate spikes above a defined threshold.
- Rollback must redeploy the previously deployed image tag, not re-run the build pipeline.
- Document the rollback procedure in `docs/RUNBOOK.md` for the on-call engineer.

---

### Notifications

- Send pipeline failure notifications to the PR author and the team's Slack / Teams channel on: test failure, deployment failure, and rollback trigger. [Confidence: 100%]
- Include in the notification: pipeline name, job that failed, commit SHA, branch/tag, and a direct link to the failed job logs.
- Send a success notification to the deployment channel when a production deployment completes.

---

### Matrix Builds

- Use matrix builds for projects that must be validated across multiple dimensions (OS, language version, dependency version):
  ```yaml
  strategy:
    matrix:
      java: ["21", "17"]
      os: [ubuntu-latest, windows-latest]
  ```
- Fail fast (`fail-fast: true`) in matrix builds for development PRs to give rapid feedback; disable for release validation runs to collect all results.

---

### Pipeline SLA

- CI pipeline (lint + test + build) must complete within **15 minutes** for developer PR feedback.
- Deployment pipeline (build + scan + deploy + smoke test) must complete within **10 minutes** for production deployments.
- If a pipeline stage consistently exceeds its SLA, split it into parallel jobs or optimize the slowest step.

---

### Pipeline Security Scanning

- Lint pipeline YAML files in CI:
  - GitHub Actions: run `actionlint` on all `.github/workflows/*.yml` files. [Confidence: 100%]
  - GitLab CI: use the built-in CI Lint API (`POST /api/v4/ci/lint`) to validate `.gitlab-ci.yml`.
- Scan third-party GitHub Actions for supply-chain risks: pin all `uses:` references to a full commit SHA, not a mutable tag. [Confidence: 100%]
  ```yaml
  # Bad:  uses: actions/checkout@v4
  # Good: uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
  ```

---

### Reusable Workflow Governance

- Store all shared/reusable workflows in a dedicated repository (e.g., `.github-workflows`) and version them with tags.
- Callers must reference reusable workflows by tag, not `@main`, to prevent unexpected breakage from upstream changes.
- Treat breaking changes to shared workflows as requiring a version bump and a migration guide for all consumers.