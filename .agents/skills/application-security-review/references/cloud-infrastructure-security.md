# Cloud & Infrastructure Security

Contents:

- [When to Activate](#when-to-activate)
- [Cloud Security Checklist](#cloud-security-checklist)
  - [1. IAM & Access Control](#1-iam--access-control)
  - [2. Secrets Management](#2-secrets-management)
  - [3. Network Security](#3-network-security)
  - [4. Logging & Monitoring](#4-logging--monitoring)
  - [5. CI/CD Pipeline Security](#5-cicd-pipeline-security)
  - [6. CDN Security](#6-cdn-security)
  - [7. Backup & Disaster Recovery](#7-backup--disaster-recovery)
- [Pre-Deployment Cloud Security Checklist](#pre-deployment-cloud-security-checklist)
- [Common Cloud Security Misconfigurations](#common-cloud-security-misconfigurations)
- [Resources](#resources)

Depth behind [SKILL.md](../SKILL.md) for cloud, network and pipeline hardening. This file holds the checks every platform shares. The configuration and the commands sit in one file per platform: [aws.md](aws.md) for AWS and [cloudflare.md](cloudflare.md) for Cloudflare.

---

### When to Activate

- Deploying applications to cloud platforms (AWS, Vercel, Railway, Cloudflare)
- Configuring IAM roles and permissions
- Implementing infrastructure as code (Terraform, CloudFormation)
- Configuring logging and monitoring
- Managing secrets in cloud environments
- Setting up CDN and edge security
- Implementing disaster recovery and backup strategies

---

### Cloud Security Checklist

#### 1. IAM & Access Control

Grant each role the minimal permissions, each action on the resource type it applies to, never all actions on all resources. Always enable multi-factor authentication for root and admin accounts. The policy and the command: [aws.md](aws.md#least-privilege-in-iam).

##### Verification Steps

- [ ] No root account usage in production
- [ ] MFA enabled for all privileged accounts
- [ ] Service accounts use roles, not long-lived credentials
- [ ] IAM policies follow least privilege
- [ ] Regular access reviews conducted
- [ ] Unused credentials rotated or removed

#### 2. Secrets Management

Application code reads every secret from its environment, as [SKILL.md](../SKILL.md) requires. In production a
secrets manager with rotation is what fills those variables, through the platform's secret injection or a fetch at
startup. A secret that exists only as a hand-set variable, with no manager behind it, is never
rotated and never audited. The fetch and the rotation command: [aws.md](aws.md#secrets-manager).

##### Verification Steps

- [ ] All secrets stored in cloud secrets manager (AWS Secrets Manager, Vercel Secrets)
- [ ] Automatic rotation enabled for database credentials
- [ ] API keys rotated at least quarterly
- [ ] No secrets in code, logs, or error messages
- [ ] Audit logging enabled for secret access

#### 3. Network Security

Restrict every firewall rule to the ports and the address ranges that must reach the service, such as HTTPS from the internal network only, and never open all ports to all addresses. The rules as code: [aws.md](aws.md#security-groups).

##### Verification Steps

- [ ] Database not publicly accessible
- [ ] SSH/RDP ports restricted to VPN/bastion only
- [ ] Security groups follow least privilege
- [ ] Network ACLs configured
- [ ] VPC flow logs enabled

#### 4. Logging & Monitoring

Log every security event with its type, the user, the address and the result, and never log sensitive data. The logging call: [aws.md](aws.md#cloudwatch-logging).

##### Verification Steps

- [ ] CloudWatch/logging enabled for all services
- [ ] Failed authentication attempts logged
- [ ] Admin actions audited
- [ ] Log retention configured (90+ days for compliance)
- [ ] Alerts configured for suspicious activity
- [ ] Logs centralized and tamper-proof

#### 5. CI/CD Pipeline Security

Pipeline OIDC, job-level permissions, and action pinning belong to `deployment-patterns`, in its
`references/github-actions.md`. This reference adds only what the
pipeline must scan: secrets on every push, and dependencies blocked at high and critical with the lock file installed
in CI, as [SKILL.md](../SKILL.md) states under Dependency risk. The npm commands and the package scripts for a local
audit are in [typescript.md](typescript.md#dependency-risk-with-npm).

##### Verification Steps

- [ ] OIDC and job permissions set per `deployment-patterns`
- [ ] Secrets scanning in pipeline
- [ ] Dependency vulnerability scanning
- [ ] Container image scanning (if applicable)
- [ ] Branch protection rules enforced
- [ ] Code review required before merge
- [ ] Signed commits enforced

#### 6. CDN Security

Set the security headers at the edge and enable the managed WAF rules: the OWASP core ruleset, the provider's managed ruleset, rate limiting and bot protection. The Worker and the rules: [cloudflare.md](cloudflare.md).

##### Verification Steps

- [ ] WAF enabled with OWASP rules
- [ ] Rate limiting configured
- [ ] Bot protection active
- [ ] DDoS protection enabled
- [ ] Security headers configured
- [ ] SSL/TLS strict mode enabled

#### 7. Backup & Disaster Recovery

Automate the database backups with a retention period, a backup window and deletion protection. The resource: [aws.md](aws.md#rds-backups).

##### Verification Steps

- [ ] Automated daily backups configured
- [ ] Backup retention meets compliance requirements
- [ ] Point-in-time recovery enabled
- [ ] Backup testing performed quarterly
- [ ] Disaster recovery plan documented
- [ ] RPO and RTO defined and tested

---

### Pre-Deployment Cloud Security Checklist

Before ANY production cloud deployment:

- [ ] IAM: Root account not used, MFA enabled, least privilege policies
- [ ] Secrets: All secrets in cloud secrets manager with rotation
- [ ] Network: Security groups restricted, no public databases
- [ ] Logging: CloudWatch/logging enabled with retention
- [ ] Monitoring: Alerts configured for anomalies
- [ ] CI/CD: secrets scanning and dependency audits, OIDC and permissions per `deployment-patterns`
- [ ] CDN/WAF: Cloudflare WAF enabled with OWASP rules
- [ ] Encryption: Data encrypted at rest and in transit
- [ ] Backups: Automated backups with tested recovery
- [ ] Compliance: GDPR/HIPAA requirements met (if applicable)
- [ ] Documentation: Infrastructure documented, runbooks created
- [ ] Incident Response: Security incident plan in place

---

### Common Cloud Security Misconfigurations

The two that recur are a storage bucket open to the public and a database reachable from the internet. The wrong and the right form of each: [aws.md](aws.md#s3-bucket-exposure) and [aws.md](aws.md#rds-public-access).

---

### Resources

- [OWASP Cloud Security](https://owasp.org/www-project-cloud-security/)

Remember: Cloud misconfigurations are the leading cause of data breaches. A single exposed S3 bucket or overly
permissive IAM policy can compromise your entire infrastructure. Always follow the principle of least privilege and
defense in depth.
