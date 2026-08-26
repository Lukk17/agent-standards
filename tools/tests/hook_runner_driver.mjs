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
//     "steps": [
//       {"kind": "call",  "input": {...}, "output": {...}, "messages": [...]},
//       {"kind": "write", "path": "relative/name.py", "content": "..."},
//       {"kind": "remove", "path": "relative/name.py"}
//     ]
//   }
//
// Writes one JSON array on stdout, one entry per step:
// {"ok": true} for an allowed call, {"ok": false, "error": "..."} for a block.

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
const plugin = await import(pathToFileURL(job.plugin).href)

let messages = []

const client = { session: { messages: async () => messages } }
const hooks = await plugin.default({ directory: job.root, client })
const handler = hooks["tool.execute.before"]

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

  messages = step.messages ?? []

  try {
    await handler(step.input ?? {}, step.output ?? {})
    results.push({ ok: true })
  } catch (error) {
    results.push({ ok: false, error: String(error?.message ?? error) })
  }
}

process.stdout.write(JSON.stringify(results))
