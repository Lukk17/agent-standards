# e2e fixtures

Files the specs read. In a service project these would be canary documents with content no model could have
memorised, because the test proves retrieval. These suites prove discovery, wiring, and gate enforcement instead, so
the fixtures here are inputs of two kinds: hook payloads fed to the preflight gate, and configuration files copied
into the container's home directory during the global install. Neither kind needs a retrieval canary, and saying so
is more honest than inventing one.

The one place a canary still earns its keep is
[e2e-no-skills-probe.md](e2e-no-skills-probe.md). It carries the marker `E2E-GATE-CANARY-9134` so a run record can
show which definition the gate refused, and so a stray copy left behind in a real agent directory is greppable.

---

### Conventions

1. Fixtures are read-only inputs. A spec copies a fixture into place, it never edits one.
2. Every fixture a spec writes into an agent directory is deleted again in the same spec, and the spec says so under
   Reset state.
3. The global fixtures hard-code the container paths `/home/sandbox` and `/work/bare`. They are container inputs, not
   templates for a real machine. The real per-machine instructions are in
   [docs/global-setup.md](../../docs/global-setup.md).
4. The global MCP fixtures carry only the two servers that are genuinely machine-wide, Context7 and Playwright, which
   is what [docs/global-setup.md](../../docs/global-setup.md) tells a reader to keep at user scope. They also use
   literal values rather than `{env:VAR}` or `${VAR}` references, so no assertion can fail because a variable was
   unset in the container.

---

### Per-fixture documentation

| File | Used by | Distinctive content |
| --- | --- | --- |
| `e2e-no-skills-probe.md` | tests 5 and 9 | Subagent definition with `E2E-GATE-CANARY-9134` that declares no skills anywhere |
| `gate-payloads/main-thread-source-edit.json` | tests 1 and 9 | Main-thread `Edit` of `src/e2e_canary_app.py` |
| `gate-payloads/main-thread-markdown-edit.json` | test 1 | Main-thread `Edit` of `docs/e2e-canary-note.md` |
| `gate-payloads/main-thread-shell-redirect.json` | test 1 | `Bash` command redirecting into `src/e2e_canary_app.py` |
| `gate-payloads/subagent-with-skills.json` | tests 5 and 9 | Subagent payload naming `code-reviewer`, which declares skills |
| `gate-payloads/subagent-without-skills.json` | tests 5 and 9 | Subagent payload naming `e2e-no-skills-probe` |
| `gate-payloads/malformed.txt` | test 1 | Not JSON, so the gate has to fail open |
| `global/claude-settings.json` | tests 6 and 9 | User-scope Claude Code hooks calling the gate at `/home/sandbox/.agents/hooks/` |
| `global/claude-CLAUDE.md` | test 6 | The single `@~/.agents/AGENTS.md` import line |
| `global/codex-hooks.json` | test 6 | User-scope Codex hooks calling the gate by absolute path |
| `global/codex-config.toml` | test 8 | Two `[mcp_servers]` tables plus the trust record for `/work/bare` |
| `global/opencode.json` | tests 7 and 8 | Global OpenCode config with the two machine-wide servers |
| `global/kilo.jsonc` | tests 7 and 8 | Global Kilo config with `skills.paths`, `instructions`, and the same two servers |
| `global/copilot-mcp-config.json` | test 8 | Copilot command-line MCP config keyed `mcpServers` |
