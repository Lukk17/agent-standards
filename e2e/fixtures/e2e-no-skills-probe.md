---
name: e2e-no-skills-probe
description: Canary subagent definition that deliberately declares no skills, used by the e2e suites to exercise rule B of the preflight gate. Never invoke it.
---

E2E-GATE-CANARY-9134. This definition exists only so the preflight gate has a subagent that declares no skills to
refuse. It names no skills in its front matter and carries no preloaded-skills section in its body, which is exactly
the shape rule B must deny. Copy it into the agent directory under test, run the gate, then delete it.
