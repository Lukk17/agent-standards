### AI Bash Development Standards

---

### Core Execution Directives

- Treat all LLM generated scripts, variable expansions, and command pipelines as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every script generation task.
- Append a Zero-Trust directive demanding mandatory web searches for current Bash built-ins.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every command flag and syntax structure provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Strict Mode and Error Handling

- Enforce the Unofficial Bash Strict Mode at the top of every script to prevent silent failures and unbound variable errors. [Confidence: 100%]
  - Link: http://redsymbol.net/articles/unofficial-bash-strict-mode/
  - Quote: "punchline."
- Require the agent to prepend the following line immediately after the shebang:

```bash
set -euo pipefail
IFS=$'\n\t'
```

- Disable the nounset option temporarily using set +u only when checking for optional positional parameters, then immediately re-enable it using set -u. [Confidence: 100%]
- Use the trap built-in to catch ERR signals and execute cleanup functions, ensuring temporary files or locks are removed even if the script crashes unexpectedly. [Confidence: 100%]

---

### Defensive Scripting Practices

- Quote all variable expansions to prevent word splitting and globbing issues. The agent must use "$VARIABLE" instead of $VARIABLE. [Confidence: 100%]
- Validate the presence of required external commands using command -v at the start of the script before executing any logic. [Confidence: 100%]