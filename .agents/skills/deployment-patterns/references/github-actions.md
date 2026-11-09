# GitHub Actions pipelines

A reference pipeline, the authentication and permission rules, and the canary automation that sits on top of it. The
strategy and gating rules live in [SKILL.md](../SKILL.md).

Every action below is pinned to a full 40-character commit SHA with the exact release tag it was resolved from in a trailing comment, `# vX.Y.Z`, because a tag can be moved to other code and a SHA cannot, and a moving major such as `# v5` says nothing about which code the SHA is. This holds for every `uses:` in a workflow and in a composite action, first-party `actions/*` included. The examples show `<commit-sha>` and `vX.Y.Z` in place of real values.

Resolve the SHA for a tag, never guess it or copy it from memory, with `git ls-remote --tags https://github.com/<owner>/<repo> refs/tags/<tag> refs/tags/<tag>^{}`. An annotated tag prints two lines, and the commit is the dereferenced `^{}` one; the other is the tag object, which `uses:` will not run. A lightweight tag prints only the commit. Then check the SHA resolves on GitHub before committing.

Runners are pinned the same way: `runs-on: ubuntu-24.04`, never `ubuntu-latest`, which GitHub moves to a new image, and a new toolchain, without a commit in your repository.

Bumps are manual. No Dependabot version updates and no Renovate bump pull requests unless the project owner asks for them: a dependency or action bump is a deliberate pull request that re-resolves the SHA and the tag together, per `build-dependency-management`. Bump majors deliberately, a major bump usually changes the runner Node version.

---

### Contents

- [Standard pipeline](#standard-pipeline)
- [OIDC instead of static credentials](#oidc-instead-of-static-credentials)
- [Job-level permissions](#job-level-permissions)
- [Workflow linting](#workflow-linting)
- [Failure notifications](#failure-notifications)
- [Matrix builds](#matrix-builds)
- [Pipeline SLA](#pipeline-sla)
- [Canary rollout automation](#canary-rollout-automation)

---

### Standard pipeline

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  IMAGE: ghcr.io/${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<commit-sha> # vX.Y.Z
      - uses: actions/setup-node@<commit-sha> # vX.Y.Z
        with:
          node-version: 26
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@<commit-sha> # vX.Y.Z
        if: always()
        with:
          name: coverage
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-24.04
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
      id-token: write
    outputs:
      digest: ${{ steps.push.outputs.digest }}
    steps:
      - uses: actions/checkout@<commit-sha> # vX.Y.Z
      - uses: docker/setup-buildx-action@<commit-sha> # vX.Y.Z
      - uses: docker/login-action@<commit-sha> # vX.Y.Z
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@<commit-sha> # vX.Y.Z
        with:
          load: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: aquasecurity/trivy-action@<commit-sha> # vX.Y.Z
        with:
          image-ref: ${{ env.IMAGE }}:${{ github.sha }}
          exit-code: '1'
          severity: CRITICAL,HIGH
          ignore-unfixed: true
          format: json
          output: trivy-report.json
      - uses: actions/upload-artifact@<commit-sha> # vX.Y.Z
        if: always()
        with:
          name: trivy-report
          path: trivy-report.json
      - id: push
        uses: docker/build-push-action@<commit-sha> # vX.Y.Z
        with:
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha
      - uses: anchore/sbom-action@<commit-sha> # vX.Y.Z
        with:
          image: ${{ env.IMAGE }}@${{ steps.push.outputs.digest }}
          format: cyclonedx-json
          output-file: sbom.json
      - uses: sigstore/cosign-installer@<commit-sha> # vX.Y.Z
      - name: Sign the image and attest the SBOM
        env:
          COSIGN_PRIVATE_KEY: ${{ secrets.COSIGN_PRIVATE_KEY }}
          COSIGN_PASSWORD: ${{ secrets.COSIGN_PASSWORD }}
        run: |
          cosign sign --yes --key env://COSIGN_PRIVATE_KEY "$IMAGE@${{ steps.push.outputs.digest }}"
          cosign attest --yes --key env://COSIGN_PRIVATE_KEY --type cyclonedx --predicate sbom.json "$IMAGE@${{ steps.push.outputs.digest }}"

  deploy-staging:
    needs: build
    runs-on: ubuntu-24.04
    environment: staging
    permissions:
      contents: read
      packages: read
      id-token: write
    steps:
      - uses: actions/checkout@<commit-sha> # vX.Y.Z
      - uses: docker/login-action@<commit-sha> # vX.Y.Z
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: sigstore/cosign-installer@<commit-sha> # vX.Y.Z
      - name: Verify the image signature
        env:
          COSIGN_PUBLIC_KEY: ${{ vars.COSIGN_PUBLIC_KEY }}
        run: cosign verify --key env://COSIGN_PUBLIC_KEY "$IMAGE@${{ needs.build.outputs.digest }}"
      - name: Deploy to staging
        run: ./scripts/deploy.sh staging "${{ github.sha }}"

  smoke-test:
    needs: deploy-staging
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@<commit-sha> # vX.Y.Z
      - name: Smoke test staging
        run: ./scripts/smoke-test.sh staging

  deploy-production:
    needs: [build, smoke-test]
    runs-on: ubuntu-24.04
    environment: production
    permissions:
      contents: read
      packages: read
      id-token: write
    steps:
      - uses: actions/checkout@<commit-sha> # vX.Y.Z
      - uses: docker/login-action@<commit-sha> # vX.Y.Z
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: sigstore/cosign-installer@<commit-sha> # vX.Y.Z
      - name: Verify the image signature
        env:
          COSIGN_PUBLIC_KEY: ${{ vars.COSIGN_PUBLIC_KEY }}
        run: cosign verify --key env://COSIGN_PUBLIC_KEY "$IMAGE@${{ needs.build.outputs.digest }}"
      - name: Deploy to production
        run: ./scripts/deploy.sh production "${{ github.sha }}"
```

The build job loads the image locally, scans it, and pushes only when Trivy finds no fixable critical or high issue.
It then signs the pushed digest and attaches the SBOM to it as a signed attestation, and each deploy job verifies the
signature before it deploys. The scan, SBOM, and signing rules themselves live in `docker-patterns`. The key pair
comes from `cosign generate-key-pair`: the private key and its password are repository secrets, the public key a
repository variable.

The `environment: production` line is the gate. It only gates anything when that GitHub environment carries a
protection rule with required reviewers, so the job pauses for a human. Configure the rule, then rely on it.

---

### OIDC instead of static credentials

Exchange a short-lived token for a cloud role. A long-lived access key in CI secrets is a credential that leaks once
and stays valid.

```yaml
- uses: aws-actions/configure-aws-credentials@<commit-sha> # vX.Y.Z
  with:
    role-to-assume: arn:aws:iam::123456789:role/deploy-role
    aws-region: eu-west-1
```

`id-token: write` on the job is what makes the exchange possible.

---

### Job-level permissions

Every job declares the minimum it needs. The default token is broad, and a compromised action inherits whatever the
job holds.

```yaml
permissions:
  contents: read
  packages: write
  id-token: write
  pull-requests: write
```

Never use `permissions: write-all`, at workflow or job level.

---

### Workflow linting

`actionlint` catches expression errors, bad `runs-on` values, and shell mistakes that otherwise surface only when the
workflow runs.

```yaml
- name: Lint GitHub Actions workflows
  uses: rhysd/actionlint@<commit-sha> # vX.Y.Z
```

---

### Failure notifications

Notify the author and a shared channel on any pipeline failure, with a link back to the run.

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@<commit-sha> # vX.Y.Z
  with:
    payload: |
      {
        "text": "Pipeline failed: ${{ github.workflow }} / ${{ github.job }}",
        "blocks": [{
          "type": "section",
          "text": {
            "type": "mrkdwn",
            "text": "*Pipeline:* ${{ github.workflow }}\n*Job:* ${{ github.job }}\n*Branch:* ${{ github.ref_name }}\n*SHA:* ${{ github.sha }}\n<${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|View logs>"
          }
        }]
      }
```

---

### Matrix builds

```yaml
strategy:
  fail-fast: true
  matrix:
    os: [ubuntu-24.04, windows-2025]
    java: ['21', '25']
```

Use `fail-fast: true` for pull request builds, where the first failure is the answer. Set it to `false` for release
validation, where you want the full picture of which combinations broke.

---

### Pipeline SLA

- CI, meaning lint plus test plus build: 15 minutes or less.
- Deployment pipeline, staging plus production: 10 minutes or less.
- A pipeline over its SLA is raised as a tech-debt item within two business days, not tolerated indefinitely.

---

### Canary rollout automation

Increment canary traffic in steps with a health gate between each:

| Step | Traffic | Minimum soak |
|---|---|---|
| 1 | 5 percent | 10 minutes |
| 2 | 25 percent | 10 minutes |
| 3 | 100 percent | n/a |

Abort and roll back automatically if the canary's error ratio exceeds the stable version's by more than 1 percentage
point, or p99 latency rises more than 20 percent, during any soak period.

Automated rollback is a safety reflex, and it is compatible with keeping promotion a manual approved gate: rolling
back returns the system to the last known-good state, it does not push an untested release forward.

The check below compares the two ratios, 5xx responses divided by all responses, and assumes the metrics carry a
`track` label set to `canary` or `stable`. Use whatever label your deployment already puts on the two versions.

```yaml
- name: Check canary health
  run: |
    error_ratio() {
      local errors="sum(rate(http_requests_total{track=\"$1\",status=~\"5..\"}[5m]))"
      local total="sum(rate(http_requests_total{track=\"$1\"}[5m]))"
      curl -sG "$PROMETHEUS_URL/api/v1/query" --data-urlencode "query=$errors / $total" | jq -r '.data.result[0].value[1]'
    }
    CANARY=$(error_ratio canary)
    STABLE=$(error_ratio stable)
    if (( $(echo "$CANARY - $STABLE > 0.01" | bc -l) )); then
      echo "Canary error ratio $CANARY exceeds stable $STABLE by more than 1 point, rolling back"
      kubectl rollout undo deployment/my-app
      exit 1
    fi
```

A human running `kubectl rollout undo` by hand is the last-resort fallback, not the mechanism. The pipeline owns the
rollback so it happens in seconds and leaves a record.
