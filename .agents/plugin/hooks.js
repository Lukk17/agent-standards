// Generic hook runner for OpenCode and Kilo Code.
//
// Neither runtime can block a reply from completing, so every check rides the
// only blocking channel they have: throwing from tool.execute.before aborts the
// tool call and surfaces the message to the model.
//
// This file holds no rules. It discovers every hook in .agents/hooks/, runs them
// in declared order against one envelope, and turns the first exit code 2 into a
// thrown Error. Adding a hook needs no edit here. The contract a hook must
// follow is documented at
// https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md.
//
// Imports nothing from @opencode-ai/plugin or @kilocode/plugin so one file
// serves both runtimes.

import { spawnSync } from "node:child_process"
import { readdirSync, readFileSync } from "node:fs"
import { join } from "node:path"

const PYTHON = process.platform === "win32" ? "python" : "python3"
const HOOKS_DIR = join(".agents", "hooks")

const CONTRACT = 1
const EVENT = "tool.execute.before"

const DEFAULT_ORDER = 100
const ORDER_RE = /^HOOK_ORDER\s*=\s*(\d+)\s*$/m
const HEAD_CHARS = 4096

const TIMEOUT_MS = 10000
const SESSION_CAP = 64

// Reading the file is load bearing twice over. It yields the declared order,
// and it proves the file can be opened at all: Python exits 2 when it cannot
// open the script it was handed, which would otherwise read as a denial. A hook
// that cannot be read here is dropped rather than run.
const inspect = (name, path) => {
  let head = ""

  try {
    head = readFileSync(path, "utf8").slice(0, HEAD_CHARS)
  } catch {
    return null
  }

  const match = ORDER_RE.exec(head)

  return { name, path, order: match ? Number(match[1]) : DEFAULT_ORDER }
}

// Re-read on every call so a hook dropped into the directory mid-session is
// picked up without a restart. An unreadable directory yields no hooks, which
// allows the call.
//
// Order is declared by the hook, never taken from the filesystem. A hook that
// declares nothing sorts at DEFAULT_ORDER, and equal orders fall back to the
// file name so the sequence stays stable.
const discover = (root) => {
  const dir = join(root, HOOKS_DIR)
  let entries = []

  try {
    entries = readdirSync(dir, { withFileTypes: true })
  } catch {
    return []
  }

  const hooks = entries
    .filter((entry) => !entry.isDirectory())
    .map((entry) => entry.name)
    .filter((name) => name.endsWith(".py") && !name.startsWith("_") && !name.startsWith("."))
    .map((name) => inspect(name, join(dir, name)))
    .filter(Boolean)

  hooks.sort((a, b) => a.order - b.order || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))

  return hooks
}

// Hooks are always run through the interpreter, so neither the executable bit
// nor the shebang matters. Any failure to spawn is an allow.
const run = (root, hook, input) => {
  try {
    return spawnSync(PYTHON, [hook.path, "--format", "plain"], {
      cwd: root,
      input,
      encoding: "utf8",
      timeout: TIMEOUT_MS,
    })
  } catch {
    return null
  }
}

// Exit code 2 is the only denial. Everything else, including a crash, a signal
// or a timeout, allows.
const denial = (result, name) => {
  if (result?.status !== 2) return ""

  return result.stderr?.trim() || "Blocked by " + name + "."
}

// Newest assistant prose in the session, or "" when there is none yet.
// client.session.messages({ path: { id } }) resolves to { info, parts }[], bare
// or wrapped in { data } depending on the client's responseStyle.
const lastAssistantText = async (client, sessionID) => {
  try {
    const reply = await client?.session?.messages?.({ path: { id: sessionID } })
    const messages = Array.isArray(reply) ? reply : reply?.data

    if (!Array.isArray(messages)) return ""

    for (let i = messages.length - 1; i >= 0; i--) {
      const entry = messages[i]

      if (entry?.info?.role !== "assistant") continue

      const text = (entry.parts ?? [])
        .filter((part) => part?.type === "text" && typeof part.text === "string")
        .map((part) => part.text)
        .join("\n")

      if (text.trim()) return text
    }
  } catch {
    return ""
  }

  return ""
}

// Each distinct text is delivered to the hooks once per session, so a run of
// tool calls after one message does not block twice on prose the model cannot
// change mid-turn.
const freshAssistantText = async (client, seen, sessionID) => {
  if (!sessionID) return ""

  const text = await lastAssistantText(client, sessionID)

  if (!text || seen.get(sessionID) === text) return ""

  if (seen.size >= SESSION_CAP) seen.clear()
  seen.set(sessionID, text)

  return text
}

// `worktree` is the project root; `directory` is only the session's working
// directory, which is a subdirectory whenever the runtime was started deeper in
// the tree. Anchoring on the root is what keeps .agents/hooks/ findable.
export const Preflight = async ({ directory, worktree, client } = {}) => {
  const root = worktree || directory || process.cwd()
  const seen = new Map()

  return {
    [EVENT]: async (input, output) => {
      const hooks = discover(root)

      // Nothing to ask, so nothing to build. This also keeps the session round
      // trip for the assistant text out of a project that checked out no hooks.
      if (hooks.length === 0) return

      const agent = typeof input?.agent === "string" ? input.agent : ""

      const envelope = JSON.stringify({
        contract: CONTRACT,
        event: EVENT,
        tool_name: input?.tool ?? "",
        tool_input: output?.args ?? {},
        agent_type: agent,
        is_subagent: Boolean(agent),
        assistant_text: await freshAssistantText(client, seen, input?.sessionID),
        cwd: root,
      })

      for (const hook of hooks) {
        const message = denial(run(root, hook, envelope), hook.name)

        if (message) throw new Error(message)
      }
    },
  }
}

export default Preflight
