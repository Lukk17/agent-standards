// Scripted model server for the subagent-write end-to-end check.
//
// Lets a real agent binary run a real main thread and a real subagent without
// provider credentials. It speaks the three wire formats the supported agents
// use, each streamed the way its client reads it:
//
//   POST .../messages            Anthropic Messages, Claude Code
//   POST .../responses           OpenAI Responses, Codex and GitHub Copilot
//   POST .../chat/completions    OpenAI Chat Completions, OpenCode and Kilo Code
//
// Every request is answered from a script keyed on a marker in the newest user
// message that carries one, and appended to a JSON lines log with the role the
// script gave it, so the suite can read back what each session was sent. The
// headers each agent sends say independently whether a request came from a
// subagent, and a request whose headers and marker disagree is answered with
// text only, so a mixed-up session can never make the scripted write.
//
// Usage: node server.mjs <port> <request log>
//
// Markers, the token being the exact file content without its newline:
//   E2E-SPAWN <agent> <path> <token>     main thread: start <agent> with
//                                        E2E-SUBAGENT-WRITE <path> <token>,
//                                        wait for it where the spawn tool
//                                        returns at once, then finish
//   E2E-SUBAGENT-WRITE <path> <token>    subagent: write <path>, then finish
//   E2E-REVIEW <agent> <path> <token>    main thread: start <agent> with
//                                        E2E-SUBAGENT-REPORT <path> <token>,
//                                        then finish, as E2E-SPAWN does
//   E2E-SUBAGENT-REPORT <path> <token>   subagent: finish at once with text,
//                                        so its first request shows what the
//                                        agent preloaded into it
//   E2E-MAIN-WRITE <path> <token>        main thread: write <path> itself,
//                                        then finish
//
// A conversation with no marker gets a one-word answer, and on the Chat
// Completions route the reply the sandbox mock-model.mjs script gives, so one
// server also answers every marker that script knows.

import { appendFileSync, realpathSync } from "node:fs"
import { createServer } from "node:http"
import { pathToFileURL } from "node:url"

import { answer as chatAnswer, completion as chatCompletion, stream as chatStream } from "../mock-model.mjs"

const MARKER_RE = /E2E-((?:SPAWN|REVIEW) ([\w.-]+)|SUBAGENT-WRITE|SUBAGENT-REPORT|MAIN-WRITE) ([\w./-]+) ([\w-]+)/g
const SPAWN_TOOLS = ["Agent", "Task", "task", "subagent", "spawn_agent"]
const WAIT_TOOLS = ["wait_agent"]
// Native file writers first, a shell only where the agent offers no writer.
const WRITE_TOOLS = ["Write", "create", "write", "exec_command", "shell", "bash", "Bash"]
const DONE = { main: "E2E main thread finished", subagent: "E2E subagent finished", other: "ok" }
const WAIT_MS = 300000

let sequence = 0

const nextId = (prefix) => `${prefix}_e2e_${++sequence}`

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value)

const parseJson = (raw) => {
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

// Every string inside a content value, joined, whatever block shape holds it.
export const flatten = (value) => {
  if (typeof value === "string") return value
  if (Array.isArray(value)) return value.map(flatten).filter(Boolean).join("\n")
  if (!isObject(value)) return ""

  return ["text", "content", "output", "input_text", "file_text"]
    .filter((key) => key in value)
    .map((key) => flatten(value[key]))
    .filter(Boolean)
    .join("\n")
}

const argsOf = (raw) => (isObject(raw) ? raw : parseJson(raw) ?? { input: raw })

// --- One conversation shape for all three wire formats -----------------------
//
// entries: {kind: "system" | "user" | "assistant", text}
//          {kind: "call", id, name, args}
//          {kind: "result", id, text}
// tools:   {name, namespace, properties}

const anthropicConversation = (body) => {
  const entries = [{ kind: "system", text: flatten(body.system) }]

  for (const message of Array.isArray(body.messages) ? body.messages : []) {
    const blocks = typeof message?.content === "string" ? [{ type: "text", text: message.content }] : message?.content

    for (const block of Array.isArray(blocks) ? blocks : []) {
      if (block?.type === "text") entries.push({ kind: message.role === "user" ? "user" : "assistant", text: block.text ?? "" })
      if (block?.type === "tool_use") entries.push({ kind: "call", id: block.id, name: block.name, args: block.input ?? {} })
      if (block?.type === "tool_result") entries.push({ kind: "result", id: block.tool_use_id, text: flatten(block.content) })
    }
  }

  const tools = (Array.isArray(body.tools) ? body.tools : []).map((tool) => ({
    name: tool?.name,
    namespace: null,
    properties: tool?.input_schema?.properties ?? {},
  }))

  return { entries, tools }
}

const responsesTools = (tools, namespace = null) =>
  (Array.isArray(tools) ? tools : []).flatMap((tool) =>
    tool?.type === "namespace"
      ? responsesTools(tool.tools, tool.name)
      : [{ name: tool?.name, namespace, properties: tool?.parameters?.properties ?? {} }],
  )

const responsesConversation = (body) => {
  const entries = [{ kind: "system", text: flatten(body.instructions) }]
  const input = typeof body.input === "string" ? [{ type: "message", role: "user", content: body.input }] : body.input

  for (const item of Array.isArray(input) ? input : []) {
    const type = item?.type ?? "message"

    if (type === "message") {
      const kind = item.role === "user" ? "user" : item.role === "assistant" ? "assistant" : "system"
      entries.push({ kind, text: flatten(item.content) })
    }
    if (type === "function_call") entries.push({ kind: "call", id: item.call_id, name: item.name, args: argsOf(item.arguments) })
    if (type === "custom_tool_call") entries.push({ kind: "call", id: item.call_id, name: item.name, args: { input: item.input } })
    if (type === "function_call_output" || type === "custom_tool_call_output") {
      entries.push({ kind: "result", id: item.call_id, text: flatten(item.output) })
    }
  }

  return { entries, tools: responsesTools(body.tools) }
}

const chatConversation = (body) => {
  const entries = []

  for (const message of Array.isArray(body.messages) ? body.messages : []) {
    const role = message?.role

    if (role === "tool") entries.push({ kind: "result", id: message.tool_call_id, text: flatten(message.content) })
    else if (role === "user") entries.push({ kind: "user", text: flatten(message.content) })
    else if (role === "assistant") {
      if (message.content) entries.push({ kind: "assistant", text: flatten(message.content) })
      for (const call of Array.isArray(message.tool_calls) ? message.tool_calls : []) {
        entries.push({ kind: "call", id: call?.id, name: call?.function?.name, args: argsOf(call?.function?.arguments) })
      }
    } else entries.push({ kind: "system", text: flatten(message?.content) })
  }

  const tools = (Array.isArray(body.tools) ? body.tools : []).map((tool) => ({
    name: tool?.function?.name,
    namespace: null,
    properties: tool?.function?.parameters?.properties ?? {},
  }))

  return { entries, tools }
}

export const CONVERSATIONS = {
  anthropic: anthropicConversation,
  responses: responsesConversation,
  chat: chatConversation,
}

// The wire format a request path names, or null for a path no format serves.
export const formatOf = (method, url) => {
  const path = String(url ?? "").split("?")[0]

  if (method !== "POST") return null
  if (path.endsWith("/messages/count_tokens")) return "count_tokens"
  if (path.endsWith("/messages")) return "anthropic"
  if (path.endsWith("/responses")) return "responses"
  if (path.endsWith("/chat/completions")) return "chat"

  return null
}

// --- The script ----------------------------------------------------------------

const ROLE_OF = { SPAWN: "main", REVIEW: "main", "MAIN-WRITE": "main", "SUBAGENT-WRITE": "subagent", "SUBAGENT-REPORT": "subagent" }
// The prompt each spawning marker hands the subagent it starts.
const SUBAGENT_MARKER_OF = { SPAWN: "SUBAGENT-WRITE", REVIEW: "SUBAGENT-REPORT" }

// The newest user entry carrying a marker decides the session. A subagent's
// prompt is a user message only inside its own session, while the main thread
// sees it only as the arguments of its own spawn call, so the two never mix.
export const classify = (entries) => {
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const entry = entries[index]
    if (entry.kind !== "user") continue

    const found = [...entry.text.matchAll(MARKER_RE)].at(-1)
    if (!found) continue

    const marker = found[1].split(" ")[0]

    return {
      role: ROLE_OF[marker],
      marker,
      agent: found[2] ?? null,
      path: found[3],
      token: found[4],
      after: entries.slice(index + 1),
    }
  }

  return { role: "other", marker: null, after: [] }
}

// The session the transport headers name, measured on the pinned binaries:
// Claude Code adds x-claude-code-agent-id inside a subagent, Codex puts
// thread_source "subagent" in x-codex-turn-metadata, the Copilot CLI sends
// x-interaction-type conversation-subagent, and OpenCode and Kilo Code send
// x-parent-session-id from a child session. Null for a client none of them is.
export const headerRole = (headers) => {
  const header = (name) => headers?.[name]
  const turn = parseJson(header("x-codex-turn-metadata") ?? "")

  if (String(header("user-agent") ?? "").startsWith("claude-cli/")) {
    return header("x-claude-code-agent-id") ? "subagent" : "main"
  }
  if (isObject(turn)) return turn.thread_source === "subagent" ? "subagent" : "main"
  if (header("x-initiator") !== undefined) return header("x-interaction-type") === "conversation-subagent" ? "subagent" : "main"
  if (header("x-session-id") !== undefined) return header("x-parent-session-id") ? "subagent" : "main"

  return null
}

const pick = (properties, names) => names.find((name) => name in properties)

const toolFrom = (tools, names) => names.map((name) => tools.find((tool) => tool.name === name)).find(Boolean)

// Spawn arguments in whatever names the offered schema uses.
export const spawnArgs = (tool, agent, prompt) => {
  const properties = tool.properties
  const args = {
    [pick(properties, ["subagent_type", "agent_type", "agent"]) ?? "subagent_type"]: agent,
    [pick(properties, ["prompt", "message"]) ?? "prompt"]: prompt,
  }

  if ("description" in properties) args.description = "E2E proof write"
  if ("name" in properties) args.name = "e2e-proof"
  if ("mode" in properties) args.mode = "sync"
  if ("fork_context" in properties) args.fork_context = false

  return args
}

// Write arguments for a file writer, or a shell redirect for a shell tool.
export const writeArgs = (tool, path, content) => {
  const properties = tool.properties
  const shellKey = pick(properties, ["cmd", "command"])

  if (shellKey && !pick(properties, ["file_path", "filePath", "path"])) {
    return { [shellKey]: `printf '%s\\n' '${content.trimEnd()}' > '${path}'` }
  }

  return {
    [pick(properties, ["file_path", "filePath", "path"]) ?? "file_path"]: path,
    [pick(properties, ["content", "file_text"]) ?? "content"]: content,
  }
}

// The agent id a spawn result names, read from JSON or from the text.
export const spawnedId = (text) => {
  const parsed = parseJson(text)
  const fromJson = isObject(parsed) ? parsed.agent_id ?? parsed.id ?? parsed.target : null

  return fromJson ?? /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.exec(text)?.[0] ?? null
}

const finish = (role) => ({ kind: "text", text: DONE[role] })

const missing = (what) => ({ kind: "text", text: `E2E: the request offers no ${what} tool` })

const callReply = (tool, args) => ({ kind: "call", tool: tool.name, namespace: tool.namespace, args })

// The reply the script gives one request, in a shape no wire format owns.
export const plan = ({ entries, tools }, headers = {}) => {
  const session = { ...classify(entries), headerRole: headerRole(headers) }
  const results = session.after.filter((entry) => entry.kind === "result")
  const content = `${session.token}\n`

  if (session.role !== "other" && session.headerRole !== null && session.headerRole !== session.role) {
    return { session, reply: { kind: "text", text: `E2E: role conflict, marker says ${session.role}, headers say ${session.headerRole}` } }
  }

  if (session.marker === "SUBAGENT-REPORT") return { session, reply: finish(session.role) }

  if (session.role === "subagent" || session.marker === "MAIN-WRITE") {
    if (results.length > 0) return { session, reply: finish(session.role) }

    const tool = toolFrom(tools, WRITE_TOOLS)

    return { session, reply: tool ? callReply(tool, writeArgs(tool, session.path, content)) : missing("write") }
  }

  if (session.marker in SUBAGENT_MARKER_OF) {
    if (results.length === 0) {
      const tool = toolFrom(tools, SPAWN_TOOLS)
      const prompt = `E2E-${SUBAGENT_MARKER_OF[session.marker]} ${session.path} ${session.token}`

      return { session, reply: tool ? callReply(tool, spawnArgs(tool, session.agent, prompt)) : missing("spawn") }
    }

    const spawn = session.after.find((entry) => entry.kind === "call" && SPAWN_TOOLS.includes(entry.name))
    const waited = session.after.some((entry) => entry.kind === "call" && WAIT_TOOLS.includes(entry.name))
    const wait = toolFrom(tools, WAIT_TOOLS)

    if (spawn?.name === "spawn_agent" && wait && !waited) {
      const result = session.after.find((entry) => entry.kind === "result" && entry.id === spawn.id)
      const id = spawnedId(result?.text ?? "")

      if (id) return { session, reply: callReply(wait, { targets: [id], timeout_ms: WAIT_MS }) }
    }

    return { session, reply: finish("main") }
  }

  return { session, reply: finish("other") }
}

// --- Rendering -------------------------------------------------------------------

const sse = (event, data) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`

const anthropicMessage = (reply, model) => ({
  id: nextId("msg"),
  type: "message",
  role: "assistant",
  model,
  content:
    reply.kind === "call"
      ? [{ type: "tool_use", id: nextId("toolu"), name: reply.tool, input: reply.args }]
      : [{ type: "text", text: reply.text }],
  stop_reason: reply.kind === "call" ? "tool_use" : "end_turn",
  stop_sequence: null,
  usage: { input_tokens: 1, output_tokens: 1 },
})

const anthropicStream = (message) => {
  const [block] = message.content
  const start = block.type === "tool_use" ? { ...block, input: {} } : { type: "text", text: "" }
  const delta =
    block.type === "tool_use"
      ? { type: "input_json_delta", partial_json: JSON.stringify(block.input) }
      : { type: "text_delta", text: block.text }

  return (
    sse("message_start", { type: "message_start", message: { ...message, content: [], stop_reason: null } }) +
    sse("content_block_start", { type: "content_block_start", index: 0, content_block: start }) +
    sse("content_block_delta", { type: "content_block_delta", index: 0, delta }) +
    sse("content_block_stop", { type: "content_block_stop", index: 0 }) +
    sse("message_delta", {
      type: "message_delta",
      delta: { stop_reason: message.stop_reason, stop_sequence: null },
      usage: { output_tokens: 1 },
    }) +
    sse("message_stop", { type: "message_stop" })
  )
}

const responsesItem = (reply) => {
  if (reply.kind === "call") {
    const item = {
      type: "function_call",
      id: nextId("fc"),
      call_id: nextId("call"),
      name: reply.tool,
      arguments: JSON.stringify(reply.args),
      status: "completed",
    }

    return reply.namespace ? { ...item, namespace: reply.namespace } : item
  }

  return {
    type: "message",
    id: nextId("msg"),
    role: "assistant",
    status: "completed",
    content: [{ type: "output_text", text: reply.text, annotations: [] }],
  }
}

const responsesBody = (item, model) => ({
  id: nextId("resp"),
  object: "response",
  created_at: 0,
  status: "completed",
  model,
  output: [item],
  usage: {
    input_tokens: 1,
    input_tokens_details: { cached_tokens: 0 },
    output_tokens: 1,
    output_tokens_details: { reasoning_tokens: 0 },
    total_tokens: 2,
  },
})

const responsesStream = (response) => {
  const [item] = response.output
  const started = item.type === "message" ? { ...item, status: "in_progress", content: [] } : { ...item, arguments: "" }
  const delta =
    item.type === "message"
      ? sse("response.output_text.delta", {
          type: "response.output_text.delta",
          item_id: item.id,
          output_index: 0,
          content_index: 0,
          delta: item.content[0].text,
        })
      : sse("response.function_call_arguments.delta", {
          type: "response.function_call_arguments.delta",
          item_id: item.id,
          output_index: 0,
          delta: item.arguments,
        })

  return (
    sse("response.created", { type: "response.created", response: { ...response, status: "in_progress", output: [] } }) +
    sse("response.output_item.added", { type: "response.output_item.added", output_index: 0, item: started }) +
    delta +
    sse("response.output_item.done", { type: "response.output_item.done", output_index: 0, item }) +
    sse("response.completed", { type: "response.completed", response })
  )
}

// The status, content type and body that answer one request.
export const respond = (format, body, headers = {}) => {
  const model = typeof body?.model === "string" ? body.model : "sandbox-model"

  if (format === "count_tokens") {
    return { status: 200, type: "application/json", text: JSON.stringify({ input_tokens: 1 }), decision: null }
  }

  const decision = plan(CONVERSATIONS[format](isObject(body) ? body : {}), headers)
  const { reply } = decision

  if (format === "chat" && decision.session.role === "other") {
    const legacy = chatAnswer(body)
    decision.reply = legacy.tool ? { kind: "call", tool: legacy.tool, args: legacy.args, legacy: true } : { kind: "text", text: legacy.text, legacy: true }

    return body?.stream
      ? { status: 200, type: "text/event-stream", text: chatStream(legacy), decision }
      : { status: 200, type: "application/json", text: JSON.stringify(chatCompletion(legacy)), decision }
  }

  if (format === "chat") {
    const legacy = reply.kind === "call" ? { id: nextId("call"), tool: reply.tool, args: reply.args } : { text: reply.text }

    return body?.stream
      ? { status: 200, type: "text/event-stream", text: chatStream(legacy), decision }
      : { status: 200, type: "application/json", text: JSON.stringify(chatCompletion(legacy)), decision }
  }

  if (format === "anthropic") {
    const message = anthropicMessage(reply, model)

    return body?.stream
      ? { status: 200, type: "text/event-stream", text: anthropicStream(message), decision }
      : { status: 200, type: "application/json", text: JSON.stringify(message), decision }
  }

  const response = responsesBody(responsesItem(reply), model)

  return body?.stream === false
    ? { status: 200, type: "application/json", text: JSON.stringify(response), decision }
    : { status: 200, type: "text/event-stream", text: responsesStream(response), decision }
}

// --- The log and the server --------------------------------------------------------

// One log line: what the suite asserts on, then the raw body for a human.
// The authorization header is the only one left out.
export const record = (sequenceNumber, request, format, body, decision) => {
  const conversation = format && CONVERSATIONS[format] && isObject(body) ? CONVERSATIONS[format](body) : null
  const session = decision?.session ?? null
  const after = session?.after ?? []
  const headers = Object.fromEntries(Object.entries(request.headers ?? {}).filter(([name]) => name !== "authorization"))

  return {
    seq: sequenceNumber,
    method: request.method,
    url: request.url,
    format,
    headers,
    role: session?.role ?? null,
    header_role: session?.headerRole ?? null,
    tool_count: conversation ? conversation.tools.length : 0,
    marker: session?.marker ?? null,
    agent: session?.agent ?? null,
    path: session?.path ?? null,
    token: session?.token ?? null,
    calls: after
      .filter((entry) => entry.kind === "call")
      .map((call) => ({
        name: call.name,
        args: call.args,
        result: after.find((entry) => entry.kind === "result" && entry.id === call.id)?.text ?? null,
      })),
    system: conversation ? conversation.entries.filter((entry) => entry.kind === "system").map((entry) => entry.text).join("\n") : "",
    context: conversation ? conversation.entries.map((entry) => entry.text ?? JSON.stringify(entry.args ?? "")).join("\n") : "",
    reply: decision?.reply ?? null,
    body,
  }
}

export const serve = (port, logPath) => {
  let count = 0

  return createServer((request, response) => {
    let raw = ""

    request.setEncoding("utf8")
    request.on("data", (part) => {
      raw += part
    })
    request.on("end", () => {
      const body = raw ? parseJson(raw) : null
      const format = formatOf(request.method, request.url)

      if (request.method === "GET" && String(request.url).split("?")[0].endsWith("/models")) {
        appendFileSync(logPath, JSON.stringify(record(++count, request, null, body, null)) + "\n")
        response.writeHead(200, { "content-type": "application/json" })
        response.end(JSON.stringify({ object: "list", data: [{ id: "sandbox-model", object: "model" }], models: [] }))
        return
      }

      if (!format) {
        appendFileSync(logPath, JSON.stringify(record(++count, request, null, body, null)) + "\n")
        response.writeHead(404, { "content-type": "application/json" })
        response.end(JSON.stringify({ error: { message: `no mock route for ${request.method} ${request.url}` } }))
        return
      }

      const answerFor = respond(format, body, request.headers)

      appendFileSync(logPath, JSON.stringify(record(++count, request, format, body, answerFor.decision)) + "\n")
      response.writeHead(answerFor.status, { "content-type": answerFor.type, "cache-control": "no-cache" })
      response.end(answerFor.text)
    })
  }).listen(port, "127.0.0.1")
}

const invokedDirectly = () => {
  try {
    return import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href
  } catch {
    return false
  }
}

if (invokedDirectly()) serve(Number(process.argv[2]), process.argv[3])
