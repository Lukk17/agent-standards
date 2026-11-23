# Cloud Security on AWS

Contents:

- [Least privilege in IAM](#least-privilege-in-iam)
- [Multi-factor authentication](#multi-factor-authentication)
- [Secrets Manager](#secrets-manager)
- [Security groups](#security-groups)
- [CloudWatch logging](#cloudwatch-logging)
- [RDS backups](#rds-backups)
- [S3 bucket exposure](#s3-bucket-exposure)
- [RDS public access](#rds-public-access)
- [Resources](#resources)

The AWS form of the cloud checks, with the IAM policy, the CLI commands, the SDK calls and the Terraform resources. Open this when the application runs on AWS. The checks themselves, with the verification steps for each area, are in [cloud-infrastructure-security.md](cloud-infrastructure-security.md).

---

### Least privilege in IAM

```yaml
# PASS: CORRECT: Minimal permissions, each action on the resource type it applies to
iam_role:
  statements:
    - permissions:
        - s3:ListBucket  # Acts on the bucket, so the ARN has no /*
      resources:
        - arn:aws:s3:::my-bucket
    - permissions:
        - s3:GetObject  # Acts on objects, so the ARN ends in /*
      resources:
        - arn:aws:s3:::my-bucket/*

# FAIL: WRONG: Overly broad permissions
iam_role:
  permissions:
    - s3:*  # All S3 actions
  resources:
    - "*"  # All resources
```

---

### Multi-factor authentication

```bash
# ALWAYS enable MFA for root/admin accounts
aws iam enable-mfa-device \
  --user-name admin \
  --serial-number arn:aws:iam::123456789:mfa/admin \
  --authentication-code1 123456 \
  --authentication-code2 789012
```

---

### Secrets Manager

The secrets manager fills the variables application code reads, through the platform's secret injection or a fetch at
startup like the one below.

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

Rotation:

```bash
# Set up automatic rotation for database credentials
aws secretsmanager rotate-secret \
  --secret-id prod/db-password \
  --rotation-lambda-arn arn:aws:lambda:region:account:function:rotate \
  --rotation-rules AutomaticallyAfterDays=30
```

---

### Security groups

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

---

### CloudWatch logging

```typescript
// PASS: CORRECT: Comprehensive logging
import { CloudWatchLogsClient, PutLogEventsCommand } from '@aws-sdk/client-cloudwatch-logs';

const client = new CloudWatchLogsClient({});

const logSecurityEvent = async (event: SecurityEvent) => {
  await client.send(new PutLogEventsCommand({
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
  }));
};
```

---

### RDS backups

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

---

### S3 bucket exposure

AWS recommends keeping ACLs disabled "except in circumstances where you must control access for each object
individually", so the fix is Object Ownership `BucketOwnerEnforced` plus a public access block, not a private ACL.

```bash
# FAIL: WRONG: Public bucket
aws s3api put-bucket-acl --bucket my-bucket --acl public-read

# PASS: CORRECT: Block public access, disable ACLs, grant access through a bucket policy
aws s3api put-public-access-block --bucket my-bucket --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-ownership-controls --bucket my-bucket --ownership-controls 'Rules=[{ObjectOwnership=BucketOwnerEnforced}]'
aws s3api put-bucket-policy --bucket my-bucket --policy file://policy.json
```

---

### RDS public access

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
- [Terraform Security Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)
