# Deployment Patterns Checklist

Run it before calling a pipeline or rollout change done, and before a release.

- [ ] The rollout strategy is chosen deliberately and the change is compatible with it.
- [ ] Nothing promotes to production without an explicit approval gate.
- [ ] The image is built, scanned, and signed through `docker-patterns`, and the pipeline fails on findings.
- [ ] Cloud authentication uses OIDC, no long-lived key in CI secrets.
- [ ] Every job declares minimum permissions, no `write-all`.
- [ ] Liveness and readiness are separate endpoints, liveness touches no dependency.
- [ ] All configuration comes from the environment and is validated at startup.
- [ ] Secrets are injected at runtime by a secrets manager.
- [ ] The rollback path has been executed in staging.
- [ ] Migrations in the release are backward compatible with the previous version.
- [ ] Production workloads carry a security context, a PDB, a NetworkPolicy, limits, and an HPA.
- [ ] The production readiness checklist in [cloud-and-operations.md](cloud-and-operations.md#production-readiness) has been walked.
