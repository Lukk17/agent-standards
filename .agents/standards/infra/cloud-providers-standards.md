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