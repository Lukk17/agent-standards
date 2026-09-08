# Cloud provider standards and operations

Account-level rules that sit under any workload, whatever ships onto it. The pipeline and rollout rules live in
[SKILL.md](../SKILL.md).

---

### IAM, least privilege

- No wildcard permission (`*`) on any resource or any action.
- One service account per workload. A shared account makes an audit log unattributable and turns one compromise into
  several.
- Rotate service account keys every 90 days, or remove them entirely in favour of Workload Identity or OIDC, which
  is the better answer.

---

### Network isolation

- Databases and internal services live in private subnets with no public endpoint.
- Administrative access goes through a bastion host or a VPN, never a public management port.

---

### Infrastructure as code

- Terraform state lives remotely with locking: S3 plus DynamoDB on AWS, GCS on GCP.
- `.tfstate` never enters version control. It contains resource attributes including, in some providers, secrets.

---

### Resource tagging

Every cloud resource carries these tags, because an untagged resource cannot be attributed, budgeted, or safely
deleted.

| Tag | Example |
|---|---|
| `env` | `production` |
| `team` | `platform` |
| `service` | `auth-api` |
| `cost-center` | `engineering` |

---

### Cost controls

- Budget alerts at 80 percent and 100 percent of the monthly budget.
- Quota monitoring with an alert that fires before a service limit is reached, not when it is hit.

---

### Audit and security posture

- CloudTrail on AWS, Cloud Audit Logs on GCP, enabled in every account including the ones nobody uses.
- GuardDuty on AWS, Security Command Center on GCP.
- A CDN in front of all static assets.

---

### Disaster recovery

- Multi-region DR with documented RTO and RPO targets. A target nobody wrote down is not a target.
- An annual DR drill, with the results written up including what did not work.
- Automated failover where RTO is under an hour. A manual runbook is only acceptable when RTO is an hour or more,
  because nobody executes a novel manual procedure correctly inside sixty minutes.

---

### Production readiness

Walk this before any first production deployment, and again after any architectural change.

Application:

- [ ] All tests pass, unit, integration, and end to end.
- [ ] No hardcoded secret in code or config.
- [ ] Error handling covers the edge cases, not only the happy path.
- [ ] Logging is structured and contains no personal data.
- [ ] The health endpoint reports something meaningful, not a constant 200.

Infrastructure:

- [ ] The image builds reproducibly from pinned versions.
- [ ] Environment variables documented and validated at startup.
- [ ] CPU and memory requests and limits set.
- [ ] Horizontal scaling configured with a minimum and a maximum.
- [ ] TLS on every endpoint.

Monitoring:

- [ ] Request rate, latency, and error metrics exported.
- [ ] An alert exists for the error rate crossing its threshold.
- [ ] Logs aggregated and searchable.
- [ ] Uptime monitoring on the health endpoint from outside the cluster.

Security:

- [ ] Dependencies scanned for known vulnerabilities.
- [ ] CORS restricted to the origins that actually need it.
- [ ] Rate limiting on every public endpoint.
- [ ] Authentication and authorization verified by someone other than the author.
- [ ] Security headers set: CSP, HSTS, X-Frame-Options.

Operations:

- [ ] Rollback plan documented and rehearsed in staging.
- [ ] Database migration tested against production-sized data.
- [ ] A runbook exists for the common failure scenarios.
- [ ] On-call rotation and escalation path defined.
