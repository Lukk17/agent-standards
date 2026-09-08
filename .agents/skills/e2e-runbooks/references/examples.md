# Worked spec examples

Three complete specs at increasing setup cost, matching the classes in [SKILL.md](../SKILL.md). Copy the closest one and
replace the endpoints, commands and assertions. Every one keeps the same seven sections in the same order.

---

### Example 1: pure curl, `1-hello-api-test.md`

Setup class 1: no state to reset, no fixtures, one endpoint.

````markdown
# Hello API: e2e test

## What this verifies

- The `/hello` endpoint returns HTTP 200 with the expected greeting.
- The endpoint echoes the `name` query parameter into the response.

## Prerequisites

Check the service is reachable. Expect HTTP 200 with `{"status":"UP"}`.

```bash
curl -fsS http://localhost:8080/actuator/health
```

## Reset state

None. This test does not write persisted state.

## Run

```bash
curl -sS -o /tmp/hello.json -w "%{http_code}" "http://localhost:8080/hello?name=canary"
```

## Expected

The body written to `/tmp/hello.json` contains `{"greeting":"Hello, canary!"}`.

The HTTP status code written by `-w` is `200`.

## Fixtures

None.

## Concurrency

- Mutates: none, read-only endpoint.
- Conflicts with: none.
- Serial: false
````

---

### Example 2: MCP tool round trip, `2-mcp-tool-test.md`

Setup class 2: still no state, but the assertion has to prove a tool actually fired rather than that the model answered
from memory. The negative assertion is what does that.

````markdown
# Weather MCP: e2e test

## What this verifies

- The agent discovers and invokes the weather MCP tool for a weather prompt.
- The response carries concrete weather data rather than a refusal.

## Prerequisites

Check the agent. Expect HTTP 200 with `{"status":"UP"}`.

```bash
curl -fsS http://localhost:9917/actuator/health
```

Check the MCP server. Expect HTTP 200 with `{"status":"UP"}`.

```bash
curl -fsS http://localhost:9998/actuator/health
```

## Reset state

None.

## Run

Send the weather prompt and wait for the response.

```bash
bru run "agent/testing/weather-mcp-prompt.yml" --env local
```

## Expected

The output shows HTTP 200.

The response body's `content` field contains a numeric temperature value.

The response body's `content` does NOT contain "I cannot access live data" or "I don't have real-time data", either of which would mean the tool was never invoked.

## Fixtures

None.

## Concurrency

- Mutates: none. The weather call is read-through and writes no persistent agent state.
- Conflicts with: none.
- Serial: false
````

---

### Example 3: fixture upload and retrieval, `5-rag-canary-test.md`

Setup class 5: multi-service reset, a canary fixture, and an async ingestion step to wait on. Note that the Reset
section drops exactly what the Concurrency section declares as mutated.

````markdown
# RAG canary: e2e test

## What this verifies

- An uploaded markdown file ingests into the vector store.
- A later prompt mentioning the canary phrase returns that file as a source.

## Prerequisites

Check object storage, the vector store, and the agent are up, one block each, each expecting HTTP 200.

## Reset state

Drop the canary user's vector points.

```bash
curl -X POST "http://localhost:6333/collections/documents/points/delete" -H "Content-Type: application/json" -d '{"filter":{"must":[{"key":"userId","match":{"value":"canary"}}]}}'
```

Drop the canary user's stored objects.

```bash
mc rm --recursive --force local/uploads/canary/
```

## Run

1. Upload the canary fixture.

```bash
bru run "agent/testing/rag-upload-canary.yml" --env local
```

2. Poll the agent's `/ingestion/status` until it reports `READY`.

3. Send a retrieval prompt mentioning the canary phrase.

```bash
bru run "agent/testing/rag-retrieve-canary.yml" --env local
```

## Expected

The upload response shows HTTP 200 with a non-empty `documentId`.

After ingestion, a vector-store scroll filtered by `userId=canary` returns at least 1 point.

The retrieval response body's `sources[]` array contains exactly 1 entry whose `key` ends in `markdown-canary.md`.

The retrieval response's `content` field references the canary phrase from the fixture.

## Fixtures

- `e2e/fixtures/markdown-canary.md`: single-line canary phrase with an invented village name and an invented festival date.

## Concurrency

- Mutates: vector collection `documents` (filter `userId=canary`), object bucket `local/uploads/canary/`, metadata rows where `user_id='canary'`.
- Conflicts with: any other test that ingests, retrieves, or wipes data for `userId=canary` across those stores.
- Serial: false, parallelisable against tests using a different `userId`.
````

---

### What to copy from which

| Situation | Start from |
| --- | --- |
| A read-only endpoint or health probe | Example 1 |
| Proving a tool, plugin, or integration actually fired | Example 2, especially its negative assertion |
| Anything that uploads, ingests, or writes across services | Example 3, especially its Reset and Concurrency pairing |
