// Test driver for the OpenCode and Kilo Code hook runner.
//
// Loads .agents/plugin/hooks.js exactly the way a runtime would, then replays a
// scripted sequence of tool calls against one plugin instance so session state
// and mid-session filesystem changes are both observable.
//
// Reads one job as JSON on stdin:
//
//   {
//     "plugin": "<absolute path to hooks.js>",
//     "root":   "<project root handed to the plugin>",
//     "sessions": {"<id>": {<Session>} | null, ...},
//     "wrapped": false,
//     "path": "<PATH for the spawned hooks, optional>",
//     "home": "<home directory the plugin and its hooks see, optional>",
//     "directory": "<start folder handed to server(), optional, root when absent>",
//     "worktree": "<worktree handed to server(), optional, none when absent>",
//     "steps": [
//       {"kind": "call",  "input": {...}, "output": {...}, "messages": [...]},
//       {"kind": "message", "input": {...}, "output": {...}},
//       {"kind": "text", "input": {...}, "output": {"text": "..."}},
//       {"kind": "todo", "input": {"todos": [...]}},
//       {"kind": "lookups"},
//       {"kind": "fetches"},
//       {"kind": "write", "path": "relative/name.py", "content": "..."},
//       {"kind": "remove", "path": "relative/name.py"}
//     ]
//   }
//
// Writes one JSON array on stdout, one entry per step:
// {"ok": true} for an allowed call, {"ok": false, "error": "..."} for a block.
// A message step answers {"ok": true, "parts": [...]} with the parts the
// plugin left on the output, and a lookups step answers {"ok": true, "count": n}
// with the number of session.get calls made so far. A text step answers
// {"ok": true, "text": "..."} with the text the plugin left on the output. A fetches step answers
// {"ok": true, "limits": [...]} with the limit each session.messages call
// asked for so far, null for a call that asked for the whole history.
//
// session.get resolves an id listed in "sessions" to that object, bare or
// wrapped in { data } when "wrapped" is true, and throws for an id listed as
// null or not listed at all. session.messages honours a limit the way both
// runtimes do, answering the newest `limit` messages oldest first.

import { mkdirSync, rmSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { pathToFileURL } from "node:url"

const readStdin = () =>
  new Promise((resolve) => {
    let data = ""

    process.stdin.setEncoding("utf8")
    process.stdin.on("data", (chunk) => {
      data += chunk
    })
    process.stdin.on("end", () => resolve(data))
  })

const job = JSON.parse(await readStdin())

if (typeof job.path === "string") process.env.PATH = job.path

// os.homedir() reads HOME on POSIX and USERPROFILE on Windows, and so does
// Python's Path.home() in every spawned hook, so setting both moves the home
// directory for the plugin and the hooks alike.
if (typeof job.home === "string") {
  process.env.HOME = job.home
  process.env.USERPROFILE = job.home
}

const plugin = await import(pathToFileURL(job.plugin).href)

let messages = []

const sessions = job.sessions ?? {}
let lookups = 0
const limits = []

const list = async ({ query } = {}) => {
  const limit = query?.limit ?? null

  limits.push(limit)

  return limit ? messages.slice(-limit) : messages
}

const get = async ({ path } = {}) => {
  lookups++

  const session = sessions[path?.id]

  if (!session) throw new Error("no such session: " + path?.id)

  return job.wrapped ? { data: session } : session
}

const client = { session: { messages: list, get } }

// The default export is { id, server, setup }. OpenCode 1.x and Kilo Code call
// server(), OpenCode 2.x calls setup(), and "v2": true drives the second the
// way 2.x does: one execute.before callback, session.get({ sessionID }) and
// session.context({ sessionID }) on the context, and the tool arguments on
// the event itself.
const entry = plugin.default
let hooks = {}
let handler = null

if (job.v2) {
  const registered = {}
  const ctx = {
    location: { project: { directory: job.root }, directory: job.root },
    session: {
      get: async ({ sessionID } = {}) => {
        lookups++

        const session = sessions[sessionID]

        if (!session) throw new Error("no such session: " + sessionID)

        return session
      },
      context: async () => messages,
      hook: async (name, callback) => {
        registered["session." + name] = callback
      },
    },
    tool: {
      hook: async (name, callback) => {
        registered[name] = callback
      },
    },
  }

  await entry.setup(ctx)
  hooks = Object.fromEntries(
    Object.keys(registered).map((name) => [name.startsWith("session.") ? name : "tool." + name, registered[name]]),
  )

  const callback = registered["execute.before"]

  handler = callback
    ? (input, output) =>
        callback({ sessionID: input?.sessionID, tool: input?.tool, agent: input?.agent, input: output?.args })
    : null
} else {
  const server = typeof entry === "function" ? entry : entry.server

  const worktree = typeof job.worktree === "string" ? { worktree: job.worktree } : {}

  hooks = await server({ directory: job.directory ?? job.root, ...worktree, client })
  handler = hooks["tool.execute.before"]
}

const results = []

for (const step of job.steps) {
  if (step.kind === "write") {
    const target = join(job.root, step.path)

    mkdirSync(dirname(target), { recursive: true })
    writeFileSync(target, step.content, "utf8")
    results.push({ ok: true })
    continue
  }

  if (step.kind === "remove") {
    rmSync(join(job.root, step.path), { force: true })
    results.push({ ok: true })
    continue
  }

  if (step.kind === "lookups") {
    results.push({ ok: true, count: lookups })
    continue
  }

  if (step.kind === "fetches") {
    results.push({ ok: true, limits: [...limits] })
    continue
  }

  if (step.kind === "keys") {
    results.push({ ok: true, keys: Object.keys(hooks) })
    continue
  }

  if (step.kind === "context") {
    const event = { system: [], ...(step.sessionID ? { sessionID: step.sessionID } : {}) }
    const callback = hooks["session.context"]

    if (typeof callback === "function") await callback(event)
    results.push({ ok: true, system: event.system })
    continue
  }

  if (step.kind === "message") {
    const output = step.output ?? {}

    if (typeof hooks["chat.message"] !== "function") {
      results.push({ ok: true, parts: output.parts ?? null })
      continue
    }

    await hooks["chat.message"](step.input ?? {}, output)
    results.push({ ok: true, parts: output.parts ?? null })
    continue
  }

  if (step.kind === "todo") {
    const callback = hooks["todo.updated"]

    try {
      if (typeof callback === "function") await callback(step.input ?? {}, step.output ?? {})
      results.push({ ok: true })
    } catch (error) {
      results.push({ ok: false, error: String(error?.message ?? error) })
    }

    continue
  }

  if (step.kind === "text") {
    const output = step.output ?? {}

    if (typeof hooks["experimental.text.complete"] !== "function") {
      results.push({ ok: true, text: output.text ?? null })
      continue
    }

    try {
      await hooks["experimental.text.complete"](step.input ?? {}, output)
      results.push({ ok: true, text: output.text ?? null })
    } catch (error) {
      results.push({ ok: false, error: String(error?.message ?? error) })
    }

    continue
  }

  messages = step.messages ?? []

  if (typeof handler !== "function") {
    results.push({ ok: true })
    continue
  }

  try {
    await handler(step.input ?? {}, step.output ?? {})
    results.push({ ok: true })
  } catch (error) {
    results.push({ ok: false, error: String(error?.message ?? error) })
  }
}

process.stdout.write(JSON.stringify(results))
