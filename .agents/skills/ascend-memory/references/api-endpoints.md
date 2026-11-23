# API Endpoints

Contents:

- [Take the base URL from configuration, never from a guess](#take-the-base-url-from-configuration-never-from-a-guess)
- [Use the four endpoints under /api/v1/memory](#use-the-four-endpoints-under-apiv1memory)
- [Search before answering, insert when something is worth keeping](#search-before-answering-insert-when-something-is-worth-keeping)
- [Delete the stale entry when the user corrects you](#delete-the-stale-entry-when-the-user-corrects-you)
- [Keep metadata small and structural](#keep-metadata-small-and-structural)
- [Never cross a user_id boundary](#never-cross-a-user_id-boundary)

Companion reference for the [ascend-memory](../SKILL.md) skill. Load it to choose an endpoint or a body field, and for the reasoning and the Pass and Fail case behind each rule. The commands themselves are in [curl-commands.md](curl-commands.md).

---

### Take the base URL from configuration, never from a guess

Read the base URL from whatever configuration surface the runtime provides for AscendMemory. It differs between a host install, a container on a Docker network, and a remote deployment. Ask the user when nothing is configured. The examples use `$BASE` as the placeholder. A configured value might look like `http://ascend-memory.local:8080`, shown here only as an example of the shape, with the real value always coming from the user's own configuration.

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

Send `text` for a plain note. Send `messages`, a list of `{role, content}`, when mem0 should infer memories from a chat snippet instead of storing the literal text. Leave `provider` out unless the user has several embedding providers configured and names one, because the service falls back to its own default provider.

Pass: `POST /insert` with `text` for a one-line preference the user just stated.

Fail: `POST /wipe` to clear one stale entry that a single delete would have fixed.

---

### Search before answering, insert when something is worth keeping

Search whenever the question touches the user's own life, preferences, prior decisions, or anything they may have told you before. A short query of three to seven words carrying the topic is enough, because the embedder does the matching. Insert when the user states something durable: preferences, names, ongoing projects, deadlines, decisions and the reasoning behind them. Leave transient task state out. When you are unsure, insert, because a small redundant memory costs little and a missed one costs the next conversation.

Pass: search `"coffee preference"` before recommending a roaster, then answer from what comes back.

Fail: store the current step of a task in progress, which is noise by tomorrow.

---

### Delete the stale entry when the user corrects you

When the user corrects a stored fact, search for the stale memory, take its id from the result, and delete that id. Leaving both versions in the store means the next search returns two contradictory hits with similar scores.

Pass: search, find the old entry, `DELETE` it by id, then insert the corrected fact.

Fail: insert the correction and leave the wrong memory in place.

---

### Keep metadata small and structural

Pass short structured tags in `metadata` when they sharpen future retrieval, for example `{"type":"preference","topic":"coffee"}` or `{"source":"chat-<date>"}`. Metadata is a filter aid and is not searched semantically, so prose belongs in `text` instead.

Pass: `{"type":"preference","topic":"coffee"}`.

Fail: `{"note":"the user said during a long conversation that they usually prefer a light roast in the morning"}`.

---

### Never cross a user_id boundary

Read and write only within the current user's `user_id` unless the user explicitly asks otherwise. Treat the contents as personal: bring back only the memories that bear on the current question, rather than reciting the store.

Pass: search the current user's id, quote the one memory that answers the question.

Fail: search a second user's id to compare, or dump every hit back into the reply.
