# Subagent Mode

How the review changes when a subagent with a read-only shell runs it. Open this before Step 1 whenever you are such a subagent.

---

### When run as a subagent

A read-only subagent, such as the `code-reviewer` or the `security-auditor` agent, each held to the few git and gh
commands its "Read-only shell" section lists, cannot run the steps in SKILL.md that check code out, execute code, or ask the
user. It changes them so:

- Review the diff the caller supplies. With no diff in the prompt and a shell that allows it, read
  `git --no-pager diff`, `git --no-pager diff --staged`, `git --no-pager show`, or `gh pr diff` and `gh pr view`, in
  exactly the form the agent's "Read-only shell" section lists. With neither, return the question to the caller.
- Skip the worktree and every command that builds, tests or runs the change, and report the verification as
  `not run`, naming the command the project's AGENTS.md documents so the caller can run it. Where the list holds
  `gh pr checks`, report a pull request's CI result from it once, never with `--watch`.
- Return every question to the caller instead of asking the user, including whether to run anything from a fork.
- Hand the security escalation of Step 4 to the caller as a named next step, since neither agent has a tool to spawn another.
