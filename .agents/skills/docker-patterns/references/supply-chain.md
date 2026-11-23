# Supply chain commands: Trivy, syft and cosign

The supply-chain rules are canonical for the repository in [SKILL.md](../SKILL.md), under "Supply chain: scan, bill of materials, signature", and other skills point there. This file carries the commands: the scan with Trivy, the CycloneDX bill of materials with syft, and the signature, the attestation and the verification with cosign.

---

### Scan with Trivy

Scan every image in CI before it is pushed, and fail the build on a fixable critical or high finding:

```bash
trivy image --exit-code 1 --severity CRITICAL,HIGH myimage:tag
```

Store the scan report as a CI artifact, so a later question about what was known at release time has an answer.

---

### Bill of materials with syft

Generate a Software Bill of Materials after push, in CycloneDX form:

```bash
syft myimage:tag -o cyclonedx-json > sbom.json
```

---

### Sign, attest and verify with cosign

Sign, attest, and verify the image by the digest the push reported, never by tag. A tag can move between the push and
the signature, so signing by tag can sign a different image, and cosign warns when it is given one. The pipeline
form, which reads the digest from the build step, is in `deployment-patterns`.

Attach the SBOM to the pushed image as a signed attestation, so it travels with the image in the registry:

```bash
cosign attest --key cosign.key --type cyclonedx --predicate sbom.json myregistry/myimage@sha256:<digest>
```

Sign every production image after push:

```bash
cosign sign --key cosign.key myregistry/myimage@sha256:<digest>
```

Verify before deploy, in the pipeline, not by hand:

```bash
cosign verify --key cosign.pub myregistry/myimage@sha256:<digest>
```

A signature nothing verifies proves nothing. The verify step belongs in the deploy job, gating it, and a cluster
policy should reject an unsigned image outright.
