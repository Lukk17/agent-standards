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