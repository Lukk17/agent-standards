---
name: ascend-memory
description: Long-term semantic memory for the user via the self-hosted AscendMemory service. Use this whenever the agent needs to remember something across conversations, recall a prior fact about the user, store a preference or note "for later", or pull back relevant context before answering. Trigger on phrases like "remember that…", "what did I tell you about…", "save this", "forget this", or any time persistent recall would obviously help.
---

# Ascend Memory

Per-user semantic memory. Embeddings live in Qdrant; the service exposes a small REST API. Every call is scoped by `user_id` — there is no global namespace, so always pass the current user's id.

## Base URL

Use whatever base URL the runtime gives you for AscendMemory; it differs between host, container, and remote setups. Examples below use `$BASE`. Ask the user if it isn't configured.

## Endpoints

All paths are under `/api/v1/memory`.

- `POST /insert` — store a memory. Body: `{user_id, text, metadata?, messages?, provider?}`. Use `text` for plain notes; use `messages` (a list of `{role, content}`) when you want mem0 to *infer* memories from a chat snippet rather than store the literal text.
- `GET  /search?user_id=…&query=…&limit=5` — semantic search. Returns a list of memory objects with `memory`, `score`, `metadata`, `created_at`. Use this *before* answering when prior context would help.
- `DELETE /?memory_id=…` — remove a single memory by id (the id comes from a search/insert response).
- `POST /wipe?user_id=…` — wipe everything for a user. Destructive — only do this when the user explicitly asks to forget everything.

`provider` is optional everywhere; omit it unless the user has multiple embedding providers configured and asks to target one specifically. The service falls back to `MEM0_DEFAULT_PROVIDER`.

## When to read vs write

- **Search before answering** when the question references the user's own life, preferences, prior decisions, or anything they may have told you before. A short query (3–7 words capturing the topic) is usually enough; let the embedder do the work.
- **Insert** when the user tells you something worth keeping (preferences, names, ongoing projects, deadlines, decisions and the reasoning behind them) — not transient task state. If unsure, prefer inserting; small redundant memories are cheap, missed memories are not.
- **Delete** specific entries when the user corrects something ("actually it's X, not Y") — find the stale one via search, then delete by id.

## Metadata

Pass small structured tags in `metadata` when they help future retrieval — e.g. `{"type":"preference","topic":"coffee"}` or `{"source":"chat-2026-05-08"}`. Keep it short; metadata isn't searched semantically, it's a filter aid.

## Examples

Insert a fact — Bash:

```bash
curl -s -X POST $BASE/api/v1/memory/insert \
  -H "Content-Type: application/json" \
  -d '{"user_id":"luksarna","text":"Prefers terse responses with no trailing summaries.","metadata":{"type":"preference"}}'
```

Insert a fact — PowerShell:

```powershell
curl.exe -s -X POST $BASE/api/v1/memory/insert `
  -H "Content-Type: application/json" `
  -d '{\"user_id\":\"luksarna\",\"text\":\"Prefers terse responses with no trailing summaries.\",\"metadata\":{\"type\":\"preference\"}}'
```

Search before answering — Bash:

```bash
curl -s "$BASE/api/v1/memory/search?user_id=luksarna&query=coffee%20preference&limit=5"
```

Search before answering — PowerShell:

```powershell
curl.exe -s "$BASE/api/v1/memory/search?user_id=luksarna&query=coffee%20preference&limit=5"
```

Delete a stale memory — Bash:

```bash
curl -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```

Delete a stale memory — PowerShell:

```powershell
curl.exe -s -X DELETE "$BASE/api/v1/memory?memory_id=<id-from-search>"
```

Note for PowerShell: line continuation is the backtick `` ` ``, not `\`. Use `curl.exe` so PowerShell doesn't route to its `Invoke-WebRequest` alias, and escape inner double quotes in JSON bodies.

## Privacy

Memories are user-scoped — never read or write across `user_id` boundaries unless the user explicitly asks. Treat the contents as personal: don't echo memory back to the user wholesale unless it's relevant to their current question.
