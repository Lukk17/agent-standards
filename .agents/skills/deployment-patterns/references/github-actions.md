# GitHub Actions pipelines

A reference pipeline, the authentication and permission rules, and the canary automation that sits on top of it. The
strategy and gating rules live in [SKILL.md](../SKILL.md).

Every action below is pinned to its current major. Bump majors deliberately, a major bump usually changes the runner
Node version.

---

### Standard pipeline

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-node@v5
        with:
          node-version: 24
          cache: npm
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm test -- --coverage
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: coverage
          path: coverage/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions:
      contents: read
      packages: write
      id-token: write
    steps:
      - uses: actions/checkout@v5
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v7
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Deploy to production
        run: ./scripts/deploy.sh "${{ github.sha }}"
```

The `environment: production` line is the gate. It only gates anything when that GitHub environment carries a
protection rule with required reviewers, so the job pauses for a human. Configure the rule, then rely on it.

---

### OIDC instead of static credentials

Exchange a short-lived token for a cloud role. A long-lived access key in CI secrets is a credential that leaks once
and stays valid.

```yaml
- uses: aws-actions/configure-aws-credentials@v5
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
  uses: rhysd/actionlint@v1
```

---

### Failure notifications

Notify the author and a shared channel on any pipeline failure, with a link back to the run.

```yaml
- name: Notify on failure
  if: failure()
  uses: slackapi/slack-github-action@v4
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
    os: [ubuntu-latest, windows-latest]
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

Abort and roll back automatically if the error rate exceeds baseline by more than 1 percent, or p99 latency rises
more than 20 percent, during any soak period.

Automated rollback is a safety reflex, and it is compatible with keeping promotion a manual approved gate: rolling
back returns the system to the last known-good state, it does not push an untested release forward.

```yaml
- name: Check canary health
  run: |
    ERROR_RATE=$(curl -s "$PROMETHEUS_URL/api/v1/query?query=rate(http_requests_total{status=~'5..'}[1m])" | jq -r '.data.result[0].value[1]')
    if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
      echo "Error rate $ERROR_RATE exceeds threshold, rolling back"
      kubectl rollout undo deployment/my-app
      exit 1
    fi
```

A human running `kubectl rollout undo` by hand is the last-resort fallback, not the mechanism. The pipeline owns the
rollback so it happens in seconds and leaves a record.
