# Writing Tests

Contents:

- [Behaviour-only assertions](#behaviour-only-assertions)
- [Number by setup cost](#number-by-setup-cost)
- [Canary fixtures](#canary-fixtures)
- [API client](#api-client)

Companion reference for the [e2e-runbooks](../SKILL.md) skill. Load it when writing an assertion, choosing the `{N}` prefix, building a canary fixture, or picking the API client for a project.

---

### Behaviour-only assertions

Assert what the user-facing API or the persisted state shows. Never assert on a log substring: logs drift across
versions and are not visible from every runner's shell. When a behaviour assertion fails, a log tail is the next
diagnostic step, not a pass criterion.

Fail: passes or fails on a string the service may rename tomorrow.

```text
The agent log contains "MCP tool invoked: getCurrentWeather".
```

Pass: asserts the observable consequence, which is only possible if the tool ran.

```text
The response body's `content` field contains a numeric temperature for the requested city.
The response body's `content` does NOT contain "I cannot access live data".
```

Persisted state counts as observable when it is queried directly.

```text
A `docker exec postgres psql ... -c "SELECT count(*) FROM chat_history WHERE user_id='canary'"` returns 2.
A Qdrant scroll on `documents` filtered by `userId=canary` returns exactly 3 points.
A `mc ls local/uploads/canary/` shows the uploaded file with non-zero size.
```

---

### Number by setup cost

The `{N}` prefix is chosen at proposal time from what the test needs. Lower numbers run first in a sweep, so a cheap
failure stops the expensive tests from wasting a stack.

| N | Setup cost class | Examples |
| --- | --- | --- |
| 1 | No state to reset, no fixtures, single endpoint or tool call | Health check, MCP weather lookup, refusal probe |
| 2 | Single fixture upload, vision model, or document parsing | Image description, inline PDF summarisation |
| 3 | Single-service reset | Cache hit and miss probe |
| 4 | Multi-service reset | Full upload, ingest, retrieve round trip |
| 5+ | Seeded state plus an async background process to observe | Compaction, projection rebuild, event replay |

Pick the lowest unused N that matches the class.

---

### Canary fixtures

A fixture used by an upload test must contain content unique enough that the model could not have memorised it, so a
passing test proves retrieval rather than recall.

Fail: the model can answer from training data, so the test passes with retrieval broken.

```text
fixtures/facts.md: "The capital of France is Paris."
```

Pass: an invented proper noun and a specific number nothing else contains.

```text
fixtures/markdown-canary.md: "The HELENA-DEDUP-CANARY village holds the 17th annual pierogi festival every August 14th."
```

The same principle in other formats: short PDFs with invented product names and specific prices, DOCX recipes with
distinctive rest times (47 minutes, not an hour), small images of an uncommon but recognisable subject, audio clips
under 60 seconds containing an invented word. Keep every fixture small enough to upload in under two seconds, put them
in `e2e/fixtures/`, and record each one's distinctive content in a table in `e2e/fixtures/README.md`.

---

### API client

The skill pins no client. Pick one per project and use it across every test.

| Client | When | Notes |
| --- | --- | --- |
| [Bruno CLI](https://www.usebruno.com/) | REST APIs, multi-step flows, mature collections | Single source of API truth, and the request file is the fixture |
| [Hurl](https://hurl.dev/) | Plain-text HTTP with assertions inside the request file | Lighter than Bruno, with assertions next to the request |
| [VS Code REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) | Human-only execution paths | `.http` files, no CLI runner |
| `curl` | Single-shot health checks and protocol probes | Use for prerequisite checks inside the spec |
| [httpie](https://httpie.io/) | Interactive debugging | Not a stored-test format |

For MCP tool tests, drive the request through the agent rather than the MCP server directly, so the assertion covers
discovery and routing rather than protocol mechanics alone.
