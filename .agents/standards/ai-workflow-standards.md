# AI Workflow Standards

Rules governing how an AI agent must behave during every interaction in this project.

---

## Docker Rule

NEVER run any `docker` command. If a Docker command is required, present it to the user and ask them to run it.

---

## Anti-Hallucination Protocol

1. **Zero-Guessing**: Never guess ports, connection strings, package names, or API patterns. If uncertain, use web search to read the official documentation for the exact library version before proposing anything.
2. **Quote the Docs**: When an integration or configuration is non-trivial, quote the relevant official documentation section before implementing.
3. **Admit Ignorance**: If you do not know the exact, documented integration pattern between two tools, state: "I do not know the verified pattern for this." Do not hallucinate a configuration to see if it works.

---

## Answering Questions First

If the user's prompt contains any questions, number and answer every question in the chat before starting any implementation plan or writing any code. Wait for explicit user approval before proceeding.

---

## Approval Protocol

1. Never start any code implementation or modification until the user has explicitly approved the plan.
2. If the user asks questions after a plan is presented, answer them and wait for a new explicit approval before proceeding.
3. "Assuming approval" is a critical failure.

---

## Side-Effect Disclosure

Before proposing any configuration change, explicitly list the worst-case scenario and any irreversible consequences.

---

## Production Standards

- Treat every response as a final, production-ready delivery. Prototype or "happy path" quality is forbidden.
- If a requirement implies associated administrative or maintenance features (e.g., CRUD implies list, create, update, delete), implement all of them unless explicitly told otherwise.
- Never deviate from architectural patterns, naming conventions, or rule files for the sake of speed.
- Do not add comments, logs, or unrequested changes. Stick exactly to the approved plan.

---

## File Creation Constraints

- Do not create `Task.md`, `Walkthrough.md`, or any validation-only scripts or helper files.
- Summarize all changes in the chat; do not create summary files.
- Do not create files unless they are absolutely necessary for the implementation.

---

## Execution Process

1. Analyze the prompt for clarity; identify ambiguities before starting.
2. Plan step-by-step: (a) requirements, (b) structure/symbols, (c) full execution flow, (d) standards applied.
3. Do not start implementation before the plan is approved.
4. If any instruction is unclear, ask before starting.
5. After generating code, perform a mental compiler-check: trace through the logic to catch errors before presenting.
6. Apply OWASP security practices, input validation, and use only trusted dependencies.

---

## Tool Use Policy

- Always prefer dedicated tools (Read, Edit, Grep, Glob) over shell commands when an equivalent tool exists.
- Use shell execution only for operations that have no dedicated tool equivalent.
- Never run destructive commands (rm -rf, drop table, force-push) without explicit user confirmation.
- If a tool call fails, diagnose the root cause before retrying. Do not retry the identical call more than once.

---

## Context Window Management

- When a task requires reading many files, read the most relevant ones first and defer others until needed.
- If accumulated context exceeds ~70% of the window, summarize completed sub-tasks internally and release intermediate detail.
- Split large implementation tasks into sequential sub-tasks rather than attempting them in one pass.
- Never truncate file writes due to context pressure; if a file is too large to write completely, pause and inform the user.

---

## Multi-Agent Coordination

- A parent agent must provide each sub-agent with a fully self-contained prompt: relevant file paths, applicable standards, and a precise success criterion.
- Sub-agents must not make assumptions about context that was not explicitly passed to them.
- A parent agent must validate sub-agent output before accepting it; never blindly merge sub-agent results.
- Sub-agents must not push to remote repositories, send external messages, or take irreversible actions without explicit authorization in their prompt.

---

## Escalation Policy

- If a requirement is ambiguous, stop and ask before writing any code. Do not interpret ambiguity silently.
- If an implementation would require deviating from architectural standards, surface the conflict to the user and propose options. Do not silently deviate.
- If a required tool, credential, or environment is unavailable, report it immediately rather than working around it with an inferior substitute.
- "I assumed it was fine" is a critical failure.

---

## Output Formatting

- Use fenced code blocks with the correct language tag for all code snippets.
- Use numbered lists for sequential steps; use bullet lists for unordered items.
- Keep prose responses concise; prefer structured output (tables, lists) over paragraphs for technical content.
- Never pad responses with filler phrases ("Great question!", "Certainly!").
- When reporting verification results, always use the structured format defined in `implementation-plan-standards.md`.
