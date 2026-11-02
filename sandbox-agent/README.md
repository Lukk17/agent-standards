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
| Claude Code | `.claude/skills` symlink resolves to all canonical skills | `.claude/agents/*.md` count matches canonical | `.claude/settings.json` calls the gate on `PreToolUse` | `claude mcp list` names every server in `.mcp.json` |
| Codex | `.agents/skills/` read natively | `.codex/agents/*.toml` count matches canonical | `.codex/config.toml` calls the gate on `PreToolUse` | `codex mcp list` names every server in `.codex/config.toml` |
| OpenCode | `.agents/skills/` read natively | `opencode agent list` names every imported subagent | `opencode.json` declares the shared plugin | `opencode mcp list` names every server in `opencode.json` |
| OpenCode 2.x | the same project, run as `opencode2` | a real turn starts subagent `docs-architect` | the plugin loads from its directory entry and the gate blocks a real main-thread write | none, the probe copy drops the MCP block |
| Kilo Code | `.agents/skills/` read natively | `kilocode agent list` names every imported subagent | `opencode.json` declares the shared plugin | `kilocode mcp list` names every server in `opencode.json` |
| GitHub Copilot | `copilot skill list` loads every skill without a parse error | `.github/agents/*.agent.md` count matches canonical, each front matter safe for Copilot to parse | `.github/hooks/preflight.json` calls the gate on `preToolUse` | `copilot mcp list` names every server in `.mcp.json` |

On top of that it proves the import itself behaved: `AGENTS.md.example` was renamed rather than copied, all three
symlinks resolve to directories, and the upstream-only `subagents/` and `tools/` trees did not come along.

It also proves the gate really denies. [.agents/hooks/preflight_gate.py](../.agents/hooks/preflight_gate.py) is run
directly with the payload each adapter would hand it, once per output format, and the decision is read back:

- Rule A denies a main-thread write of any file inside the working tree, markdown and configuration included, in
  three of the four formats: `claude`, `codex`, and `plain`.
- On the `copilot` format the payload carries no agent identifier, so the gate cannot tell a subagent from the main
  thread and allows the same edit. The sandbox asserts that allowance deliberately, rather than losing sight of it.
- Rule A denies a shell redirect that writes into a source file.
- Rule B denies a subagent whose definition declares no skills, using a fixture agent the sandbox writes and deletes.
- A subagent that declares skills is allowed, and a malformed payload fails open rather than blocking the session.

---

### OpenCode 2.x beside 1.x

Every run covers OpenCode 1.x, OpenCode 2.x and Kilo Code. OpenCode 2.x is a different npm package, `@opencode/cli`, and its install page says "The npm package uses a postinstall script to select the native `opencode` binary for your platform" (https://opencode.ai/v2/docs/). Both packages own the `opencode` binary name, so 2.x is installed into its own prefix, `/home/sandbox/.opencode-v2`, and reaches `PATH` only through the [opencode2.sh](opencode2.sh) wrapper, installed as `opencode2`.

The wrapper moves 2.x to its own data directory, `~/.local/share/opencode-v2`, because both majors keep their database at `$XDG_DATA_HOME/opencode/opencode.db`. Measured in the container with 1.18.25 and 2.0.28: once a 2.x turn has created that file on the shared path, `opencode agent list` exits 1 with `Database is not empty and has no session table`. The configuration directory stays shared, which is the part the suites assert on.

No 2.x assertion reads a configuration file alone. Each one runs a real 2.x turn against [mock-model.mjs](mock-model.mjs), a stdlib Node server that speaks the OpenAI chat completions format, answers from a script keyed on a marker in the prompt, and logs every request body. The provider block follows the custom provider example at https://opencode.ai/v2/docs/providers/. Every turn uses `run --standalone`, so no background service outlives it and no earlier plugin load answers for a later turn. [lib-opencode2.sh](lib-opencode2.sh) holds the assertions both suites share:

- the plugin logs `loading plugin` with `entrypoint=file://<plugin directory>/index.js`, and no `configured plugin path must be a directory` warning, which is what 2.x logs when the entry names `hooks.js` instead
- a main-thread `write` tool call comes back with the gate's `PREFLIGHT: the main thread may not write files directly` refusal, and the file does not exist afterwards
- every agent turn of the main session carries `reply-rules.md` in a system message, and every turn of a `docs-architect` subagent carries none. The title request 2.x makes from the prompt offers no tools and is not counted.
- the 2.x database sits in its own data directory, and 1.x still starts after 2.x ran
- the 2.x turns tried to start no MCP server

The project suite runs 2.x in a copy of the imported project with the MCP block and `.mcp.json` removed, because the copy also carries the 2.x-only `providers` key. The global suite runs it in a temporary directory holding only the provider block, before the MCP fixtures land in the user configuration.

The project suite also drives OpenCode 1.x and Kilo Code through real turns against the same mock, in its own MCP-free copy of the project, with the provider passed in `OPENCODE_CONFIG_CONTENT` and `KILO_CONFIG_CONTENT` and the session database in a temporary directory. `verify_reply_style_v1` in [lib-opencode2.sh](lib-opencode2.sh) asserts on each runtime that reply style is a main-thread matter while the gate covers every session. The prose the mock writes carries an em dash, which the text rewrite fixes, and a semicolon and an unnumbered question, which only the tool-call checks refuse. A runtime stores a reply's prose only after that reply's own tool call has started, so the mock follows each prose with two glob calls, and the second one is where a check reads the prose.

- the main session's stored prose has lost its em dash, and its second glob is refused with `Formatting violation in your last reply`
- a `docs-architect` subagent started through the `task` tool keeps its em dash, and both of its glob calls run
- a main-thread `write` is refused by the gate and the file does not exist afterwards
- a subagent whose definition declares no skills is refused by rule B inside its own session

---

### A real subagent writes a real file, on every agent

The last mock section of the project suite proves on every pull request that a subagent really writes a file, for all six runtimes: Claude Code, Codex, the GitHub Copilot CLI, OpenCode 2.x, OpenCode 1.x with the `.v1` backstop, and Kilo Code. Each one is the binary the [Dockerfile](Dockerfile) pins, run headless in its own copy of the imported project, with the hooks, the gate and the generated subagents as imported. Only the model is replaced, by [e2e-mock/server.mjs](e2e-mock/server.mjs), a stdlib Node server that replays a scripted conversation, so a run needs no key and costs nothing. [e2e-mock/subagent-write.sh](e2e-mock/subagent-write.sh) drives it, and [verify-project.sh](verify-project.sh) sources it.

Each agent runs two scripted cases. In the first, the main thread is asked to have `python-pro` create `e2e-subagent-proof.txt`. The mock answers the main thread with that agent's own spawn tool call, answers the subagent's first turn with a write tool call carrying the fixed content, and ends both turns with text. On Codex, whose `spawn_agent` returns at once, the main thread also calls `wait_agent` on the id the spawn returned. In the second, the main thread is asked to write a file itself, and the mock answers with the write call the gate has to refuse. Claude Code runs a third: the main thread starts the project's `code-reviewer`, whose definition preloads `security-review`, and the mock ends the subagent's first turn at once, so that request shows what Claude Code preloaded.

| Agent | Wire format and route | How the binary reaches the mock | Spawn call | Write call | Header that marks a subagent request |
| --- | --- | --- | --- | --- | --- |
| Claude Code | Anthropic Messages, `/v1/messages` | `ANTHROPIC_BASE_URL`, every model alias variable, `--strict-mcp-config` with no server, `--permission-mode acceptEdits` | `Agent` | `Write` | `x-claude-code-agent-id` |
| Codex | OpenAI Responses, `/v1/responses` | a throwaway `CODEX_HOME/config.toml` provider with `wire_api = "responses"`, a trust record, and `-c mcp_servers.<name>.enabled=false` for every server | `spawn_agent` in the `multi_agent_v1` namespace, `fork_context` false | `exec_command` with a shell redirect, the only writer Codex offers a model it has no metadata for | `thread_source` `subagent` in `x-codex-turn-metadata` |
| GitHub Copilot CLI | OpenAI Responses, `/v1/responses` | `COPILOT_PROVIDER_*` with `COPILOT_OFFLINE`, as [live/copilot.sh](live/copilot.sh) sets them, and `--disable-mcp-server` for every server | `task` in `sync` mode | `create` | `x-interaction-type: conversation-subagent` |
| OpenCode 2.x | OpenAI Chat Completions | the `providers` block from [lib-opencode2.sh](lib-opencode2.sh), MCP block removed | `subagent` | `write` | `x-parent-session-id` |
| OpenCode 1.x, Kilo Code | OpenAI Chat Completions | `OPENCODE_CONFIG_CONTENT` and `KILO_CONFIG_CONTENT` from `v1_config`, MCP block removed | `task` | `write` | `x-parent-session-id` |

The mock places every request twice. The newest user message carrying a scripted marker says which session it belongs to, because a subagent's prompt is a user message only inside its own session. The headers in the table say it independently, measured on the pinned binaries. A request whose two answers disagree gets text only, so a mixed-up session can never make the scripted write. Every request is logged with both answers, the tool calls since the marker paired with the results the agent sent back, and its flattened system and message text.

An agent passes when all of these hold, each its own `PASS` or `FAIL` line:

- `e2e-subagent-proof.txt` exists with exactly the scripted content
- the main thread's spawn call got a result, a request that both the marker and the headers place in the subagent got the result of the write call, no main-thread request carries a write of that file, and the agent's own record agrees: [e2e-mock/records.py](e2e-mock/records.py) reads the Claude Code subagent transcript, the Codex rollout whose `session_meta` names a subagent, the Copilot event carrying a `parentToolCallId`, the OpenCode 1.x and Kilo Code export of the child session, or the 2.x `session_v2` row with a `parent_id`, and finds the write there and not in the main session
- every subagent turn carries `python-pro`'s own definition in its system text
- every main-thread turn carries that agent's own main-thread reminder: the Claude Code reminder from `.claude/settings.json` on Claude Code, and on every other agent the `REMINDER` of `.agents/hooks/copilot/prompt_reminder.py`, which Codex and Copilot inject from their wiring and the OpenCode plugin reads from that file
- every subagent turn carries the subagent text, `PREFLIGHT for a subagent:`, and none carries either main-thread reminder. Every text is read from the imported project, the subagent opening from `.agents/hooks/copilot/prompt_reminder.py`, so a change of wording moves the check with it
- the main thread's own write is refused with the gate's `RULE_A_REASON`, read from the imported gate, and the file was never created
- on Claude Code, every `code-reviewer` turn carries the first prose line of the project's `.agents/skills/security-review/SKILL.md`, read at run time, and none carries the opening of the built-in `/security-review` command's prompt, `You are a senior security engineer conducting a focused security review of the changes on this branch.`, read from the pinned 2.1.314 binary. The check first confirms that line is still in the `claude` binary it runs, so its absence from the request means the project skill won the name

GitHub Copilot reports one `KNOWN-GAP`, the way live test 1 does, and it does not fail the run: the main thread's own write lands, because the Copilot `preToolUse` payload carries no agent identifier, as the Maintenance follow-ups in [AGENTS.md](../AGENTS.md) record. A Copilot subagent that does not write the file is a plain `FAIL`.

Measured on 2026-11-01 without Docker, with Claude Code 2.1.314, Codex 0.166.0, Copilot CLI 1.0.103, OpenCode 1.18.25, OpenCode 2.0.28 and Kilo Code 7.5.5, the twelve runs took 52 to 55 seconds together, over three repeats with the same result. The main-thread reminder and `code-reviewer` checks were added the same day and passed on the same versions. With the plugin as it stood before the reminder was restored, OpenCode 1.x, OpenCode 2.x and Kilo Code each failed the main-thread reminder check with 0 of 2 turns. Each OpenCode 1.x and Kilo Code case keeps its own data directory, because on Kilo Code 7.5.5 a run in a data directory where `kilocode export` had read a child session hung before its first model request in 2 of 4 tries. To run the check on its own against a project that was already imported, from the repository root, Unix shell:

```bash
bash sandbox-agent/e2e-mock/subagent-write.sh /work/project
```

PowerShell:

```powershell
bash sandbox-agent/e2e-mock/subagent-write.sh /work/project
```

Name agents after the project to run only those, out of `claude-code`, `codex`, `copilot`, `opencode2`, `opencode` and `kilo-code`. `SANDBOX_E2E_KEEP=1` keeps the work directory with every request log, stream and record, and `SANDBOX_E2E_TIMEOUT` bounds each run, 120 seconds by default.

---

### What it cannot prove

A real model needs provider credentials, so none answers in the container:

- Every turn the container drives is answered by a scripted mock, which makes the tool calls it was scripted to make whatever text it was shown, so nothing here proves a real model obeys the gate text or delegates on its own.
- The subagent-write section fires every hook through the agent runtime itself, on all six runtimes, and proves there that the gate lets a subagent's write through and, on every runtime but the Copilot CLI, whose payload carries no agent identifier, refuses a main-thread write. The rest of the suite drives the gate script directly with the payload each adapter would send, so only the rules that section exercises, rule A and a skilled subagent's write, are proven on the payload the runtime really delivers.
- Skill selection quality is untested. Discovery is not the same as the agent choosing the right skill.
- The two GitHub Copilot surfaces that read no project file (JetBrains and the cloud agent) are out of reach, as is
  Copilot inside VS Code. Only the Copilot command-line tool is exercised.
- Every MCP server is listed, not proven healthy. Some fail to connect inside the container because `uvx` and `docker`
  are deliberately absent, which is a property of the container rather than of the configuration. The live tests
  below prove one server, `context7`, against a real model, and none of the others.

The first three gaps are what the live tests below close, at the price of a funded key.

---

### Live tests against a real model

[agent-live-tests.yml](../.github/workflows/agent-live-tests.yml) installs each agent at the version the
[Dockerfile](Dockerfile) pins, points it at a real model through Requesty or OpenAI, and runs it headless in a fresh
project that imported this repository the way a consumer does. Every verdict is read from the tool calls and hook
events the agent recorded, never from what the model wrote back.

| Test | Passes when |
| --- | --- |
| 1 Gate blocks the main thread | The main thread tried to write a file, the gate's denial is in the transcript, and the file is absent or was written only by a subagent the model started after the denial |
| 2 A named subagent writes | The main thread started `docs-architect`, the recorded write of the file came from the subagent, and what the agent's hooks injected into the subagent carries the subagent text (`PREFLIGHT for a subagent:`) and not the main-thread reminder. A project `AGENTS.md`, a tool result, the model's own text and history a Codex fork inherited from the main thread are not hook output and do not count |
| 3 A skill is loaded | The main thread loaded the `kicad` skill through its skill tool or by reading its `SKILL.md` |
| 4 The reminder reaches the model | The per-prompt reminder text is in the recorded context of that prompt, not only the session start. On OpenCode and Kilo Code only a synthetic part the plugin added to the main-session user message that carries this prompt's nonce counts, never the typed prompt or the model's reply |
| 5 Key and model | One tiny request in the agent's own wire format is answered by the agent's provider |
| 6 The one MCP server answers | `context7` is the only MCP server the session loaded, and a recorded `resolve-library-id` call for React returned a library id. A call whose result carries no id, such as a rate-limit or an invalid-key answer, is a `FAIL` quoting that result |
| 7 Codex only: a subagent's payload names its type | The main thread started the read-only `code-reviewer`, and a `PreToolUse` payload the capture hook placed in the reviewer's own rollout, for any tool, carried `agent_id` and `agent_type` `code-reviewer`. A placed payload without either fails, and only a case with no placed payload is `INCONCLUSIVE` |
| 7b Codex only: Rule E denies the reviewer's touch | The reviewer ran `touch readonly-probe.txt`, the payload of that call carried `agent_id` and `agent_type` `code-reviewer`, Rule E's reason is in the transcript, and the file is absent. A reviewer that never tried the touch is `INCONCLUSIVE` |
| 8 Claude Code only: the gate sees a plugin subagent | The same probe from `review-and-security:code-reviewer`, installed from the rendered marketplace, carried `agent_type` `review-and-security:code-reviewer`, Rule E denied it, and the file is absent |
| 9 Claude Code only: a plugin subagent preloads a `core` skill | `review-and-security:code-reviewer` returned a canary that only its preloaded `core` skill `security-review` carries, in the spawn result or, for a spawn run in the background, in its own reply or the task notification Claude Code handed the main thread, with no run-time load of that skill anywhere in the session |

Three verdicts are possible besides a pass:

- `FAIL` means the agent did the thing and the configuration did not behave, or the provider rejected the agent's
  own model request so the model never ran. It fails the job.
- `INCONCLUSIVE` means the model never attempted the tool call the test needs, so nothing was proven either way. It
  raises a warning and does not fail the job.
- `KNOWN-GAP` appears on GitHub Copilot for test 1 only: its payload carries no agent identifier, so the gate
  cannot tell the main thread from a subagent, as the Maintenance follow-ups in AGENTS.md already record. It does not
  fail the job. Codex tests 7 and 7b have no `KNOWN-GAP` any more: live run 41348146352 measured `agent_id` and
  `agent_type` on a Codex 0.166.0 subagent's `PreToolUse` payload, so a subagent payload without them is a `FAIL`.

Test 1 counts any gate denial as the block, whichever rule gave it, because [live/lib.sh](live/lib.sh) reads the fixed
text of every `RULE_*_REASON` out of the gate itself, so a new rule needs no harness change. A probe file that landed
is a failure whatever the transcript says. Test 2 reads what the hooks injected into the subagent through the
`agent_subagent_context` function each agent script supplies. The Copilot expectation is a switch in
[live/copilot.sh](live/copilot.sh), `GATE_KNOWN_GAP=1` for test 1, which every other agent script sets to `0`. It goes
in the same change that removes its Maintenance follow-up in [AGENTS.md](../AGENTS.md).

#### How tests 7 to 9 measure the payload

Tests 7 and 8 read the hook payload itself rather than the gate's verdict, because on Codex a payload with no
`agent_id` is read as the main thread and denied by Rule A, which would look like the Rule E denial the test expects.
A capture hook, written by [live/lib.sh](live/lib.sh) under the work directory and never into the project, records
for every `PreToolUse` call the payload's key names, whether `agent_id` is there, the `agent_type` value, whether
the shell command names the probe file, and the file name alone of the transcript the payload names. It keeps no other
value and always allows, and runs as `python3 -I -S`, so no `PYTHON*` variable, user site or module beside the
script reaches it. Codex gets it in the
throwaway `CODEX_HOME/config.toml`, and Codex "loads all matching hooks" from every layer, so it runs beside the
project's gate (`https://developers.openai.com/codex/hooks`, "Where Codex looks for hooks"). Claude Code gets it in
the user settings of a separate `CLAUDE_CONFIG_DIR`. Each case keeps what it captured as `payloads.ndjson` beside its
transcripts. A case where the capture hook recorded nothing, or the subagent never ran the probe, is `INCONCLUSIVE`
for tests 7b and 8. Test 7 asks only whether a Codex subagent's payload names its type, so it reads every payload
the hook placed in the reviewer's own rollout by its transcript name, `agent_id` playing no part in the placement,
whatever tool the call was for: in live run 41348146352 the reviewer never ran the touch, yet its `send_message`
call carried both fields.

A payload with `agent_id` is the subagent's, since both agents send it only inside one. A payload without it is
placed by its transcript name: on Codex the rollout of that name says whether the thread was the main one or a spawned
agent, and on Claude Code only a copied subagent transcript counts, because there `transcript_path` is the main
session's transcript and a subagent's own sits in `agent_transcript_path` (`https://code.claude.com/docs/en/hooks`,
SubagentStop). So a main thread that ran the probe itself never hides a subagent payload without `agent_id`, which
still fails. A subagent touch that landed while the hook recorded no payload for it fails too, because the gate never
saw the call. The prompt has the subagent answer only "allowed" or "denied", so the gate's reason stays in the
subagent's own transcript rather than in the spawn result, where the Codex parser reads `PREFLIGHT:` as an error. A
spawn the transcript marks as failed while the subagent's own calls are recorded is not reported as rejected.

Tests 8 and 9 render the marketplace with [tools/gen_plugins.py](../tools/gen_plugins.py) into the work directory,
which the job's own Python step installs the tooling for, and append a random preload marker, the canary, to that copy of the `core` skill
`security-review` only. Each plugin subagent preloads its skills by their full plugin name, such as `core:security-review`, because a bare `security-review` resolved to the built-in `/security-review` command in live run 41255837007. They add it as a local marketplace and install `review-and-security`, which pulls `core` in as
its dependency, into a separate `CLAUDE_CONFIG_DIR`, and run in a second project that holds only the gate-only import,
`.agents/hooks` and `.claude/settings.json`. With no agent tree in that project, the gate can find the reviewer's
definition only in the plugin cache, so a Rule E denial in test 8 proves that lookup. Tests 1 to 6 keep their own
configuration and never see the plugin. Test 9 asks the subagent to repeat the canary without any tool. A spawn
Claude Code runs in the background returns only "Async agent launched successfully", so the check also reads the
subagent's own assistant text and the task notification that carries its final message to the main thread, through
the `agent_subagent_replies` function in [live/claude-code.sh](live/claude-code.sh), never a loaded skill or the main
thread's own text. In live run 41348146352 the spawn result was that launch notice while the reviewer's reply was
exactly the canary. A recorded `Skill` call or `SKILL.md` read of `security-review`, a subagent tool result holding the
canary, a main-thread call input holding it, or hook text injected into the subagent holding it makes it
`INCONCLUSIVE`, because the canary then no longer proves the preload. Each run first clears
the marketplace, the plugin configuration, the plugin project and cases 8 and 9 that an earlier run in the same
`LIVE_WORK` left, and runs both `claude plugin` commands from the work directory at `--scope user`, with stdin closed
and a 120 second limit. A missing reviewer definition, capture hook or gate-only project blocks both tests. A canary
that could not be planted or did not survive the install fails test 9 alone, and test 8 still runs.

#### One MCP server in the live runs

Each live project runs with `context7` alone, out of the servers the repository ships. With all of them, every
model request carried about 34,500 tokens of MCP tool descriptions, and Copilot's subagent test alone used 206,000
tokens, above the 200,000 tokens per minute the OpenAI key allows. None of tests 1 to 4 needs an MCP server, so the
others only cost tokens. One server stays so that test 6 still proves the MCP setup works against a real model.

`context7` is the one because it has the smallest tool descriptions, needs no secret on its free tier, and runs
headless on a GitHub runner. Each size below is the JSON of the server's own `tools/list` answer at its `@latest`
release on 2026-09-25, and the token figure assumes four characters per token:

| Server | Tools | Characters | About this many tokens | Why it is not the one |
| --- | --- | --- | --- | --- |
| `context7` | 2 | 4,937 | 1,200 | Kept |
| `n8n` | 7 | 12,408 | 3,100 | Two and a half times the size, and its control tools need an n8n instance |
| `playwright` | 25 | 21,143 | 5,300 | Downloads browsers on first use |
| `chrome-devtools` | 30 | 27,710 | 6,900 | Needs Chrome |
| `redis` | 53 | 40,383 | 10,100 | Needs a running Redis |
| `mongodb` | 20 | 60,158 | 15,000 | Needs a running MongoDB |
| `grafana` | 81 | 106,016 | 26,500 | Needs a Grafana instance and a token |
| `sonarqube` | not measured | | | Exits before its handshake without `SONARQUBE_TOKEN`, so it needs a secret |
| `home-assistant` | not measured | | | Needs a Home Assistant instance and a token in the credential env file, and `uvx` refuses to start it when that file is missing |

Every agent keeps the others out through its own documented mechanism, working from a filtered copy of its own MCP
file or from overrides, and never from an edited repository file:

| Agent | Mechanism | Vendor source |
| --- | --- | --- |
| Claude Code | `--strict-mcp-config --mcp-config` with a copy of `.mcp.json` that holds only `context7` | `https://code.claude.com/docs/en/cli-reference` |
| Codex | `-c mcp_servers.<name>.enabled=false` for every other server in `.codex/config.toml`, plus `mcp_optional_startup_grace_ms = 0`, which makes the first tool list wait for each server's own `startup_timeout_sec` instead of the shared 1 second default, and `-c mcp_servers.context7.startup_timeout_sec=60`, which raises that wait for `context7` from the 10 second default | `https://developers.openai.com/codex/config-reference` |
| OpenCode | `"enabled": false` on every other server in `OPENCODE_CONFIG_CONTENT`, which outranks the project's `opencode.json` | `https://opencode.ai/docs/mcp-servers/` and `https://opencode.ai/docs/config/` |
| Kilo Code | The same in `KILO_CONFIG_CONTENT` | `https://kilo.ai/docs/automate/mcp/using-in-kilo-code` and `https://kilo.ai/docs/getting-started/settings` |
| GitHub Copilot | `--disable-builtin-mcps`, `--disable-mcp-server` for every other server, and `--additional-mcp-config` with a copy of `.github/mcp.json` that holds only `context7` | `https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference` |

Copilot gets the extra override because it reads `context7` from `.mcp.json`, and with no `CONTEXT7_API_KEY` set
the `${CONTEXT7_API_KEY:-}` entry there reaches Context7 as an empty header, measured on Copilot CLI 1.0.103 on
2026-10-25. How Context7 answers an empty header was not measured. The override is the `context7` block of
`.github/mcp.json`, which sends no header at all, and the reference ranks `--additional-mcp-config` "(highest)" under
"MCP server loading priority", so the call goes out with no header and the free tier answers.

Test 6 reads the loaded servers where the agent records them: the `system/init` event on Claude Code and the
`session.mcp_servers_loaded` event on Copilot. Codex, OpenCode and Kilo Code record no server list in their sessions,
so the harness asks the agent itself with `mcp list` under the same configuration and keeps the answer beside the
transcripts.

What the live runs therefore do not prove: that any of the other servers starts, authenticates or answers a
tool call inside a real session. The containerised suite above still checks, for every agent, that its own `mcp list`
names every server in the file that agent reads: `.mcp.json` for Claude Code and GitHub Copilot, `.codex/config.toml`
for Codex, and `opencode.json` for OpenCode and Kilo Code. So discovery of each agent's full set stays covered on
every pull request.

Test 5 runs first, as its own step, and the job stops there with one plain cause when the provider refuses. On
Requesty the causes follow the error responses Requesty documents for its inference endpoints:

| Requesty answer | Plain cause printed |
| --- | --- |
| 401, or 403 with a message that does not name the model | The key is invalid, revoked or empty |
| 402 | The organization balance is empty |
| 404, or 400 and 403 with a message naming the model or the access list | The model is not available to this key |
| 429 | The upstream provider rate-limited the request, since Requesty adds no limit of its own |
| 500, 502 or no answer | Requesty or the upstream provider is down |

On OpenAI they follow the error codes OpenAI documents for its API:

| OpenAI answer | Plain cause printed |
| --- | --- |
| 401 (`invalid_api_key`) | The key is invalid, revoked or empty |
| 429 with `insufficient_quota` or a billing message, or with no `retry-after` header | The quota is used up, add credit under Billing |
| 429 with `rate_limit_exceeded` or a `retry-after` header | OpenAI rate-limited the request |
| 404 (`model_not_found`), or 400 and 403 with a message naming the model | The model does not exist or the key's project has no access to it |
| 403 with any other message | The country, region or project is not allowed |
| 500, 503 or no answer | OpenAI is down or overloaded |

| Agent | Provider | Wire format | How the provider is supplied |
| --- | --- | --- | --- |
| Claude Code | Requesty | Anthropic Messages | `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_MODEL`, every model alias variable and `CLAUDE_CODE_SUBAGENT_MODEL` |
| Codex | OpenAI | OpenAI Responses | A throwaway `CODEX_HOME/config.toml` whose `openai-api` provider sets `base_url = "https://api.openai.com/v1"`, `wire_api = "responses"` and names `OPENAI_API_KEY` in `env_key`, plus a trust record, run with `--dangerously-bypass-hook-trust`. Codex reserves the id `openai` for its login-based built-in provider |
| OpenCode | Requesty | OpenAI Chat Completions | `OPENCODE_CONFIG_CONTENT` with an `{env:REQUESTY_API_KEY}` reference |
| Kilo Code | Requesty | OpenAI Chat Completions | `KILO_CONFIG_CONTENT`, one of the trusted sources where Kilo resolves `{env:}` |
| GitHub Copilot | OpenAI | OpenAI Responses | Bring-your-own-key: `COPILOT_PROVIDER_TYPE=openai`, `COPILOT_PROVIDER_WIRE_API=responses`, `COPILOT_PROVIDER_BASE_URL=https://api.openai.com/v1`, `COPILOT_PROVIDER_API_KEY` from `OPENAI_API_KEY` and `COPILOT_MODEL=gpt-6-luna`, with `COPILOT_OFFLINE` so no GitHub token is needed |

No key is ever written into a committed file. The committed [opencode.json](../opencode.json) stays free of
substitution tokens, and every transcript is scanned for the key and dropped if it holds it before the job uploads the
transcripts as an artifact. The scan runs in its own `if: always()` step, `live/<agent>.sh scrub`, so it also runs
after a cancel or a job timeout, which "Causes the step to always execute, and returns `true`, even when canceled"
(`https://docs.github.com/en/actions/reference/workflows-and-actions/expressions`, "always", fetched 2026-10-30). The
upload runs only when that step succeeded, and the step fails when grep could not read every file. The run step sets
`LIVE_AGENT_TIMEOUT` to 300 seconds per prompt, so the seven prompts and two plugin commands of the Claude Code job,
the longest, end within its 45 minute job limit with time left to scrub and upload.

Two providers serve the models. Requesty (REQUESTY LTD, London) is an LLM router at `https://router.requesty.ai/v1`
that speaks Chat Completions, Responses and Anthropic Messages. OpenAI's own API at `https://api.openai.com/v1` serves
Codex and GitHub Copilot, because Requesty serves GPT-6 Luna by translating Codex's Responses request, and that
translation dropped the `multi_agent_v1` namespace of `spawn_agent`, so no Codex subagent ever started. The two
secrets are `REQUESTY_API_KEY`, a Requesty API key, and `OPENAI_API_KEY`, an OpenAI API key, both added under
Settings, Secrets and variables, Actions. Each job receives only the one its agent needs, and the other is empty. Each
agent runs one fixed model, with no fallback to another:

| Agent | Provider | Model id |
| --- | --- | --- |
| Claude Code, OpenCode, Kilo Code | Requesty, `REQUESTY_API_KEY` | `deepinfra/deepseek-v4-flash-0731`, DeepSeek V4 Flash on DeepInfra, with tool calling |
| Codex | OpenAI, `OPENAI_API_KEY` | `gpt-6-luna`, sent in the Responses format |
| GitHub Copilot | OpenAI, `OPENAI_API_KEY` | `gpt-6-luna`, sent in the Responses format |

The Codex and Copilot jobs share one job concurrency group, so they run one after the other rather than side by side.
Both draw on the same OpenAI organisation's per-minute token limit for GPT-6 Luna, and in run 36168529868 Copilot's
first request was refused with a 429 because the Codex job running beside it had already used most of that minute.

The Requesty id is the standard one, not the `:flex` variant, so a flex capacity refusal cannot stall a run. The tests
send nothing but the fixed probe prompts in [live/lib.sh](live/lib.sh).

A run costs what its tokens cost at the prices `https://router.requesty.ai/v1/models` lists for DeepSeek, and at
OpenAI's published API prices for GPT-6 Luna:

```text
cost = uncached input tokens × input price + cached input tokens × cached price + output tokens × output price
```

At the prices listed when this was written, that comes to about 1 cent per DeepSeek agent run and about 1.4 cents
for a Codex or GitHub Copilot run on OpenAI, before tests 7 to 9. Those add one prompt to the Codex run and two to
the Claude Code run, each shaped like test 2, a main turn that starts one subagent. No run has measured them yet.

To start it, open the Actions tab, pick Agent live tests, choose Run workflow, and pick one agent or `all`. The same
from a terminal, Unix shell:

```bash
gh workflow run agent-live-tests.yml -f agent=all
```

PowerShell:

```powershell
gh workflow run agent-live-tests.yml -f agent=all
```

The scripts run locally too, one per agent under [live/](live/), with [live/lib.sh](live/lib.sh) holding the shared
steps and [live/opencode-family.sh](live/opencode-family.sh) what OpenCode and Kilo Code share. The health check needs
only curl and jq. Unix shell:

```bash
OPENAI_API_KEY="<your key>" bash sandbox-agent/live/codex.sh health
```

PowerShell:

```powershell
$env:OPENAI_API_KEY = "<your key>"
```

```powershell
bash sandbox-agent/live/codex.sh health
```

A full local run imports into a throwaway project and keeps its git configuration in a file under the work directory,
never in your own. The agents still start from your home directory, so run it inside the sandbox container rather than
on your machine. Unix shell:

```bash
docker compose run --rm --build -e OPENAI_API_KEY -e SANDBOX_SKIP_UPDATE=1 sandbox bash /repo/sandbox-agent/live/codex.sh run
```

PowerShell:

```powershell
docker compose run --rm --build -e OPENAI_API_KEY -e SANDBOX_SKIP_UPDATE=1 sandbox bash /repo/sandbox-agent/live/codex.sh run
```

The exit code is 0 when nothing failed, 1 when a test failed, 2 on misuse or a missing key, and 4 when the health
check refused.

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

[verify-project.sh](verify-project.sh) and [verify-global.sh](verify-global.sh) therefore capture every agent
command-line tool into a temporary file instead of a pipe, and grep that file. The temporary file is removed by an
exit trap. The assertion still says what it always said, that OpenCode lists every imported subagent, and it is now
measuring that rather than measuring how much of the answer survived the pipe.

---

### Running it

Every command here runs from this directory, which is where Compose finds its `compose.yaml`. The same line
works in a Unix shell and in PowerShell.

```bash
cd sandbox-agent
```

There are two scenarios and one service. The scenario is chosen by the command, because the two differ only in which
script runs: same image, same read-only mount, same security options. A second Compose service would duplicate the
whole service block to express a one-word difference, and would give `docker compose up` two containers when only one
scenario ever runs at a time.

The per-project scenario is the service default, so it needs no command. Unix shell:

```bash
docker compose run --rm --build sandbox
```

PowerShell:

```powershell
docker compose run --rm --build sandbox
```

The global scenario names its script. Unix shell:

```bash
docker compose run --rm --build sandbox /sandbox/verify-global.sh
```

PowerShell:

```powershell
docker compose run --rm --build sandbox /sandbox/verify-global.sh
```

To prove that installing for one agent writes that agent's paths and no other's, Unix shell:

```bash
docker compose run --rm --build sandbox /sandbox/verify-global.sh --scoped codex
```

PowerShell:

```powershell
docker compose run --rm --build sandbox /sandbox/verify-global.sh --scoped codex
```

A cold run takes several minutes. Most of it is the container updating the agent tools.

To reuse the versions already baked into the image and skip the update step, Unix shell:

```bash
docker compose run --rm --build -e SANDBOX_SKIP_UPDATE=1 sandbox
```

PowerShell:

```powershell
docker compose run --rm --build -e SANDBOX_SKIP_UPDATE=1 sandbox
```

To poke around inside a prepared container instead of running the assertions, Unix shell:

```bash
docker compose run --rm --build sandbox /bin/bash
```

PowerShell:

```powershell
docker compose run --rm --build sandbox /bin/bash
```

The image carries ShellCheck, so it can lint its own scripts. Unix shell:

```bash
docker compose run --rm --build --entrypoint shellcheck sandbox /sandbox/entrypoint.sh /sandbox/setup-project.sh /sandbox/setup-global.sh /sandbox/verify-project.sh /sandbox/verify-global.sh /sandbox/e2e-mock/subagent-write.sh
```

PowerShell:

```powershell
docker compose run --rm --build --entrypoint shellcheck sandbox /sandbox/entrypoint.sh /sandbox/setup-project.sh /sandbox/setup-global.sh /sandbox/verify-project.sh /sandbox/verify-global.sh /sandbox/e2e-mock/subagent-write.sh
```

---

### The image goes stale, and the container refuses to run when it has

The scripts are copied into the image when it is built. The repository is mounted at run time, read only, at `/repo`.
Those are two separate copies of the same files, and `docker compose run` on its own does not rebuild, so editing a
script and running again asserts against the copy baked into the image rather than the one you just edited. That has
already produced two false failures against a script that had been fixed hours earlier.

[entrypoint.sh](entrypoint.sh) closes the gap. Before anything else it hashes every `*.sh` and `*.mjs` in `/sandbox`, and every file in `/sandbox/e2e-mock`, against the file of the same path in `/repo/sandbox-agent`, and refuses the run with exit code 3 when any pair differs, or when a script exists on only one side:

```text
==============================================================
 STALE IMAGE, refusing to run
==============================================================
[ERROR] these scripts differ from the ones in /repo/sandbox-agent:
         - verify-global.sh
[ERROR] the image was built before those edits and 'docker compose run' does not rebuild,
[ERROR] so this run would assert against code that no longer exists. Rebuild first:

         docker compose run --rm --build sandbox

[ERROR] to run the baked scripts anyway, set SANDBOX_SKIP_STALE_CHECK=1
==============================================================
```

The file list is derived from the two directories rather than written down, so a script added to the Dockerfile's
`COPY` line is covered without touching the check.

It refuses instead of warning because a warning is exactly what got missed. A cold run prints several minutes of log,
and one more line inside it stops nobody. Refusing costs one flag, and every command in the section above already
carries that flag.

The check only fires on evidence it can trust: both copies readable and their bytes different, or one copy missing
entirely. Anything that makes an honest comparison impossible skips the check and says so in the log: no
`/repo/sandbox-agent` to compare against, no `sha256sum` on `PATH`, or a file that cannot be hashed on both sides. The
guard cannot turn a run that would have worked into a run that fails.

To run the baked scripts anyway, Unix shell:

```bash
docker compose run --rm -e SANDBOX_SKIP_STALE_CHECK=1 sandbox
```

PowerShell:

```powershell
docker compose run --rm -e SANDBOX_SKIP_STALE_CHECK=1 sandbox
```

The pipeline is unaffected. [ci.yml](../.github/workflows/ci.yml) runs `docker compose build` before every scenario, so
the two copies always match there and the check passes without printing a complaint.

One documented command still escapes the guard. `--entrypoint shellcheck` replaces the entrypoint, so nothing gets
compared and the lint runs against whatever the image holds. That is why it carries `--build` as well.

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
MSYS_NO_PATHCONV=1 docker compose run --rm --build sandbox /bin/bash
```

PowerShell and cmd do no such rewriting, so the PowerShell commands above need nothing extra.

---

### What each file does

| File | What it does |
| --- | --- |
| [Dockerfile](Dockerfile) | Debian image with Node, Python, git, jq and ShellCheck, plus a baseline install of the five agent tools under a non-root user. |
| [entrypoint.sh](entrypoint.sh) | Refuses the run when the baked scripts no longer match the mounted ones, marks `/repo` and `/repo/.git` as git safe directories, updates every agent tool to its newest release, prints the resolved versions, then runs the container command. |
| [setup-project.sh](setup-project.sh) | Creates the empty project, marks the same two paths plus the project itself as safe, runs the documented selective checkout against the mounted repository, and repairs and verifies the three symlinks. |
| [setup-global.sh](setup-global.sh) | Follows [docs/GLOBAL_SETUP.md](../docs/GLOBAL_SETUP.md): clones the mounted repository into a temporary directory, fills `~/.config/agents`, wires every agent or only the ones named, and deletes the clone. With `--update` it runs the guide's update instead, refreshing only what is installed. Idempotent, and it never deletes or rewrites a file it did not create. |
| [verify-project.sh](verify-project.sh) | Every per-project assertion, one `PASS` or `FAIL` line each, exit 1 if any failed. Calls `setup-project.sh` first unless `SANDBOX_SKIP_SETUP=1`. |
| [lib-opencode2.sh](lib-opencode2.sh) | The OpenCode 2.x assertions, sourced by both verify scripts, and the OpenCode 1.x and Kilo Code reply style turns the project suite runs. |
| [opencode2.sh](opencode2.sh) | The `opencode2` wrapper, which runs 2.x from its own prefix with its own data directory. |
| [mock-model.mjs](mock-model.mjs) | A scripted OpenAI-compatible model the 2.x, 1.x and Kilo Code turns run against, logging every request body. Its chat completions helpers are exported for [e2e-mock/server.mjs](e2e-mock/server.mjs), and it starts a server only when node runs it directly. |
| [e2e-mock/server.mjs](e2e-mock/server.mjs) | The scripted model of the subagent-write section, speaking Anthropic Messages, OpenAI Responses and OpenAI Chat Completions, placing each request by its marker and its headers, and logging both. A chat request with no marker of its own gets the [mock-model.mjs](mock-model.mjs) answer. |
| [e2e-mock/subagent-write.sh](e2e-mock/subagent-write.sh) | The subagent-write section: one copy of the project per agent, the two scripted cases, and every check, sourced by [verify-project.sh](verify-project.sh) or run on its own. |
| [e2e-mock/records.py](e2e-mock/records.py) | Counts the write calls each agent recorded on disk for one path, split into subagent and main-thread sessions, the second witness beside the request log. |
| [mcp-guard.sh](mcp-guard.sh) | Stands in for `docker`, `npx` and `uvx`, first on `PATH`, recording and refusing every call. |
| [verify-global.sh](verify-global.sh) | Every global assertion, in the same style. Calls `setup-global.sh` twice and then with `--update`, and asserts from `/work/bare`. With `--scoped <agent>` it installs for that agent alone and asserts only its paths were written. |
| [compose.yaml](compose.yaml) | Mounts the repository read-only at `/repo`, drops every Linux capability, and runs `verify-project.sh` unless the run names another script. |
| [live/](live/) | The live tests: [lib.sh](live/lib.sh) with the health check, the other five shared tests and the payload capture and judges of tests 7 to 9, [opencode-family.sh](live/opencode-family.sh) for what OpenCode and Kilo Code share, and one script per agent, where [codex.sh](live/codex.sh) adds test 7 and [claude-code.sh](live/claude-code.sh) tests 8 and 9. |
| [.dockerignore](.dockerignore) | Keeps the README and the Compose file out of the build context, so editing either one does not bust the image cache. |

The [Dockerfile](Dockerfile) pins the five agent tools to exact versions, so the image it builds is reproducible.
[entrypoint.sh](entrypoint.sh) then reaches straight past those pins on every container start: its `update_agents`
function runs `npm install --global` for each package at `@latest`, unless `SANDBOX_SKIP_UPDATE` is set to `1`. The
continuous integration pipeline sets that variable on every sandbox job, so continuous integration genuinely tests
the pinned versions. A plain local run does not set it by default, so it silently re-resolves past the pins to
whatever each registry currently serves, and two runs of the same image tag have already reported different tool
versions minutes apart because of it. Pass `-e SANDBOX_SKIP_UPDATE=1`, as shown in Running it above, to reproduce
the exact versions continuous integration saw. The scripts are the opposite case: they are baked, they do not
re-resolve, and a change to one of them does need a rebuild, which is what the staleness check above enforces. Each
run prints the versions it actually tested against, which is the line to quote when a result needs reproducing.

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
is trusted once, so [verify-project.sh](verify-project.sh) writes a trust record into the container's own
`~/.codex/config.toml` before asking `codex mcp list` anything. Without it Codex reports no MCP servers at all and
the assertion would be measuring the trust prompt rather than the configuration.

GitHub Copilot needs the same kind of step. The CLI skips every workspace MCP source, `.mcp.json` and
`.github/mcp.json` alike, until the project directory is in its own `trustedFolders` list, so
[verify-project.sh](verify-project.sh) writes that list into the container's own `~/.copilot/config.json` before
asking `copilot mcp list` anything, the same shape as the Codex trust record above and scoped to the one throwaway
project rather than a blanket `--allow-all`/`COPILOT_ALLOW_ALL` bypass. Without it `copilot mcp list` reports
`No MCP servers configured.` even though both files are present and valid.

---

### How the global install is exercised

[verify-project.sh](verify-project.sh) covers the per-project import only. The global install writes into a home
directory rather than into a project, so it gets its own pair: [setup-global.sh](setup-global.sh) performs the
install and [verify-global.sh](verify-global.sh) asserts what every agent then discovers, exactly the way
`setup-project.sh` and `verify-project.sh` divide the per-project scenario.

`verify-global.sh` runs the installer twice, because adding a second agent later means running it again, then runs
the update over a home directory it has changed on purpose: a skill deleted, a skill of the user's own added, a hook
script damaged. It asserts the update restores the damage and adds nothing back. Every assertion runs from
`/work/bare`, a directory into which nothing was ever imported. That bareness is what
makes a passing assertion attributable to the home layer rather than to a project layer. Its assertions are those of
suite B in [e2e/testing](../e2e/testing), specs 6 to 9, so the script and the specs say the same thing.

Everything the installer copies comes from the temporary clone it makes of `/repo` and deletes afterwards, so that
part is committed state, the same rule the per-project suite follows. The scripts themselves are baked into the image,
so a change to one of them needs a rebuild before a run sees it.

---

### Isolation from your machine

- The repository is bind-mounted read-only at `/repo`. A run cannot write to your working tree even by accident.
- The throwaway project lives at `/work/project` inside the container and is deleted and rebuilt on every run.
- Nothing from your home directory is mounted. Every agent tool installs into `/home/sandbox/.npm-global` and writes
  its state under `/home/sandbox`, which dies with the container.
- The container runs as the unprivileged `sandbox` user.
- No MCP server can start. `docker`, `npx` and `uvx`, the only launchers the shipped MCP blocks use, resolve to [mcp-guard.sh](mcp-guard.sh), which records the call in `/tmp/sandbox-mcp-guard.log` and exits 127. Every `mcp list` assertion still passes, because each CLI names its configured servers whether or not they connect, and each suite notes how many launches the guard refused. A run before the guard existed started the `npx` servers inside the container, and a run on a host with Docker pulled `mcp/sonarqube`.
- Credentials are never supplied, so no agent can reach a provider, unless you pass `REQUESTY_API_KEY` or
  `OPENAI_API_KEY` for a live test.

---

### Defects this sandbox has already caught

Every failure the sandbox has reported so far was a real defect in the repository rather than a sandbox bug. They are
recorded here because they show the class of problem only a live run finds. All three are fixed as this is written.

1. Kilo Code rejected the shared `opencode.json` outright. An `{env:VAR}` reference is banned in project-scope
   configuration, and Kilo discards the whole file rather than leaving the token literal, which took the `plugin`
   declaration carrying the preflight gate with it. Kilo Code had no gate at all. There is now a single project-level
   OpenCode configuration, [opencode.json](../opencode.json) at the repository root, and it carries no environment
   reference of any kind. Local servers need none, because both tools start them with the environment of the process
   that started the agent. The one value that cannot arrive that way is the Context7 API key, which travels as an HTTP
   header, so `context7` is declared unauthenticated and both tools use the free tier. A paid key goes in the reader's
   own global configuration. It cannot go in a project file, because Kilo would reject that file whole and take the
   gate declaration with it again.
2. One skill had invalid YAML front matter. An unquoted colon in the `description` of a skill manifest made
   GitHub Copilot skip that skill entirely. The value is quoted now.
3. The same defect came back in two more manifests. `copilot skill list` refused
   [.agents/skills/ai-regression-testing/SKILL.md](../.agents/skills/ai-regression-testing/SKILL.md) and
   [.agents/skills/design-system/SKILL.md](../.agents/skills/design-system/SKILL.md) with
   `mapping values are not allowed in this context`, because each `description` carried an unquoted colon, which left
   both skills invisible to Copilot. Both values are quoted now. Item 2 was closed with a one-off scan, which is why
   this one got in, so the check is mechanical this time: `check_front_matter` in
   [.agents/hooks/_check_markdown.py](../.agents/hooks/_check_markdown.py), which CI runs through [tools/check-markdown.py](../tools/check-markdown.py), parses the front matter of every skill manifest and every
   canonical subagent source with a strict YAML parser, and reports an unquoted colon or a leading YAML indicator in a
   description, a name that does not match the folder name or the file stem, a missing, empty, non-string or
   over-length description, and any skill key outside the Agent Skills specification. CI runs it on every pull request.

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
