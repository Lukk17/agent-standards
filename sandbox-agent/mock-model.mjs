// Mock OpenAI-compatible chat completions endpoint for the container sandbox.
//
// Lets a real OpenCode 2.x session run a turn without provider credentials. It
// answers from a script keyed on a marker in the newest user message, streams
// the answer the way the chat completions API does, and appends every request
// body to a JSON lines log so the suite can read what the model was sent.
//
// Usage: node mock-model.mjs <port> <request log>
//
// Markers, each answered only once per conversation, the turn after a tool
// result always being plain text:
//   SANDBOX-WRITE-PROBE <path>    a write tool call creating <path>
//   SANDBOX-TASK-PROBE <agent>    a subagent tool call starting <agent>
//   anything else                 plain text
//
// Reply-style markers, for OpenCode 1.x and Kilo Code, which keep one prose
// text and two glob calls per session so a reply check reads the prose at the
// second call, the first prose being stored only after its own call started:
//   SANDBOX-TEXT-PROBE                 the main session writes PROBE_PROSE
//   SANDBOX-TASK-TEXT-PROBE <agent>    a task (1.x) or subagent (2.x) call
//                                      starting <agent>, whose session does
//                                      the same with CHILD_PROSE

import { appendFileSync } from "node:fs"
import { createServer } from "node:http"

const [, , portArgument, logPath] = process.argv
const port = Number(portArgument)

const WRITE_RE = /SANDBOX-WRITE-PROBE ([\w./-]+)/
const TASK_RE = /SANDBOX-TASK-PROBE ([\w-]+)/
const TASK_TEXT_RE = /SANDBOX-TASK-TEXT-PROBE ([\w-]+)/
const CHILD_TEXT_MARKER = "SANDBOX-CHILD-TEXT-PROBE"
// An em dash a text rewrite fixes, and a semicolon and an unnumbered question
// it leaves for the tool-call checks to refuse.
const PROBE_PROSE = "Main prose — SANDBOX-MAIN-PROSE; Should I go on?"
const CHILD_PROSE = "Child prose — SANDBOX-CHILD-PROSE; Should I go on?"

const textOf = (content) => {
  if (typeof content === "string") return content
  if (!Array.isArray(content)) return ""

  return content.map((part) => (typeof part?.text === "string" ? part.text : "")).join("\n")
}

const toolNamed = (tools, wanted) =>
  (Array.isArray(tools) ? tools : []).map((tool) => tool?.function?.name).find((name) => name === wanted)

// One session's prose then two globs, keyed on how many tool results it holds.
const proseAndTwoGlobs = (prose, toolResults) => {
  if (toolResults === 0) return { text: prose, tool: "glob", args: { pattern: "*.sandbox-first" } }
  if (toolResults === 1) return { tool: "glob", args: { pattern: "*.sandbox-second" } }

  return { text: "sandbox probe finished" }
}

// The reply-style markers, or null for every other prompt.
const replyStyleAnswer = (body) => {
  const messages = Array.isArray(body?.messages) ? body.messages : []
  const prompt = messages.filter((message) => message?.role === "user").map((message) => textOf(message.content)).join("\n")
  const toolResults = messages.filter((message) => message?.role === "tool").length

  if (!toolNamed(body?.tools, "glob")) return null
  if (prompt.includes(CHILD_TEXT_MARKER)) return proseAndTwoGlobs(CHILD_PROSE, toolResults)
  if (prompt.includes("SANDBOX-TEXT-PROBE")) return proseAndTwoGlobs(PROBE_PROSE, toolResults)

  const task = TASK_TEXT_RE.exec(prompt)

  if (!task) return null
  if (toolResults > 0) return { text: "sandbox probe finished" }

  const child = "Reply with one word. " + CHILD_TEXT_MARKER

  if (toolNamed(body.tools, "task")) {
    return { tool: "task", args: { description: "sandbox probe", prompt: child, subagent_type: task[1] } }
  }

  return { tool: "subagent", args: { agent: task[1], description: "sandbox probe", prompt: child } }
}

// OpenCode 1.x and Kilo Code name the write tool's path filePath, 2.x path.
const writeArgs = (tools, path) => {
  const write = (Array.isArray(tools) ? tools : []).find((tool) => tool?.function?.name === "write")
  const key = write?.function?.parameters?.properties?.filePath ? "filePath" : "path"

  return { [key]: path, content: "written by the sandbox probe\n" }
}

const answer = (body) => {
  const messages = Array.isArray(body?.messages) ? body.messages : []
  const last = messages[messages.length - 1]
  const replyStyle = replyStyleAnswer(body)

  if (replyStyle) return replyStyle
  if (!last || last.role !== "user") return { text: "sandbox probe finished" }

  const prompt = textOf(last.content)
  const write = WRITE_RE.exec(prompt)

  if (write && toolNamed(body.tools, "write")) {
    return { tool: "write", args: writeArgs(body.tools, write[1]) }
  }

  const task = TASK_RE.exec(prompt)

  if (task && toolNamed(body.tools, "subagent")) {
    return {
      tool: "subagent",
      args: { agent: task[1], description: "sandbox probe", prompt: "Reply with one word. SANDBOX-CHILD-PROBE" },
    }
  }

  return { text: "sandbox probe finished" }
}

const chunk = (delta, finish = null) =>
  "data: " +
  JSON.stringify({
    id: "chatcmpl-sandbox",
    object: "chat.completion.chunk",
    created: 0,
    model: "sandbox-model",
    choices: [{ index: 0, delta, finish_reason: finish }],
  }) +
  "\n\n"

const stream = (reply) => {
  if (reply.tool) {
    const call = { index: 0, id: "call_sandbox", type: "function", function: { name: reply.tool, arguments: JSON.stringify(reply.args) } }
    const prose = reply.text ? chunk({ role: "assistant", content: reply.text }) : ""

    return prose + chunk({ role: "assistant", tool_calls: [call] }) + chunk({}, "tool_calls") + "data: [DONE]\n\n"
  }

  return chunk({ role: "assistant", content: reply.text }) + chunk({}, "stop") + "data: [DONE]\n\n"
}

const server = createServer((request, response) => {
  let raw = ""

  request.setEncoding("utf8")
  request.on("data", (part) => {
    raw += part
  })
  request.on("end", () => {
    let body = null

    try {
      body = raw ? JSON.parse(raw) : null
    } catch {
      body = null
    }

    appendFileSync(logPath, JSON.stringify({ method: request.method, url: request.url, body }) + "\n")

    if (request.method === "GET" && request.url.endsWith("/models")) {
      response.writeHead(200, { "content-type": "application/json" })
      response.end(JSON.stringify({ object: "list", data: [{ id: "sandbox-model", object: "model" }] }))
      return
    }

    const reply = answer(body)

    if (body?.stream) {
      response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" })
      response.end(stream(reply))
      return
    }

    const message = reply.tool
      ? { role: "assistant", content: reply.text ?? null, tool_calls: [{ id: "call_sandbox", type: "function", function: { name: reply.tool, arguments: JSON.stringify(reply.args) } }] }
      : { role: "assistant", content: reply.text }

    response.writeHead(200, { "content-type": "application/json" })
    response.end(
      JSON.stringify({
        id: "chatcmpl-sandbox",
        object: "chat.completion",
        created: 0,
        model: "sandbox-model",
        choices: [{ index: 0, message, finish_reason: reply.tool ? "tool_calls" : "stop" }],
      }),
    )
  })
})

server.listen(port, "127.0.0.1")
