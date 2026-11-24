---
name: ascend-memory
description: 'Per-user long-term memory through the self-hosted AscendMemory service: insert, search, delete, wipe. Use when the user says "remember that…" or "what did I tell you about…". Not for web research, use `research`.'
compatibility: Requires the self-hosted AscendMemory service reachable over HTTP. Its base URL is configured by the user and appears in the examples as the placeholder $BASE, for example `http://ascend-memory.local:8080`. No default base URL is assumed.
metadata:
  version: "1.1.0"
---

# Ascend Memory

Store and retrieve per-user semantic memory through AscendMemory, which keeps embeddings in Qdrant and exposes a small REST API. Every call is scoped by `user_id` and there is no global namespace, so pass the current user's id on every request.

---

### When not to activate

- Running a web search or fetching a page for information you do not have, use `research`.
- Turning a recording into text before storing anything from it, use `audio-scribe` if it is installed, else ask the user for the text.
- Recording an architectural decision about a codebase rather than a fact about the user, use `architecture-decision-records`.

---

### Rules

1. Take the base URL from the runtime's configuration for AscendMemory, never from a guess, and use it as `$BASE` in every call. Ask the user when nothing is configured.
2. Use the four endpoints under `/api/v1/memory`: `POST /insert`, `GET /search`, `DELETE /?memory_id=…` and `POST /wipe`. `wipe` erases everything for one user, so call it only on an explicit request.
3. Search before answering whenever the question touches the user's own life, preferences, prior decisions, or anything they may have told you before. A short query of three to seven words carrying the topic is enough.
4. Insert when the user states something durable: preferences, names, ongoing projects, deadlines, decisions and the reasoning behind them. Leave transient task state out. When you are unsure, insert.
5. When the user corrects a stored fact, search for the stale memory, delete it by its id, then insert the corrected fact.
6. Keep `metadata` to short structured tags that sharpen future retrieval. It is a filter aid and is not searched semantically, so prose belongs in `text`.
7. Read and write only within the current user's `user_id` unless the user explicitly asks otherwise, and bring back only the memories that bear on the current question, rather than reciting the store.

---

### Reference files

| Open this | When |
| --- | --- |
| [api-endpoints.md](references/api-endpoints.md) | Choosing an endpoint or a body field, resolving the base URL, deciding when to search, insert or delete, metadata and the `user_id` boundary, each with Pass and Fail |
| [curl-commands.md](references/curl-commands.md) | The exact Bash or PowerShell command for an insert, a search or a delete |
| [checklist.md](references/checklist.md) | Before calling a memory read or write done |
