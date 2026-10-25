// Generic hook runner for OpenCode 1.x, OpenCode 2.x and Kilo Code. A global
// copy stands down when the project ships its own plugin: it registers no hooks
// so the project copy runs the gate exactly once.
//
// One default export serves all three loaders: { id, server, setup }. OpenCode
// 1.x and Kilo Code call `server` and read the hooks object it returns. OpenCode
// 2.x calls `setup` with its own context and registers through
// ctx.tool.hook("execute.before"). Declare the plugin by its directory, so
// index.js beside this file is what a loader resolves.
//
// No runtime can block a reply from completing, so every check rides the only
// blocking channel they have: throwing from the tool hook aborts the tool call
// and surfaces the message to the model. OpenCode 2.x has no hook on a
// finished reply at all, so there the formatting check sees the reply only
// when the next tool call starts, and a reply with no tool call after it is
// never checked.
//
// This file holds no rules. It discovers every hook in the project's own
// .agents/hooks/, or in the user's ~/.config/agents/hooks/ when the project has none,
// runs them in declared order against one envelope, and turns the first exit
// code 2 into a thrown Error. Adding a hook needs no edit here. The contract a
// hook must follow is documented at
// https://github.com/Lukk17/agent-standards/blob/master/docs/hooks-contract.md.
//
// On OpenCode 1.x and Kilo Code it hands every finished text part through
// experimental.text.complete to the hooks that declare HOOK_TEXT_EVENT, so a
// hook can store a fixed version of it. That is the one event whose stdout
// counts.
//
// Reply style is for the main thread only, on every runtime. A session placed
// as a subagent, a child whose parentID is set, gets no text rewrite and hands
// the hooks no assistant text, so no reply check can block it. A session that
// could not be placed keeps both, and the gate runs for every session.
//
// Imports nothing from @opencode-ai/plugin or @kilocode/plugin so one file
// serves both runtimes.

import { spawn } from "node:child_process"
import { existsSync, readdirSync, readFileSync, realpathSync, statSync } from "node:fs"
import { homedir } from "node:os"
import { isAbsolute, join, relative, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"

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
// Where the global install in docs/GLOBAL_SETUP.md keeps the hooks, under the
// home directory.
const GLOBAL_HOOKS_DIR = join(".config", "agents", "hooks")
const PLUGIN_ID = "agent-standards.preflight"
const REPLY_RULES = join(".agents", "instructions", "reply-rules.md")
// A project that deliberately runs without the user's global hooks holds this
// file. Only its presence counts, and it never switches off hooks the project
// ships in its own .agents/hooks/.
const OPT_OUT = join(".agents", "no-global-hooks")

const CONTRACT = 3
const EVENT = "tool.execute.before"
const TEXT_EVENT = "experimental.text.complete"
const TODO_EVENT = "todo.updated"

const DEFAULT_ORDER = 100
const ORDER_RE = /^HOOK_ORDER\s*=\s*(\d+)\s*$/m
const TEXT_RE = /^HOOK_TEXT_EVENT\s*=\s*True\s*$/m
const HEAD_CHARS = 16384

const TIMEOUT_MS = 10000
const SESSION_CAP = 64
const MESSAGE_WINDOW = 8

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
// global install in docs/GLOBAL_SETUP.md puts under ~/.config/agents/hooks/ serve it,
// unless the project opted out, which leaves it with none. Resolved on every call,
// like the directory listing, so either change takes effect without a restart.
const hooksDirectory = (root) => {
  const own = join(root, HOOKS_DIR)

  if (isDirectory(own)) return own
  if (existsSync(join(root, OPT_OUT))) return null

  try {
    const home = homedir()

    return home ? join(home, GLOBAL_HOOKS_DIR) : null
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
// the previous one left, in the same declared order as a tool call. The envelope
// names no agent and no caller, which every hook already reads as unknown. A part
// from a session placed as a subagent is left as written, because nobody reads
// its reply style. `place` is asked only once a hook would run, so a project
// with no text hook makes no session round trip.
const completeText = async (root, text, place) => {
  const hooks = discover(root).filter((hook) => hook.text)

  if (hooks.length === 0) return text
  if ((await place()) === true) return text

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

// Inside a git repository `worktree` is the project root and `directory` only
// the session's start folder, a subdirectory whenever the runtime was started
// deeper in the tree. Anchoring on the root is what keeps .agents/hooks/
// findable. Outside one, OpenCode 1.x and Kilo Code hand "/" as `worktree`, so
// there the start folder is the project, as it is on Claude Code, Codex and
// OpenCode 2.x. A hook taken from the global directory still runs with the
// project root as its working directory and its envelope cwd, so it protects
// the project, not home.
// A global copy stands down when the project ships its own plugin file, so the
// gate runs exactly once, from the project copy. Both paths are compared after
// links are followed, so a ~/.agents linked to the global install is the same
// file rather than a project copy, and a path that cannot be followed is
// compared as written.
const realPath = (path) => {
  try {
    return realpathSync(path)
  } catch {
    return resolve(path)
  }
}

const standsDown = (root) => {
  const ownPath = realPath(fileURLToPath(import.meta.url))
  const projectPluginPath = join(root, ".agents", "plugin", "hooks.js")
  const projectPath = realPath(projectPluginPath)
  const same =
    process.platform === "win32" ? ownPath.toLowerCase() === projectPath.toLowerCase() : ownPath === projectPath

  return !same && existsSync(projectPluginPath)
}

// Whether `inner` is `outer` or sits below it, after links are followed.
const holds = (outer, inner) => {
  const path = relative(realPath(outer), realPath(inner))

  return path === "" || (path !== ".." && !path.startsWith(".." + sep) && !isAbsolute(path))
}

// The OpenCode 1.x and Kilo Code project root: the worktree while it is a git
// root holding the start folder, else the start folder.
const projectRoot = (directory, worktree) => {
  if (typeof directory !== "string" || !directory) return worktree || process.cwd()

  const gitRoot = typeof worktree === "string" && worktree && existsSync(join(worktree, ".git"))

  return gitRoot && holds(worktree, directory) ? worktree : directory
}

// Runs every discovered hook against one tool call and throws the first denial.
const gate = async (root, call) => {
  const hooks = discover(root)

  // Nothing to ask, so nothing to build. This also keeps the session round
  // trips out of a project that checked out no hooks.
  if (hooks.length === 0) return

  const python = await resolvePython(root)

  if (!python) return

  const { subagent, agent, text, tool, args } = await call()

  // is_subagent is left out when the session could not be placed, which the
  // gate reads as an unknown caller and allows.
  const envelope = JSON.stringify({
    contract: CONTRACT,
    event: EVENT,
    tool_name: tool ?? "",
    tool_input: args ?? {},
    agent_type: agent,
    ...(subagent === null ? {} : { is_subagent: subagent }),
    assistant_text: text,
    cwd: root,
  })

  for (const hook of hooks) {
    const message = denial(await run(python, root, hook, envelope), hook.name)

    if (message) throw new Error(message)
  }
}

// OpenCode 1.x and Kilo Code entry point.
export const Preflight = async ({ directory, worktree, client } = {}) => {
  const root = projectRoot(directory, worktree)

  if (standsDown(root)) return {}

  const seen = new Map()
  const placed = new Map()

  return {
    [TEXT_EVENT]: async (input, output) => {
      try {
        if (typeof output?.text !== "string" || !output.text) return

        const sessionID = typeof input?.sessionID === "string" ? input.sessionID : ""

        output.text = await completeText(root, output.text, () => placeSession(client, placed, sessionID))
      } catch {
        return
      }
    },

    [EVENT]: async (input, output) =>
      gate(root, async () => {
        const sessionID = typeof input?.sessionID === "string" ? input.sessionID : ""
        const [subagent, messages] = await Promise.all([
          placeSession(client, placed, sessionID),
          sessionMessages(client, sessionID),
        ])

        return {
          subagent,
          agent: agentName(messages),
          text: subagent === true ? "" : freshAssistantText(messages, seen, sessionID),
          tool: input?.tool,
          args: output?.args,
        }
      }),

    [TODO_EVENT]: async (input, output) => {
      try {
        const todos = input?.todos ?? output?.todos ?? input?.todo ?? output?.todo ?? []

        if (!Array.isArray(todos) || todos.length === 0) return

        const python = await resolvePython(root)

        if (!python) return

        const envelope = JSON.stringify({
          contract: CONTRACT,
          event: EVENT,
          tool_name: "todo",
          tool_input: { todos },
          agent_type: "",
          assistant_text: "",
          cwd: root,
        })

        for (const hook of discover(root)) {
          await run(python, root, hook, envelope)
        }
      } catch {
        return
      }
    },
  }
}

// Newest assistant prose in an OpenCode 2.x session context, whose messages
// carry `type` and `content` where 1.x carries `info.role` and `parts`.
const lastAssistantTextV2 = (messages) => {
  const list = Array.isArray(messages) ? messages : messages?.messages

  for (let i = (list?.length ?? 0) - 1; i >= 0; i--) {
    const message = list[i]

    if (message?.type !== "assistant" && message?.role !== "assistant") continue

    const parts = message.content ?? message.parts ?? []
    const text = (Array.isArray(parts) ? parts : [])
      .filter((part) => part?.type === "text" && typeof part.text === "string")
      .map((part) => part.text)
      .join("\n")

    if (text.trim()) return text
  }

  return ""
}

// true for a child session, false for a root session, null when it could not be read.
const placeSessionV2 = async (ctx, sessionID) => {
  try {
    const session = await ctx?.session?.get?.({ sessionID })

    if (session?.id !== sessionID) return null

    return typeof session.parentID === "string" && session.parentID !== ""
  } catch {
    return null
  }
}

// placeSessionV2 behind a cache shared by every 2.x hook. A session's parent
// never changes, so a definite answer is kept and a failed lookup is retried.
const sessionPlacerV2 = (ctx) => {
  const placed = new Map()

  return async (sessionID) => {
    if (!sessionID) return null
    if (placed.has(sessionID)) return placed.get(sessionID)

    const subagent = await placeSessionV2(ctx, sessionID)

    if (subagent !== null) {
      if (placed.size >= SESSION_CAP) placed.clear()
      placed.set(sessionID, subagent)
    }

    return subagent
  }
}

// The reply rules file for a project: its own copy when it ships one, else the
// global install's, else null. OpenCode 2.x ignores the `instructions` key that
// loads this file on 1.x and Kilo Code, so the 2.x entry point adds it itself.
const replyRules = (root) => {
  const own = join(root, REPLY_RULES)

  if (existsSync(own)) return own

  try {
    const home = homedir()
    const global = home ? join(home, ".config", "agents", "instructions", "reply-rules.md") : null

    return global && existsSync(global) ? global : null
  } catch {
    return null
  }
}

// Adds the reply rules as one more system part on every model request of the
// main thread and keeps the built-in prompt. A session placed as a subagent
// gets nothing, because nobody reads its reply style and the rules cost tokens
// on every request. A session that could not be placed still gets them. Any
// failure adds nothing.
const addReplyRules = (root, place) => async (event) => {
  try {
    if ((await place(event?.sessionID)) === true) return

    const path = replyRules(root)

    if (!path || !Array.isArray(event?.system)) return

    event.system.push({ type: "text", text: "Instructions from: " + path + "\n" + readFileSync(path, "utf8") })
  } catch {
    return
  }
}

// OpenCode 2.x entry point. Its only hook that can refuse anything is the tool
// execute.before hook, so the gate and the reply checks all ride it. The
// session context hook carries the reply rules. Reply rules and reply checks
// are for the main thread only: a session placed as a subagent gets no rules
// and hands the hooks no assistant text, so no reply check can block it. The
// gate itself still runs for every session.
const setup = async (ctx) => {
  const root = ctx?.location?.project?.directory || ctx?.location?.directory || process.cwd()

  if (standsDown(root)) return

  // Loud stand-down: a host without the tool hook API would die on the
  // first await below and the loader drops the failure quiet, so say so in
  // the service log instead and register nothing.
  if (typeof ctx?.tool?.hook !== "function" || typeof ctx?.session?.get !== "function") {
    console.error(
      `[${PLUGIN_ID}] setup stands down: host has no tool/session hooks ` +
        `(tool.hook: ${typeof ctx?.tool?.hook}, session.get: ${typeof ctx?.session?.get})`,
    )
    return
  }

  const place = sessionPlacerV2(ctx)

  try {
    await ctx.session?.hook?.("context", addReplyRules(root, place))
  } catch {
    // Without the hook the rules are simply not added, which never blocks anything.
  }

  const seen = new Map()

  await ctx.tool.hook("execute.before", async (event) =>
    gate(root, async () => {
      const sessionID = typeof event?.sessionID === "string" ? event.sessionID : ""
      const subagent = await place(sessionID)
      let messages = null

      try {
        messages = sessionID && subagent !== true ? await ctx.session.context({ sessionID }) : null
      } catch {
        messages = null
      }

      const text = lastAssistantTextV2(messages)
      let fresh = ""

      if (sessionID && text && seen.get(sessionID) !== text) {
        if (seen.size >= SESSION_CAP) seen.clear()
        seen.set(sessionID, text)
        fresh = text
      }

      return {
        subagent,
        agent: typeof event?.agent === "string" ? event.agent : "",
        text: fresh,
        tool: event?.tool,
        args: event?.input,
      }
    }),
  )
}

export default { id: PLUGIN_ID, server: Preflight, setup }
