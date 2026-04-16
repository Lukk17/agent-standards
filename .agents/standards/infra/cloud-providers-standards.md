### AI Cloud Provider Infrastructure Standards (AWS, GCP, Azure)

---

### Core Execution Directives

- Treat all LLM generated IAM policies, network rules, and infrastructure configurations as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every cloud architecture task.
- Append a Zero-Trust directive demanding mandatory web searches for current AWS, GCP, or Azure documentation regarding IAM limits and networking defaults.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every IAM action, CIDR block, and resource attribute provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### IAM and Least Privilege

- Absolutely prohibit the use of wildcard (`*`) permissions in any IAM policy. Policies must explicitly define the exact Actions and exact Resources allowed. [Confidence: 100%]
  - Link: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
  - Quote: "you"
- Never generate or recommend long-lived static access keys (e.g., AWS Access Keys) for compute resources. Mandate the use of attached IAM Roles, Managed Identities, or Workload Identity Federation. [Confidence: 100%]
- Implement permissions boundaries to ensure that even if an identity is compromised, the blast radius is strictly contained to a specific subset of the cloud environment. [Confidence: 100%]

---

### Networking and Isolation

- Never deploy databases, internal APIs, or cache clusters into public subnets. They must reside strictly in private subnets with no direct route to the Internet Gateway. [Confidence: 100%]
  - Link: https://cloud.google.com/vpc/docs/vpc
  - Quote: "provides"
- Ensure that all Security Groups (AWS), VPC Firewall Rules (GCP), or Network Security Groups (Azure) default to a strict implicit deny-all. Explicitly open only the exact ports required for cross-service communication. [Confidence: 100%]
- Restrict inbound SSH or RDP access globally. Mandate the use of secure tunneling services like AWS Systems Manager Session Manager (SSM), GCP Identity-Aware Proxy (IAP), or Azure Bastion. [Confidence: 100%]

---

### Infrastructure as Code (IaC) State Management

- When generating Terraform, OpenTofu, or Bicep code, strictly prohibit local state files. The AI must configure a remote backend (e.g., S3 + DynamoDB for locking, GCS, or Azure Blob Storage). [Confidence: 100%]
- Ensure the remote state storage bucket itself has versioning enabled and server-side encryption enforced. [Confidence: 100%]
- Abstract cloud components into reusable modules. Do not generate monolithic IaC files for entire environments. [Confidence: 100%]

---

### Resource Tagging and Cost Governance

- Enforce a mandatory tagging policy for every deployed resource. At a minimum, every resource must have `Environment` (e.g., dev, prod), `Owner`, and `Project` tags. [Confidence: 100%]
  - Link: https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/tag-resources
  - Quote: "to"
- Ensure the AI defines lifecycle rules for ephemeral resources (like test storage buckets or temporary EBS volumes) to automatically delete them after a set duration, preventing runaway cloud costs. [Confidence: 100%]
- Configure automated budget alerts tied to the specific project tags to trigger webhooks or notifications if spending thresholds are breached. [Confidence: 100%]

---

### Logging and Audit Trails

- Enable cloud-native audit logging on every account/project/subscription: [Confidence: 100%]
  - AWS: **CloudTrail** (all management events, data events for S3 and Lambda) with a minimum 1-year retention in a dedicated, protected S3 bucket.
  - GCP: **Cloud Audit Logs** (Admin Activity, Data Access) with export to Cloud Storage or BigQuery.
  - Azure: **Activity Log** + **Microsoft Defender for Cloud** with Log Analytics workspace retention ≥ 1 year.
- Enable **GuardDuty** (AWS), **Security Command Center** (GCP), or **Microsoft Defender for Cloud** (Azure) for threat detection; route findings to the security team's alerting channel.
- Never disable audit logging; treat any attempt to disable it as a security incident.

---

### Security Posture Management

- Enroll every account in a cloud security posture management (CSPM) tool: AWS Security Hub, GCP Security Command Center, or Azure Defender.
- Enforce compliance standards appropriate to the workload (CIS Benchmarks, NIST 800-53, PCI-DSS, HIPAA) via the CSPM tool's compliance dashboard.
- Review and remediate all HIGH and CRITICAL findings within 7 days; MEDIUM findings within 30 days.
- Export CSPM findings to a central SIEM for cross-cloud visibility.

---

### Disaster Recovery

- Define **RTO** (Recovery Time Objective) and **RPO** (Recovery Point Objective) for every production service tier. [Confidence: 100%]
- For services with RTO < 1 hour: implement active-active or active-passive multi-region architecture.
- For services with RTO < 4 hours: implement automated failover with infrastructure-as-code that can recreate the environment in a secondary region.
- Conduct a full DR drill at least once per year; document the results and remediate gaps.
- Enable cross-region replication for: S3 buckets (AWS), Cloud Storage (GCP), Azure Blob Storage, and all production databases.

---

### Compliance Framework Alignment

- Before building a system that processes regulated data, identify the applicable compliance frameworks (SOC2 Type II, ISO 27001, HIPAA, GDPR, PCI-DSS).
- Tag all cloud resources with the applicable compliance framework: `compliance=pci-dss`.
- Maintain an evidence collection pipeline for continuous compliance: automated screenshots of security configurations, change logs, access reviews.
- Use AWS Audit Manager, GCP Compliance Reports, or Azure Policy to map cloud controls to compliance requirements.

---

### Cost Optimisation

- Use **Reserved Instances** (AWS), **Committed Use Discounts** (GCP), or **Azure Reservations** for baseline steady-state compute; target 60–70% reservation coverage of predictable workloads. [Confidence: 100%]
- Use **Spot/Preemptible/Spot VMs** for fault-tolerant, non-critical batch workloads (CI workers, data processing jobs) to reduce cost by up to 90%.
- Right-size instances: review CPU and memory utilisation metrics monthly; downsize any resource consistently below 20% utilisation.
- Delete or snapshot and terminate all non-production resources outside of business hours using scheduled start/stop policies.

---

### CDN and Static Asset Delivery

- Serve all static assets (images, JS, CSS, fonts) through a CDN: **CloudFront** (AWS), **Cloud CDN** (GCP), or **Azure Front Door**. [Confidence: 100%]
- Set long-lived `Cache-Control` headers on static assets that are content-addressed (hashed filenames): `Cache-Control: public, max-age=31536000, immutable`.
- Configure CDN geographic restrictions to comply with data residency requirements where applicable.
- Enable CDN access logs and route them to the central logging pipeline.

---

### Service Limit Monitoring

- Monitor service quota utilisation for all critical resources (EC2 vCPUs, Lambda concurrency, DynamoDB throughput, GCS buckets).
- Alert when any quota reaches 70% utilisation; submit a limit increase request before reaching 80%.
- Document current quota limits and usage in `docs/INFRASTRUCTURE.md`; review quarterly.