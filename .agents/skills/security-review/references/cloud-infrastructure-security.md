# Cloud & Infrastructure Security

Depth behind [SKILL.md](../SKILL.md) for cloud, network and pipeline hardening.

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

##### Principle of Least Privilege

```yaml
# PASS: CORRECT: Minimal permissions
iam_role:
  permissions:
    - s3:GetObject  # Only read access
    - s3:ListBucket
  resources:
    - arn:aws:s3:::my-bucket/*  # Specific bucket only

# FAIL: WRONG: Overly broad permissions
iam_role:
  permissions:
    - s3:*  # All S3 actions
  resources:
    - "*"  # All resources
```

##### Multi-Factor Authentication (MFA)

```bash
# ALWAYS enable MFA for root/admin accounts
aws iam enable-mfa-device \
  --user-name admin \
  --serial-number arn:aws:iam::123456789:mfa/admin \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

##### Verification Steps

- [ ] No root account usage in production
- [ ] MFA enabled for all privileged accounts
- [ ] Service accounts use roles, not long-lived credentials
- [ ] IAM policies follow least privilege
- [ ] Regular access reviews conducted
- [ ] Unused credentials rotated or removed

#### 2. Secrets Management

##### Cloud Secrets Managers

Application code reads every secret from its environment, as [SKILL.md](../SKILL.md) requires. In production a
secrets manager with rotation is what fills those variables, through the platform's secret injection or a fetch at
startup like the one below. A secret that exists only as a hand-set variable, with no manager behind it, is never
rotated and never audited.

```typescript
// PASS: CORRECT: the secrets manager is the source of the value
import { SecretsManager } from '@aws-sdk/client-secrets-manager';

const client = new SecretsManager({ region: 'us-east-1' });
const secret = await client.getSecretValue({ SecretId: 'prod/api-key' });
const apiKey = JSON.parse(secret.SecretString).key;

// PASS: CORRECT: application code reads the variable the platform filled from the manager
const apiKey = process.env.API_KEY;

// FAIL: WRONG: hardcoded
const apiKey = 'sk-live-3f8a2b91c4';
```

##### Secrets Rotation

```bash
# Set up automatic rotation for database credentials
aws secretsmanager rotate-secret \
  --secret-id prod/db-password \
  --rotation-lambda-arn arn:aws:lambda:region:account:function:rotate \
  --rotation-rules AutomaticallyAfterDays=30
```

##### Verification Steps

- [ ] All secrets stored in cloud secrets manager (AWS Secrets Manager, Vercel Secrets)
- [ ] Automatic rotation enabled for database credentials
- [ ] API keys rotated at least quarterly
- [ ] No secrets in code, logs, or error messages
- [ ] Audit logging enabled for secret access

#### 3. Network Security

##### VPC and Firewall Configuration

```terraform
# PASS: CORRECT: Restricted security group
resource "aws_security_group" "app" {
  name = "app-sg"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]  # Internal VPC only
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Only HTTPS outbound
  }
}

# FAIL: WRONG: Open to the internet
resource "aws_security_group" "bad" {
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # All ports, all IPs!
  }
}
```

##### Verification Steps

- [ ] Database not publicly accessible
- [ ] SSH/RDP ports restricted to VPN/bastion only
- [ ] Security groups follow least privilege
- [ ] Network ACLs configured
- [ ] VPC flow logs enabled

#### 4. Logging & Monitoring

##### CloudWatch/Logging Configuration

```typescript
// PASS: CORRECT: Comprehensive logging
import { CloudWatchLogsClient, CreateLogStreamCommand } from '@aws-sdk/client-cloudwatch-logs';

const logSecurityEvent = async (event: SecurityEvent) => {
  await cloudwatch.putLogEvents({
    logGroupName: '/aws/security/events',
    logStreamName: 'authentication',
    logEvents: [{
      timestamp: Date.now(),
      message: JSON.stringify({
        type: event.type,
        userId: event.userId,
        ip: event.ip,
        result: event.result,
        // Never log sensitive data
      })
    }]
  });
};
```

##### Verification Steps

- [ ] CloudWatch/logging enabled for all services
- [ ] Failed authentication attempts logged
- [ ] Admin actions audited
- [ ] Log retention configured (90+ days for compliance)
- [ ] Alerts configured for suspicious activity
- [ ] Logs centralized and tamper-proof

#### 5. CI/CD Pipeline Security

Pipeline OIDC, job-level permissions, and action pinning belong to `deployment-patterns`, in
[github-actions.md](../../deployment-patterns/references/github-actions.md). This reference adds only what the
pipeline must scan: secrets on every push, and dependencies blocked at high and critical with the lock file installed
through `npm ci`, as [SKILL.md](../SKILL.md) states under Dependency risk.

##### Supply Chain Security

The package scripts for a local audit. `install` is not redefined, because npm runs that lifecycle script during
every install.

```json
{
  "scripts": {
    "audit": "npm audit --audit-level=high",
    "check": "npm outdated"
  }
}
```

##### Verification Steps

- [ ] OIDC and job permissions set per `deployment-patterns`
- [ ] Secrets scanning in pipeline
- [ ] Dependency vulnerability scanning
- [ ] Container image scanning (if applicable)
- [ ] Branch protection rules enforced
- [ ] Code review required before merge
- [ ] Signed commits enforced

#### 6. Cloudflare & CDN Security

##### Cloudflare Security Configuration

```typescript
// PASS: CORRECT: Cloudflare Workers with security headers
export default {
  async fetch(request: Request): Promise<Response> {
    const response = await fetch(request);

    // Add security headers
    const headers = new Headers(response.headers);
    headers.set('X-Frame-Options', 'DENY');
    headers.set('X-Content-Type-Options', 'nosniff');
    headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
    headers.set('Permissions-Policy', 'geolocation=(), microphone=()');

    return new Response(response.body, {
      status: response.status,
      headers
    });
  }
};
```

##### WAF Rules

```bash
# Enable Cloudflare WAF managed rules
# - OWASP Core Ruleset
# - Cloudflare Managed Ruleset
# - Rate limiting rules
# - Bot protection
```

##### Verification Steps

- [ ] WAF enabled with OWASP rules
- [ ] Rate limiting configured
- [ ] Bot protection active
- [ ] DDoS protection enabled
- [ ] Security headers configured
- [ ] SSL/TLS strict mode enabled

#### 7. Backup & Disaster Recovery

##### Automated Backups

```terraform
# PASS: CORRECT: Automated RDS backups
resource "aws_db_instance" "main" {
  allocated_storage     = 20
  engine               = "postgres"

  backup_retention_period = 30  # 30 days retention
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  deletion_protection = true  # Prevent accidental deletion
}
```

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

#### S3 Bucket Exposure

```bash
# FAIL: WRONG: Public bucket
aws s3api put-bucket-acl --bucket my-bucket --acl public-read

# PASS: CORRECT: Private bucket with specific access
aws s3api put-bucket-acl --bucket my-bucket --acl private
aws s3api put-bucket-policy --bucket my-bucket --policy file://policy.json
```

#### RDS Public Access

```terraform
# FAIL: WRONG
resource "aws_db_instance" "bad" {
  publicly_accessible = true  # NEVER do this!
}

# PASS: CORRECT
resource "aws_db_instance" "good" {
  publicly_accessible = false
  vpc_security_group_ids = [aws_security_group.db.id]
}
```

---

### Resources

- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [Cloudflare Security Documentation](https://developers.cloudflare.com/security/)
- [OWASP Cloud Security](https://owasp.org/www-project-cloud-security/)
- [Terraform Security Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)

Remember: Cloud misconfigurations are the leading cause of data breaches. A single exposed S3 bucket or overly
permissive IAM policy can compromise your entire infrastructure. Always follow the principle of least privilege and
defense in depth.
