# Containerised end-to-end harness

A throwaway Debian container that installs all five supported agent command-line tools, builds a brand-new project
inside itself, imports this repository's shared configuration exactly the way
[docs/AGENT_TOOLING.md](../docs/AGENT_TOOLING.md) tells a consumer to, and then asks each agent what it can actually
see. Every assertion prints a `PASS` or a `FAIL` line and the run exits non-zero if anything failed.

The point is to catch the failure mode that documentation cannot catch on its own: the import looks right on disk, and
the agent still finds nothing, because a symlink flattened, a schema key changed, or a config file was rejected.

---

### What it proves

For each of the five agents, in the agent's own terms wherever the agent offers a way to ask:

| Agent | Skills | Subagents | Preflight wiring | MCP servers |
| --- | --- | --- | --- | --- |
| Claude Code | `.claude/skills` symlink resolves to all canonical skills | `.claude/agents/*.md` count matches canonical | `.claude/settings.json` calls the gate on `PreToolUse` | `claude mcp list` names every server |
| Codex | `.agents/skills/` read natively | `.codex/agents/*.toml` count matches canonical | `.codex/config.toml` calls the gate on `PreToolUse` | `codex mcp list` names every server |
| OpenCode | `.agents/skills/` read natively | `opencode agent list` names every imported subagent | `opencode.json` declares the shared plugin | `opencode mcp list` names every server |
| Kilo Code | `.agents/skills/` read natively | `kilocode agent list` names every imported subagent | `opencode.json` declares the shared plugin | `kilocode mcp list` names every server |
| GitHub Copilot | `copilot skill list` loads every skill without a parse error | `.github/agents/*.agent.md` count matches canonical | `.github/hooks/preflight.json` calls the gate on `preToolUse` | `copilot mcp list` names every server |

On top of that it proves the import itself behaved: `AGENTS.md.example` was renamed rather than copied, all three
symlinks resolve to directories, and the upstream-only `subagents/` and `tools/` trees did not come along.

It also proves the gate really denies. [.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py) is run
directly with the payload each adapter would hand it, once per output format, and the decision is read back:

- Rule A denies a main-thread edit of a source file, in all four formats.
- Rule A denies a shell redirect that writes into a source file.
- Rule B denies a subagent whose definition declares no skills, using a fixture agent the harness writes and deletes.
- A main-thread markdown edit is allowed, a subagent that declares skills is allowed, and a malformed payload fails
  open rather than blocking the session.

---

### What it cannot prove

Driving a real agent session needs provider credentials, so none of this happens in the container:

- No agent is asked to answer a prompt, so nothing here proves a model obeys the gate text it was shown.
- The `PreToolUse` and `preToolUse` hooks are never fired by the agent runtime itself. The harness proves the wiring
  points at the gate script and proves the gate script denies the right payloads. It does not prove the runtime
  delivers that payload in the shape the script expects.
- Skill selection quality is untested. Discovery is not the same as the agent choosing the right skill.
- The two GitHub Copilot surfaces that read no project file (JetBrains and the cloud agent) are out of reach, as is
  Copilot inside VS Code. Only the Copilot command-line tool is exercised.
- Every MCP server is listed, not proven healthy. Some fail to connect inside the container because `uvx` and `docker`
  are deliberately absent, which is a property of the container rather than of the configuration.

---

### Running it

Everything runs from the repository root. Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm --build harness
```

PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm --build harness
```

A cold run takes several minutes. Most of it is the container updating the five agent tools and then waiting on MCP
servers that cannot connect.

To reuse the versions already baked into the image and skip the update step, Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm -e HARNESS_SKIP_UPDATE=1 harness
```

PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm -e HARNESS_SKIP_UPDATE=1 harness
```

To poke around inside a prepared container instead of running the assertions, Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm harness /bin/bash
```

PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm harness /bin/bash
```

The image carries ShellCheck, so it can lint its own scripts. Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml run --rm --entrypoint shellcheck harness /harness/entrypoint.sh /harness/setup-project.sh /harness/verify.sh
```

PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml run --rm --entrypoint shellcheck harness /harness/entrypoint.sh /harness/setup-project.sh /harness/verify.sh
```

---

### What each file does

| File | What it does |
| --- | --- |
| [Dockerfile](Dockerfile) | Debian image with Node, Python, git, jq and ShellCheck, plus a baseline install of the five agent tools under a non-root user. |
| [entrypoint.sh](entrypoint.sh) | Updates every agent tool to its newest release, prints the resolved versions, then runs the container command. |
| [setup-project.sh](setup-project.sh) | Creates the empty project, runs the documented selective checkout against the mounted repository, and repairs and verifies the three symlinks. |
| [verify.sh](verify.sh) | Every assertion, one `PASS` or `FAIL` line each, exit 1 if any failed. Calls `setup-project.sh` first unless `HARNESS_SKIP_SETUP=1`. |
| [docker-compose.yml](docker-compose.yml) | Mounts the repository read-only at `/repo` and runs `verify.sh`. |

Versions are never pinned in the image. The baseline install exists only to warm the layer cache, and
[entrypoint.sh](entrypoint.sh) re-resolves every tool to `@latest` on container start, so testing against a newer
release needs no rebuild. Each run prints the versions it actually tested against, which is the line to quote when a
result needs reproducing.

---

### How the import is exercised

[setup-project.sh](setup-project.sh) follows the consumer flow from
[docs/AGENT_TOOLING.md](../docs/AGENT_TOOLING.md) step for step. The only substitution is the remote URL: instead of
the GitHub address it adds the mounted working tree at `/repo` as the `agent-standards` remote, so the harness tests
your local changes rather than whatever is already published.

The push URL is still set to `no_push`, the same selective checkout path list is used, and `AGENTS.md.example` is
renamed rather than copied. Git recreates the three symlinks from the tree, and the script recreates any that did not
arrive as links before verifying all three resolve to directories.

Codex needs one extra step that a human normally does by hand. It ignores the whole `.codex/` layer until the project
is trusted once, so [verify.sh](verify.sh) writes a trust record into the container's own `~/.codex/config.toml`
before asking `codex mcp list` anything. Without it Codex reports no MCP servers at all and the assertion would be
measuring the trust prompt rather than the configuration.

---

### Isolation from your machine

- The repository is bind-mounted read-only at `/repo`. A run cannot write to your working tree even by accident.
- The throwaway project lives at `/work/project` inside the container and is deleted and rebuilt on every run.
- Nothing from your home directory is mounted. Every agent tool installs into `/home/harness/.npm-global` and writes
  its state under `/home/harness`, which dies with the container.
- The container runs as the unprivileged `harness` user.
- Credentials are never supplied, so no agent can reach a provider.

---

### Defects this harness has already caught

The harness currently passes every assertion. Both failures it reported on its first run were real defects in the
repository rather than harness bugs, and both are fixed. They are recorded here because they show the class of
problem only a live run finds.

1. Kilo Code rejected the shared `opencode.json` outright. An `{env:VAR}` reference is banned in project-scope
   configuration, and Kilo discards the whole file rather than leaving the token literal, which took the `plugin`
   declaration carrying the preflight gate with it. Kilo Code had no gate at all. The shared file now carries no
   substitution token, and the one value that cannot be inherited from the process environment sits in an
   `.opencode/opencode.json` overlay that only OpenCode reads.
2. One skill had invalid YAML front matter. An unquoted colon in the `description` of
   `.agents/skills/nextjs-turbopack/SKILL.md` made GitHub Copilot skip the skill entirely. The value is quoted now,
   and a scan confirmed it was the only one of the 84 affected.

---

### Cleaning up

Remove the container and the image it built. Unix shell:

```bash
docker compose -f test-harness/docker-compose.yml down --rmi local
```

PowerShell:

```powershell
docker compose -f test-harness\docker-compose.yml down --rmi local
```
