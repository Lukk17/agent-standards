# Docker Patterns Checklist

Run it before calling a Dockerfile, Compose or image pipeline change done.

- [ ] Every image pinned to an exact tag plus its digest, compose defaults and CI service images included, and no `:latest` published or consumed.
- [ ] Build split into stages, dependency manifests copied before source.
- [ ] Runtime stage runs as a created non-root user.
- [ ] `HEALTHCHECK` declared.
- [ ] `.dockerignore` present next to the Dockerfile and excludes `.git`, `.env`, and tests.
- [ ] No secret in `ENV`, `ARG`, or a committed compose file.
- [ ] Named volumes only, no anonymous volume anywhere.
- [ ] Internal services on their own network, published ports bound to loopback or omitted.
- [ ] `cap_drop: [ALL]`, `no-new-privileges`, and a read-only root filesystem where the process allows it.
- [ ] Trivy scan gates the push, the report is archived, and an SBOM is generated and attested to the image.
- [ ] Production images are signed by digest and the signature is verified by the deploy job.
- [ ] Registry retention enforced by a lifecycle policy.
