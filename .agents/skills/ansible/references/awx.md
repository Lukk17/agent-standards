# AWX and Ansible Automation Platform

How automation is defined and gated on AWX and Ansible Automation Platform. The rules that always apply live in [SKILL.md](../SKILL.md).

---

### Job Templates

Define automation as reusable Job Templates. Ad-hoc playbook runs against production leave no audit trail and no approval record, which is the whole reason the platform exists.

- Use Survey Variables for operator-supplied runtime parameters, with allowed values and a default on each.
- Use Credentials objects for every secret. A secret passed as an extra variable is stored in the job's own record and shows up in the job output.
- Name Job Templates `[Environment] Role/Action Description`, for example `[Prod] Deploy Web Application`, so the environment is visible in every list, notification, and audit line without opening the template.
- Gate production execution behind an approval node in a Workflow Job Template. Merging to the main branch produces a ready-to-run template, it does not run it.
