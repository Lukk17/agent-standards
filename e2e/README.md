# End-to-end capability tests

Manual and AI-runnable e2e suite for this repository. Each test exercises one capability end-to-end against a live
stack and asserts only observable behaviour: process exit codes, what an agent's own listing command prints, and the
decision the preflight gate actually returns. Logs are diagnostic, never a pass criterion.

The live stack here is the container built by [sandbox-agent/](../sandbox-agent/README.md). It installs the five
supported agent command-line tools, mounts this repository read-only at `/repo`, and lets a runner build a consumer
project inside itself. The suites below drive that container. They do not replace
[verify.sh](../sandbox-agent/verify.sh), they restate the same behaviours as separately runnable, separately numbered
specs so a sweep reports a verdict per capability instead of one pass or fail for everything.

---

### What is here

```text
e2e/
├── README.md                                     # this file
├── fixtures/                                     # payloads and config files the specs read
│   ├── README.md
│   ├── e2e-no-skills-probe.md
│   ├── gate-payloads/
│   └── global/
└── testing/
    ├── README.md
    ├── 1-project-gate-decisions-test.md          # suite A, per-project setup
    ├── 2-project-import-shape-test.md
    ├── 3-project-agent-discovery-test.md
    ├── 4-project-mcp-visibility-test.md
    ├── 5-project-gate-subagent-rule-test.md
    ├── 6-global-install-shape-test.md            # suite B, global setup
    ├── 7-global-agent-discovery-test.md
    ├── 8-global-mcp-visibility-test.md
    ├── 9-global-gate-enforcement-test.md
    ├── templates/
    │   ├── README.md
    │   └── <N>-<capability>-tasks.template.md
    └── runs/
        ├── README.md
        └── <UTC-timestamp>_<N>-<capability>-tasks.md    # one per executed test, gitignored
```

Specs are number-prefixed by setup cost. `1` needs the least, higher numbers need more. The two suites share one
numeric sequence, and the second word of every filename says which suite a spec belongs to.

---

### The two suites

Suite A, specs 1 to 5, covers the per-project setup. It proves that a clean project which imported this repository's
shared configuration is seen correctly by every agent: skills discoverable, subagent definitions present in each
agent's own format, the preflight gate wired into the file that agent reads, MCP servers visible, and the gate
actually denying a main-thread source edit.

Suite B, specs 6 to 9, covers the global setup from [docs/global-setup.md](../docs/global-setup.md). It proves the
same four things for an installation into the container user's home directory.

Suite B has one design constraint that shapes every spec in it. A global install only counts as proven when the
assertions run from a directory that contains none of the per-project files, because otherwise there is no way to
tell which layer the agent read. So suite B works in a second bare directory, `/work/bare`, into which nothing is
ever imported, and every suite B spec asserts that bareness before it asserts anything else.

---

### What these suites cannot prove

Driving a real agent session needs provider credentials, and the container is never given any. That puts live model
behaviour out of scope. These suites prove discovery, wiring, and gate enforcement. They do not prove model
behaviour.

Concretely, out of scope:

1. No agent is asked to answer a prompt, so nothing here proves that a model obeys the gate text it was shown, or
   that it picks the right skill once it can see all of them. Discovery is not selection.
2. The `PreToolUse` and `preToolUse` hooks are never fired by an agent runtime. The specs prove the wiring points at
   the gate script, and prove the gate script decides correctly for the payload each adapter would hand it. They do
   not prove the runtime delivers that payload in the shape the script expects.
3. MCP servers are listed, not proven healthy. Several cannot connect inside the container because `uvx` and `docker`
   are deliberately absent, which is a property of the container rather than of the configuration.
4. Only the GitHub Copilot command-line tool is exercised. Copilot in VS Code, in JetBrains, and the cloud agent read
   no file the container can reach.
5. Both suites read the committed state of the mounted repository. The project import fetches from it as a git remote
   and the global install clones it, so uncommitted working-tree edits are invisible to every spec. Commit first,
   then run.

---

### Before a sweep

Every host command below runs from the [sandbox-agent/](../sandbox-agent/README.md) directory, which is where
Compose finds its `compose.yaml`. The same line works in PowerShell and in a Unix shell.

```bash
cd sandbox-agent
```

Build the image once, so no spec pays for it and no two specs contend for the build. PowerShell:

```powershell
docker compose build sandbox
```

Unix shell:

```bash
docker compose build sandbox
```

Every spec then starts its own throwaway container with `run --rm` and no `--build`. A fresh container per spec is
what keeps the specs independent. Each one gets its own `/work` and its own `$HOME`, both of which die with the
container, and the only shared surface is the read-only `/repo` mount.

---

### How a spec is executed

Every spec opens one interactive container shell as its first step. PowerShell:

```powershell
docker compose run --rm sandbox /bin/bash
```

Unix shell:

```bash
docker compose run --rm sandbox /bin/bash
```

Every later block in that spec is typed into that container shell, which is bash. Container blocks carry no
PowerShell variant, because the container has no PowerShell. Host blocks always give both.

Assertions are exit codes. After running an Expected block, read the exit status of the command it just ran:

```bash
echo $?
```

To skip the agent-tool update step and test the versions already baked into the image, add `-e SANDBOX_SKIP_UPDATE=1`
to the `run` command. A cold run without it spends several minutes updating the five tools.

---

### API client

There is no HTTP API under test here, so the client role is filled by two things: the `docker compose` command that
starts the container, and each agent's own command-line tool inside it. Where an agent offers a listing command, the
specs use it, because it answers in the agent's own terms rather than in the filesystem's. Claude Code publishes no
skills or subagents listing, so those two assertions fall back to path and count checks, which the specs say plainly.

The listing commands that work without credentials, established by the sandbox:

| Command | Notes |
| --- | --- |
| `claude mcp list` | works unauthenticated |
| `codex mcp list` | needs the working directory trusted first, which the specs do with a trust record |
| `opencode agent list`, `opencode mcp list` | work unauthenticated |
| `kilocode agent list`, `kilocode mcp list`, `kilocode config check` | work unauthenticated |
| `copilot skill list`, `copilot mcp list` | work unauthenticated |

---

### Flow

1. Read the spec at `testing/<N>-<capability>-test.md`.
2. Copy `testing/templates/<N>-<capability>-tasks.template.md` to
   `testing/runs/<UTC-timestamp>_<N>-<capability>-tasks.md`.
3. Record `Start (UTC)` as the very first action.
4. Execute prerequisites, then reset state, then run, then expected. Tick boxes as you go.
5. Record `End (UTC)` and compute Duration as HH:MM:SS.
6. Fill the Result summary, the Verdict, and any off-spec actions under "Additional tasks I did".

Full methodology in the [e2e-runbooks skill](../.agents/skills/e2e-runbooks/SKILL.md).

---

### Prerequisites before any test

Each spec lists its own concrete prerequisite checks. Common to all of them:

1. Docker is running on the host and `docker compose` resolves.
2. The `agent-standards-sandbox:local` image exists, built by the sweep step above.
3. The work under test is committed, because neither suite can see uncommitted edits.

---

### Adding a new test

This repository ships the [e2e-runbooks OpenSpec schema](../openspec/schemas/e2e-runbooks/README.md) these suites
were written from. With OpenSpec initialised, create the change:

```bash
openspec new change "add-<capability>-test" --schema e2e-runbooks
```

Without OpenSpec, follow the methodology in the [e2e-runbooks skill](../.agents/skills/e2e-runbooks/SKILL.md) and
hand-write the spec and its tasks-template in the same shape as the nine already here.
