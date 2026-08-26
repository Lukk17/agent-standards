# Containerised end-to-end sandbox

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
- Rule B denies a subagent whose definition declares no skills, using a fixture agent the sandbox writes and deletes.
- A main-thread markdown edit is allowed, a subagent that declares skills is allowed, and a malformed payload fails
  open rather than blocking the session.

---

### What it cannot prove

Driving a real agent session needs provider credentials, so none of this happens in the container:

- No agent is asked to answer a prompt, so nothing here proves a model obeys the gate text it was shown.
- The `PreToolUse` and `preToolUse` hooks are never fired by the agent runtime itself. The sandbox proves the wiring
  points at the gate script and proves the gate script denies the right payloads. It does not prove the runtime
  delivers that payload in the shape the script expects.
- Skill selection quality is untested. Discovery is not the same as the agent choosing the right skill.
- The two GitHub Copilot surfaces that read no project file (JetBrains and the cloud agent) are out of reach, as is
  Copilot inside VS Code. Only the Copilot command-line tool is exercised.
- Every MCP server is listed, not proven healthy. Some fail to connect inside the container because `uvx` and `docker`
  are deliberately absent, which is a property of the container rather than of the configuration.

---

### An OpenCode quirk the sandbox works around

`opencode agent list` truncates its own output at a random point whenever its stdout is a pipe, and still exits 0.
The same command writing to a file produces the whole listing. Discovery is not the problem. OpenCode finds all 30
imported subagents every time, it just stops writing them out partway through.

This is what made an early run report that OpenCode had not listed the last nine subagents alphabetically. OpenCode
had listed them, and the capture threw them away.

Measured inside the container against the imported project, where 30 imported subagents plus 7 OpenCode built-ins
mean 37 agent names per complete run:

| Capture method | Runs | Complete, 37 agents | Truncated |
| --- | --- | --- | --- |
| Pipe, `out="$(opencode agent list)"` | 15 | 7 | 8 |
| File, `opencode agent list > out.txt` | 35 | 35 | 0 |

The truncated runs stopped at a different byte offset every time, at 529883, 593826, 600024, 604120, 613728, 635033,
798760 and 821607 bytes out of a complete 940426, always mid-line and always with exit status 0.

That rules out the other explanations:

- Not a cap on how many agents it lists. A complete run names all 37, and every one of the 30 files under
  `.agents/agents` appears in it.
- Not a width or column limit. `COLUMNS=40` and `COLUMNS=400` both produce 940427 bytes with a longest line of 82
  characters.
- Not paging. No pager runs on a non-terminal stdout, and a pager would cut at the same boundary on every run rather
  than at a different one each time.
- Not a property of the shared tree. `kilocode agent list` reads the same `.agents/agents` directory in the same
  container and printed all 40 of its agents through the same kind of pipe on 10 runs out of 10.

Only the large listing is affected. `opencode mcp list` is 1037 bytes, small enough to sit in a single pipe buffer,
and never truncated in any run.

[verify.sh](verify.sh) therefore captures every agent command-line tool into a temporary file instead of a pipe, and
greps that file. The temporary file is removed by an exit trap. The assertion still says what it always said, that
OpenCode lists every imported subagent, and it is now measuring that rather than measuring how much of the answer
survived the pipe.

---

### Running it

Every command here runs from this directory, which is where Compose finds its `compose.yaml`. The same line
works in a Unix shell and in PowerShell.

```bash
cd sandbox-agent
```

Then run the assertions. Unix shell:

```bash
docker compose run --rm --build sandbox
```

PowerShell:

```powershell
docker compose run --rm --build sandbox
```

A cold run takes several minutes. Most of it is the container updating the five agent tools and then waiting on MCP
servers that cannot connect.

To reuse the versions already baked into the image and skip the update step, Unix shell:

```bash
docker compose run --rm -e SANDBOX_SKIP_UPDATE=1 sandbox
```

PowerShell:

```powershell
docker compose run --rm -e SANDBOX_SKIP_UPDATE=1 sandbox
```

To poke around inside a prepared container instead of running the assertions, Unix shell:

```bash
docker compose run --rm sandbox /bin/bash
```

PowerShell:

```powershell
docker compose run --rm sandbox /bin/bash
```

The image carries ShellCheck, so it can lint its own scripts. Unix shell:

```bash
docker compose run --rm --entrypoint shellcheck sandbox /sandbox/entrypoint.sh /sandbox/setup-project.sh /sandbox/verify.sh
```

PowerShell:

```powershell
docker compose run --rm --entrypoint shellcheck sandbox /sandbox/entrypoint.sh /sandbox/setup-project.sh /sandbox/verify.sh
```

---

### Running it on a Windows host

Two things behave differently when the host is Windows with Docker Desktop. Both were hit by every runner, and the
first one is now handled by the sandbox itself.

Git refuses to read the mounted repository. Docker Desktop presents a bind mount as owned by root, the container runs
as the unprivileged `sandbox` user, and git's dubious-ownership check then refuses any command that reads `/repo`. A
clone from the mount fails with exit 128 and this message:

```text
fatal: detected dubious ownership in repository at '/repo/.git'
```

Nothing downstream runs after that. [entrypoint.sh](entrypoint.sh) now marks both `/repo` and `/repo/.git` as git safe
directories for the container user before anything else happens, so every container is already correct when its
command starts. Two entries are needed rather than one, because git keys the check on the exact path it resolved. The
working-tree entry covers a command run inside the checkout, and a clone whose source is a path is checked against
that path's `.git` directory instead. The specs under [e2e/testing](../e2e/testing) mark only `/repo`, which is why
the global install used to fail on its very first clone while the per-project suite passed.

A broader entry, the `*` wildcard that trusts every repository, would also work and is defensible here. The container
is disposable, the mount is read-only, and no repository from an untrusted source ever reaches it, so the ownership
check is protecting nothing in this setting. The two explicit entries are still the better choice, because they say
out loud which paths are trusted and why. A wildcard would silently swallow the next path that trips the check, and
that path is precisely the signal worth seeing.

Git Bash rewrites arguments that look like Unix paths. MSYS, the environment Git Bash runs on, converts any argument
starting with a forward slash into a Windows path before the program ever sees it, so `/bin/bash` reaches Docker as
something like `C:/Program Files/Git/usr/bin/bash` and the container dies with exit 127 and a "no such file or
directory" from the runtime. Prefix the run with `MSYS_NO_PATHCONV=1`.

Git Bash:

```bash
MSYS_NO_PATHCONV=1 docker compose run --rm sandbox /bin/bash
```

PowerShell and cmd do no such rewriting, so the PowerShell commands above need nothing extra.

---

### What each file does

| File | What it does |
| --- | --- |
| [Dockerfile](Dockerfile) | Debian image with Node, Python, git, jq and ShellCheck, plus a baseline install of the five agent tools under a non-root user. |
| [entrypoint.sh](entrypoint.sh) | Marks `/repo` and `/repo/.git` as git safe directories, updates every agent tool to its newest release, prints the resolved versions, then runs the container command. |
| [setup-project.sh](setup-project.sh) | Creates the empty project, marks the same two paths plus the project itself as safe, runs the documented selective checkout against the mounted repository, and repairs and verifies the three symlinks. |
| [verify.sh](verify.sh) | Every assertion, one `PASS` or `FAIL` line each, exit 1 if any failed. Calls `setup-project.sh` first unless `SANDBOX_SKIP_SETUP=1`. |
| [compose.yaml](compose.yaml) | Mounts the repository read-only at `/repo`, drops every Linux capability, and runs `verify.sh`. |
| [.dockerignore](.dockerignore) | Keeps the README and the Compose file out of the build context, so editing either one does not bust the image cache. |

Versions are never pinned in the image. The baseline install exists only to warm the layer cache, and
[entrypoint.sh](entrypoint.sh) re-resolves every tool to `@latest` on container start, so testing against a newer
release needs no rebuild. Each run prints the versions it actually tested against, which is the line to quote when a
result needs reproducing.

---

### How the import is exercised

[setup-project.sh](setup-project.sh) follows the consumer flow from
[docs/AGENT_TOOLING.md](../docs/AGENT_TOOLING.md) step for step. The only substitution is the remote URL: instead of
the GitHub address it adds the mounted working tree at `/repo` as the `agent-standards` remote, so the sandbox tests
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
- Nothing from your home directory is mounted. Every agent tool installs into `/home/sandbox/.npm-global` and writes
  its state under `/home/sandbox`, which dies with the container.
- The container runs as the unprivileged `sandbox` user.
- Credentials are never supplied, so no agent can reach a provider.

---

### Defects this sandbox has already caught

The sandbox currently passes every assertion. Both failures it reported on its first run were real defects in the
repository rather than sandbox bugs, and both are fixed. They are recorded here because they show the class of
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
docker compose down --rmi local
```

PowerShell:

```powershell
docker compose down --rmi local
```
