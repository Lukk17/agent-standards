// Generic hook runner for OpenCode and Kilo Code.
//
// Neither runtime can block a reply from completing, so every check rides the
// only blocking channel they have: throwing from tool.execute.before aborts the
// tool call and surfaces the message to the model.
//
// This file holds no rules. It discovers every hook in the project's own
// .agents/hooks/, or in the user's ~/.agents/hooks/ when the project has none,
// runs them in declared order against one envelope, and turns the first exit
// code 2 into a thrown Error. Adding a hook needs no edit here. The contract a
// hook must follow is documented at
// https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md.
//
// It also adds the preflight reminder to every user message of a root session
// through chat.message, and the subagent reminder to every user message of a
// child session, the same two wordings the other agents inject from their own
// wiring. It hands every
// finished text part through experimental.text.complete to the hooks that declare
// HOOK_TEXT_EVENT, so a hook can store a fixed version of it. That is the one
// event whose stdout counts.
//
// Imports nothing from @opencode-ai/plugin or @kilocode/plugin so one file
// serves both runtimes.

import { spawn } from "node:child_process"
import { randomBytes } from "node:crypto"
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

// Tried in this order, the way every other wiring resolves its interpreter:
// Debian and Ubuntu ship no `python`, the python.org Windows installer ships no
// `python3`, and a Windows Store alias of either name can exist and run nothing.
const PYTHON_CANDIDATES = ["python3", "python"]
const PROBE = ["-c", "import sys; sys.stdout.write('ok')"]
// -S skips site initialisation and -E ignores the PYTHON* environment, which
// takes a measurable slice off the interpreter start the runner pays on every
// tool call. Every hook here is stdlib only, so neither flag costs it anything.
const PYTHON_FLAGS = ["-S", "-E"]
const HOOKS_DIR = join(".agents", "hooks")
// A project that deliberately runs without the user's global hooks holds this
// file. Only its presence counts, and it never switches off hooks the project
// ships in its own .agents/hooks/.
const OPT_OUT = join(".agents", "no-global-hooks")

const CONTRACT = 3
const EVENT = "tool.execute.before"
const TEXT_EVENT = "experimental.text.complete"

const DEFAULT_ORDER = 100
const ORDER_RE = /^HOOK_ORDER\s*=\s*(\d+)\s*$/m
const TEXT_RE = /^HOOK_TEXT_EVENT\s*=\s*True\s*$/m
const HEAD_CHARS = 16384

const TIMEOUT_MS = 10000
const SESSION_CAP = 64
const MESSAGE_WINDOW = 8

const REMINDER = [
  "PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, " +
    "or say none apply and why. Delegate investigation, review and bounded implementation by default. " +
    "Follow the user-communication skill when writing to the user. " +
    "If the prompt asks anything, answer every question first, then start the work. " +
    "End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, " +
    "plain lines only, keeping every blank line:",
  "",
  "Running: `running task name` (or: nothing)",
  "",
  "~~DONE: older finished task~~",
  "~~DONE: most recent finished task~~",
  "",
  "**NOW: what is being done right now**",
  "",
  "Next: the next task",
  "Then: the task after that",
  "",
  "Waiting on: what you wait for (or: nothing)",
  "",
  "When several tasks run, list each name in backticks on the Running line, separated by commas.",
].join("\n")

const SUBAGENT_REMINDER =
  "PREFLIGHT for a subagent: you are a subagent, and the main thread delegated this task to you. " +
  "Do the work yourself with your own tools and load the skills your definition names. " +
  "The rules that the main thread must delegate and may not write files apply to the main thread only, " +
  "so do not hand this task on and do not refuse it for that reason. " +
  "The preflight gate still checks every tool call you make. " +
  "Report back what you changed and how you verified it."

const PART_PREFIX = "prt_"
const PART_RANDOM_CHARS = 14
const BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

// Reading the file is load bearing twice over. It yields the declared order and
// whether the hook takes the text event, and it proves the file can be opened
// at all: Python exits 2 when it cannot open the script it was handed, which
// would otherwise read as a denial. A hook that cannot be read here is dropped
// rather than run.
const inspect = (name, path) => {
  let head = ""

  try {
    head = readFileSync(path, "utf8").slice(0, HEAD_CHARS)
  } catch {
    return null
  }

  const match = ORDER_RE.exec(head)

  return { name, path, order: match ? Number(match[1]) : DEFAULT_ORDER, text: TEXT_RE.test(head) }
}

const isDirectory = (path) => {
  try {
    return statSync(path).isDirectory()
  } catch {
    return false
  }
}

// The directory whose hooks serve this project. The project's own
// .agents/hooks/ wins whenever it exists, even empty. Without one, the hooks the
// global install in docs/GLOBAL_SETUP.md puts under ~/.agents/hooks/ serve it,
// unless the project opted out, which leaves it with none. Resolved on every call,
// like the directory listing, so either change takes effect without a restart.
const hooksDirectory = (root) => {
  const own = join(root, HOOKS_DIR)

  if (isDirectory(own)) return own
  if (existsSync(join(root, OPT_OUT))) return null

  try {
    const home = homedir()

    return home ? join(home, HOOKS_DIR) : null
  } catch {
    return null
  }
}

// Re-read on every call so a hook dropped into the directory mid-session is
// picked up without a restart. A missing or unreadable directory yields no
// hooks, which allows the call.
//
// Order is declared by the hook, never taken from the filesystem. A hook that
// declares nothing sorts at DEFAULT_ORDER, and equal orders fall back to the
// file name so the sequence stays stable.
const discover = (root) => {
  const dir = hooksDirectory(root)
  let entries = []

  if (!dir) return []

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
// nor the shebang matters. Any failure to spawn is an allow, and so is a hook
// still running at TIMEOUT_MS, which is killed.
//
// The spawn is asynchronous with its own timer on purpose. spawnSync under the
// Bun runtime both tools ship on Windows returned ETIMEDOUT within 100 ms on
// most calls after the first, which skipped the gate without a trace.
const run = (python, root, hook, input) => execute(python, [...PYTHON_FLAGS, hook.path, "--format", "plain"], root, input)

const execute = (command, args, root, input) =>
  new Promise((resolve) => {
    let child = null
    let stdout = ""
    let stderr = ""
    let settled = false
    let timer = null

    const finish = (result) => {
      if (settled) return

      settled = true
      clearTimeout(timer)
      resolve(result)
    }

    try {
      child = spawn(command, args, {
        cwd: root,
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      })
    } catch {
      finish(null)
      return
    }

    timer = setTimeout(() => {
      try {
        child.kill()
      } catch {
        // The timeout allows whether or not the kill lands.
      }

      finish(null)
    }, TIMEOUT_MS)

    child.on("error", () => finish(null))
    child.on("close", (status) => finish({ status, stdout, stderr }))
    child.stdout?.setEncoding("utf8")
    child.stdout?.on("data", (chunk) => {
      stdout += chunk
    })
    child.stderr?.setEncoding("utf8")
    child.stderr?.on("data", (chunk) => {
      stderr += chunk
    })
    child.stdin?.on("error", () => {})
    child.stdin?.end(input, "utf8")
  })

// The first candidate that runs the probe and prints its answer, or null when
// none does, which runs no hook and so allows. Only an interpreter that answered
// is kept for the life of the plugin, so a probe that failed under load is
// tried again on the next call.
let interpreter = null

const resolvePython = async (root) => {
  if (interpreter) return interpreter

  for (const candidate of PYTHON_CANDIDATES) {
    const result = await execute(candidate, [...PYTHON_FLAGS, ...PROBE], root, "")

    if (result?.status === 0 && result.stdout === "ok") {
      interpreter = candidate

      return interpreter
    }
  }

  return null
}

// Exit code 2 is the only denial. Everything else, including a crash, a signal
// or a timeout, allows.
const denial = (result, name) => {
  if (result?.status !== 2) return ""

  return result.stderr?.trim() || "Blocked by " + name + "."
}

// A text event cannot be denied, so only a clean exit counts, and only when it
// printed one JSON object whose `text` is a string. Anything else keeps the text.
const rewrite = (result) => {
  if (result?.status !== 0 || !result.stdout?.trim()) return null

  try {
    const answer = JSON.parse(result.stdout)

    return typeof answer?.text === "string" ? answer.text : null
  } catch {
    return null
  }
}

// Only a hook that declares HOOK_TEXT_EVENT sees the text, so a finished part
// costs no interpreter start for a hook that would ignore it. Each sees the text
// the previous one left, in the same declared order as a tool call. No session
// lookup is made, so the envelope names no agent and no caller, which every hook
// already reads as unknown.
const completeText = async (root, text) => {
  const hooks = discover(root).filter((hook) => hook.text)

  if (hooks.length === 0) return text

  const python = await resolvePython(root)

  if (!python) return text

  let current = text

  for (const hook of hooks) {
    const envelope = JSON.stringify({
      contract: CONTRACT,
      event: TEXT_EVENT,
      tool_name: "",
      tool_input: {},
      agent_type: "",
      assistant_text: "",
      text: current,
      cwd: root,
    })
    const rewritten = rewrite(await run(python, root, hook, envelope))

    if (rewritten !== null) current = rewritten
  }

  return current
}

// The newest `limit` messages of the session, oldest first, or every message
// when no limit is given, or null when the lookup failed.
// client.session.messages({ path: { id }, query: { limit } }) resolves to
// { info, parts }[], bare or wrapped in { data } depending on the client's
// responseStyle.
const fetchMessages = async (client, sessionID, limit) => {
  try {
    const request = { path: { id: sessionID }, ...(limit ? { query: { limit } } : {}) }
    const reply = await client?.session?.messages?.(request)
    const messages = Array.isArray(reply) ? reply : reply?.data

    return Array.isArray(messages) ? messages : null
  } catch {
    return null
  }
}

// Enough of the session to name the agent and read the newest assistant prose.
// The newest MESSAGE_WINDOW messages answer both on almost every call, so the
// whole history is fetched only when that window is full and still misses one
// of them, which keeps both answers exactly what the full history gives.
const sessionMessages = async (client, sessionID) => {
  if (!sessionID) return null

  const recent = await fetchMessages(client, sessionID, MESSAGE_WINDOW)

  if (recent === null || recent.length < MESSAGE_WINDOW) return recent
  if (agentName(recent) && lastAssistantText(recent)) return recent

  return fetchMessages(client, sessionID)
}

// true for a child session, false for a root session, null when the session
// could not be read. Only a session object naming this very id counts, so an
// error body or an empty reply is never mistaken for a root session.
const lookupSubagent = async (client, sessionID) => {
  if (!sessionID) return null

  try {
    const reply = await client?.session?.get?.({ path: { id: sessionID } })
    const session = reply?.id === undefined ? reply?.data : reply

    if (session?.id !== sessionID) return null

    return typeof session.parentID === "string" && session.parentID !== ""
  } catch {
    return null
  }
}

// A session's parent never changes, so a definite answer is kept for the life
// of the plugin and a failed lookup is retried on the next call.
const placeSession = async (client, placed, sessionID) => {
  if (placed.has(sessionID)) return placed.get(sessionID)

  const subagent = await lookupSubagent(client, sessionID)

  if (subagent !== null) {
    if (placed.size >= SESSION_CAP) placed.clear()
    placed.set(sessionID, subagent)
  }

  return subagent
}

// The agent acting in the session: the newest message that names one. A user
// message carries it as `agent`, an assistant message as `agent` or `mode`.
const agentName = (messages) => {
  for (let i = (messages?.length ?? 0) - 1; i >= 0; i--) {
    const info = messages[i]?.info
    const name = [info?.agent, info?.mode].find((value) => typeof value === "string" && value.trim())

    if (name) return name.trim()
  }

  return ""
}

// Newest assistant prose in the session, or "" when there is none yet.
const lastAssistantText = (messages) => {
  for (let i = (messages?.length ?? 0) - 1; i >= 0; i--) {
    const entry = messages[i]

    if (entry?.info?.role !== "assistant") continue

    const text = (entry.parts ?? [])
      .filter((part) => part?.type === "text" && typeof part.text === "string")
      .map((part) => part.text)
      .join("\n")

    if (text.trim()) return text
  }

  return ""
}

// Each distinct text is delivered to the hooks once per session, so a run of
// tool calls after one message does not block twice on prose the model cannot
// change mid-turn.
const freshAssistantText = (messages, seen, sessionID) => {
  if (!sessionID) return ""

  const text = lastAssistantText(messages)

  if (!text || seen.get(sessionID) === text) return ""

  if (seen.size >= SESSION_CAP) seen.clear()
  seen.set(sessionID, text)

  return text
}

// A part id in the runtime's own ascending shape: prefix, 12 hex digits of
// millisecond time and a per-millisecond counter, then random base62.
let lastStamp = 0
let stampCounter = 0

const partID = () => {
  const now = Date.now()

  if (now !== lastStamp) {
    lastStamp = now
    stampCounter = 0
  }

  stampCounter++

  const time = (BigInt(now) * 0x1000n + BigInt(stampCounter)).toString(16).padStart(12, "0").slice(-12)
  const random = Array.from(randomBytes(PART_RANDOM_CHARS), (byte) => BASE62[byte % 62]).join("")

  return PART_PREFIX + time + random
}

// A synthetic text part on the user message reaches the model with the prompt
// and stays out of the visible transcript.
const remind = (input, output, text) => {
  const parts = output?.parts
  const sessionID = output?.message?.sessionID || input?.sessionID
  const messageID = output?.message?.id || input?.messageID

  if (!Array.isArray(parts) || !sessionID || !messageID) return

  parts.push({ id: partID(), sessionID, messageID, type: "text", text, synthetic: true })
}

// `worktree` is the project root; `directory` is only the session's working
// directory, which is a subdirectory whenever the runtime was started deeper in
// the tree. Anchoring on the root is what keeps .agents/hooks/ findable. A hook
// taken from the global directory still runs with the project root as its
// working directory and its envelope cwd, so it protects the project, not home.
export const Preflight = async ({ directory, worktree, client } = {}) => {
  const root = worktree || directory || process.cwd()
  const seen = new Map()
  const placed = new Map()

  return {
    // The reminder tells the reader to delegate, so only a session placed as a
    // root session gets it. A subagent's task prompt arrives through this same
    // event in its child session and gets the subagent text instead, and a
    // session that cannot be placed gets nothing.
    "chat.message": async (input, output) => {
      try {
        const sessionID = output?.message?.sessionID || input?.sessionID
        const subagent = await placeSession(client, placed, sessionID)

        if (subagent === null) return

        remind(input, output, subagent ? SUBAGENT_REMINDER : REMINDER)
      } catch {
        return
      }
    },

    [TEXT_EVENT]: async (_input, output) => {
      try {
        if (typeof output?.text !== "string" || !output.text) return

        output.text = await completeText(root, output.text)
      } catch {
        return
      }
    },

    [EVENT]: async (input, output) => {
      const hooks = discover(root)

      // Nothing to ask, so nothing to build. This also keeps the session round
      // trips out of a project that checked out no hooks.
      if (hooks.length === 0) return

      const python = await resolvePython(root)

      if (!python) return

      const sessionID = typeof input?.sessionID === "string" ? input.sessionID : ""
      const [subagent, messages] = await Promise.all([
        placeSession(client, placed, sessionID),
        sessionMessages(client, sessionID),
      ])

      // is_subagent is left out when the session could not be placed, which the
      // gate reads as an unknown caller and allows.
      const envelope = JSON.stringify({
        contract: CONTRACT,
        event: EVENT,
        tool_name: input?.tool ?? "",
        tool_input: output?.args ?? {},
        agent_type: agentName(messages),
        ...(subagent === null ? {} : { is_subagent: subagent }),
        assistant_text: freshAssistantText(messages, seen, sessionID),
        cwd: root,
      })

      for (const hook of hooks) {
        const message = denial(await run(python, root, hook, envelope), hook.name)

        if (message) throw new Error(message)
      }
    },
  }
}

export default Preflight
