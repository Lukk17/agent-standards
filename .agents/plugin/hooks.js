// Preflight and response-formatting adapter for OpenCode and Kilo Code.
//
// Neither runtime can block a reply from completing, so both checks ride the
// only blocking channel they have: throwing from tool.execute.before aborts the
// tool call and surfaces the message to the model. Every tool call runs the
// preflight gate first, then the formatting check against the newest assistant
// text in the session. Exit code 2 from either Python script becomes a thrown
// Error. Everything else allows the call.
//
// Thin shim with no rules of its own. Imports nothing from @opencode-ai/plugin
// or @kilocode/plugin so one file serves both runtimes.

import { spawnSync } from "node:child_process"
import { existsSync } from "node:fs"
import { join } from "node:path"

const PYTHON = process.platform === "win32" ? "python" : "python3"
const GATE = join(".agents", "hooks", "preflight_gate.py")
const MARKERS = join(".agents", "hooks", "no_ai_markers_check.py")

const SESSION_CAP = 64

// The existence check is load bearing: Python itself exits 2 when it cannot
// open the script, which would otherwise read as a denial.
const run = (root, script, args, input) => {
  try {
    const path = join(root, script)

    if (!existsSync(path)) return null

    return spawnSync(PYTHON, [path, ...args], { cwd: root, input, encoding: "utf8" })
  } catch {
    return null
  }
}

const denial = (result, fallback) => {
  if (result?.status !== 2) return ""

  return result.stderr?.trim() || fallback
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

export const Preflight = async ({ directory, client } = {}) => {
  const root = directory || process.cwd()
  const seen = new Map()

  const gate = (input, output) => {
    const agent = typeof input?.agent === "string" ? input.agent : ""

    const payload = JSON.stringify({
      tool_name: input?.tool ?? "",
      tool_input: output?.args ?? {},
      agent_type: agent,
    })

    const args = ["--format", "plain"]
    if (agent) args.push("--subagent")

    const message = denial(
      run(root, GATE, args, payload),
      "Preflight gate denied this call.",
    )

    if (message) throw new Error(message)
  }

  // Checked once per distinct text, so a run of tool calls after one message
  // does not throw again on prose the model cannot change mid-turn.
  const formatting = async (sessionID) => {
    if (!sessionID) return

    const text = await lastAssistantText(client, sessionID)

    if (!text || seen.get(sessionID) === text) return

    if (seen.size >= SESSION_CAP) seen.clear()
    seen.set(sessionID, text)

    const message = denial(
      run(root, MARKERS, ["--text"], text),
      "Rewrite your last reply without banned formatting.",
    )

    if (message) throw new Error(message)
  }

  return {
    "tool.execute.before": async (input, output) => {
      gate(input, output)
      await formatting(input?.sessionID)
    },
  }
}

export default Preflight
