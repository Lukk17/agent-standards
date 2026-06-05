// Preflight enforcement adapter for OpenCode.
//
// Re-injects the skill/subagent preflight gate into the system prompt on every
// request, so it stays salient in long sessions instead of decaying out of the
// model's attention. Mirrors the Claude Code UserPromptSubmit hook
// (.claude/settings.json) and the Kilo Code rule (.kilocode/rules/00-preflight.md).
// Canonical wording lives at the top of AGENTS.md.
//
// Uses the experimental `chat.system.transform` hook. If a future OpenCode
// release renames or stabilises it, update the hook key below.

const GATE =
  "PREFLIGHT: before code work, name the skills and subagents that own this task " +
  "and invoke them, or say none apply and why. Delegate investigation, review and " +
  "bounded implementation by default."

export const Preflight = async () => {
  return {
    "experimental.chat.system.transform": async (_input, output) => {
      output.system.push(GATE)
    },
  }
}
