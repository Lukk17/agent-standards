---
name: ascend-memory
description: Long-term semantic memory for one user through the self-hosted AscendMemory service, covering insert, semantic search, delete, and wipe against a per-user Qdrant namespace. Use when the user says "remember that…", "what did I tell you about…", "save this for later", "forget this", or when prior context about the user would change your answer. Not for fetching content from the live web, use `ascend-web-hunter`.
compatibility: Requires the self-hosted AscendMemory service reachable over HTTP. Its base URL is configured by the user and appears in the examples as the placeholder $BASE, for example `http://ascend-memory.local:8080`. No default base URL is assumed.
---

# Ascend Memory

Store and retrieve per-user semantic memory through AscendMemory, which keeps embeddings in Qdrant and exposes a
small REST API. Every call is scoped by `user_id` and there is no global namespace, so pass the current user's id on
every request.

---

### When to activate

- The user states a durable fact about themselves: a preference, a name, an ongoing project, a deadline.
- The user asks what they told you before, or the answer depends on a prior decision of theirs.
- The user asks you to save, remember, correct, or forget something.
- You are about to answer a question about the user's own life, work, or choices.

---

### When not to activate

- Fetching a page or running a web search for information you do not have, use `ascend-web-hunter`.
- Turning a recording into text before storing anything from it, use `audio-scribe`.
- Recording an architectural decision about a codebase rather than a fact about the user, use
  `architecture-decision-records`.

---

### Take the base URL from configuration, never from a guess

Read the base URL from whatever configuration surface the runtime provides for AscendMemory. It differs between a
host install, a container on a Docker network, and a remote deployment. Ask the user when nothing is configured.
Examples below use `$BASE` as the placeholder. A configured value might look like `http://ascend-memory.local:8080`,
shown here only as an example of the shape, with the real value always coming from the user's own configuration.

Pass: resolve the base URL from configuration, then use it as `$BASE` in every call.

Fail: assume a default host and port and send the user's memories to whatever answers.

---

### Use the four endpoints under /api/v1/memory

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/insert` | POST | Store a memory. Body: `{user_id, text, metadata?, messages?, provider?}`. |
| `/search?user_id=…&query=…&limit=5` | GET | Semantic search. Returns objects with `memory`, `score`, `metadata`, `created_at`. |
| `/?memory_id=…` | DELETE | Remove one memory by the id returned from a search or an insert. |
| `/wipe?user_id=…` | POST | Erase everything for one user. Destructive, so only on an explicit request. |

Send `text` for a plain note. Send `messages`, a list of `{role, content}`, when mem0 should infer memories from a
chat snippet instead of storing the literal text. Leave `provider` out unless the user has several embedding
providers configured and names one, because the service falls back to its own default provider.

Pass: `POST /insert` with `text` for a one-line preference the user just stated.

Fail: `POST /wipe` to clear one stale entry that a single delete would have fixed.

---

### Search before answering, insert when something is worth keeping

Search whenever the question touches the user's own life, preferences, prior decisions, or anything they may have
told you before. A short query of three to seven words carrying the topic is enough, because the embedder does the
matching. Insert when the user states something durable: preferences, names, ongoing projects, deadlines, decisions
and the reasoning behind them. Leave transient task state out. When you are unsure, insert, because a small
redundant memory costs little and a missed one costs the next conversation.

Pass: search `"coffee preference"` before recommending a roaster, then answer from what comes back.

Fail: store the current step of a task in progress, which is noise by tomorrow.

Insert, Bash:

```bash
curl -s -X POST $BASE/api/v1/memory/insert -H "Content-Type: application/json" -d '{"user_id":"<user-id>","text":"Prefers terse responses with no trailing summaries.","metadata":{"type":"preference"}}'
```

Insert, PowerShell:

```powershell
curl.exe -s -X POST $BASE/api/v1/memory/insert -H "Content-Type: application/json" -d '{\"user_id\":\"<user-id>\",\"text\":\"Prefers terse responses with no trailing summaries.\",\"metadata\":{\"type\":\"preference\"}}'
```

Search, Bash:

```bash
curl -s "$BASE/api/v1/memory/search?user_id=<user-id>&query=coffee%20preference&limit=5"
```

Search, PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/memory/search?user_id=<user-id>&query=coffee%20preference&limit=5"
```

Call `curl.exe` in PowerShell so the shell does not route the name to its `Invoke-WebRequest` alias, and escape the
inner double quotes of any JSON body.

---

### Delete the stale entry when the user corrects you

When the user corrects a stored fact, search for the stale memory, take its id from the result, and delete that id.
Leaving both versions in the store means the next search returns two contradictory hits with similar scores.

Pass: search, find the old entry, `DELETE` it by id, then insert the corrected fact.

Fail: insert the correction and leave the wrong memory in place.

Delete, Bash:

```bash
curl -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```

Delete, PowerShell:

```powershell
curl.exe -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```

---

### Keep metadata small and structural

Pass short structured tags in `metadata` when they sharpen future retrieval, for example
`{"type":"preference","topic":"coffee"}` or `{"source":"chat-2026-05-08"}`. Metadata is a filter aid and is not
searched semantically, so prose belongs in `text` instead.

Pass: `{"type":"preference","topic":"coffee"}`.

Fail: `{"note":"the user said during a long conversation that they usually prefer a light roast in the morning"}`.

---

### Never cross a user_id boundary

Read and write only within the current user's `user_id` unless the user explicitly asks otherwise. Treat the
contents as personal: bring back only the memories that bear on the current question, rather than reciting the store.

Pass: search the current user's id, quote the one memory that answers the question.

Fail: search a second user's id to compare, or dump every hit back into the reply.

---

### Related skills

- `ascend-web-hunter` for information that lives on the web rather than in the user's history.
- `audio-scribe` for turning a recording into text you might then store.
- `architecture-decision-records` for decisions about a codebase rather than facts about a person.

---

### Checklist

- Base URL resolved from configuration, not from a default.
- `user_id` present on every insert, search, and wipe.
- Search run before answering anything that depends on the user's history.
- Corrections applied as delete plus insert, not insert alone.
- `metadata` short and structural, with prose kept in `text`.
- `wipe` used only on an explicit request to forget everything.
