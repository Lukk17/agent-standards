# Vitest and Next.js regression harness

The setup behind the examples in [SKILL.md](../SKILL.md). It runs Next.js App Router route handlers directly in Node,
with the project's sandbox mode forced on, so a full API regression suite needs no database, no HTTP server, and no
browser. On another stack, keep the assertions from the skill and swap this harness for the framework's own test client.

---

### Test runner configuration

Route handlers are server code, so the environment is `node` rather than a DOM. The path alias has to mirror the
application's own alias or the handler imports will not resolve.

```typescript
import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
    include: ["__tests__/**/*.test.ts"],
    setupFiles: ["__tests__/setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
})
```

---

### Sandbox setup file

The setup file runs before every test file and is the single place the sandbox flag is forced. Blanking the database
credentials is deliberate: if a handler ever falls through to the production path, it fails loudly instead of quietly
reaching a real datastore.

```typescript
process.env.SANDBOX_MODE = "true"
process.env.DATABASE_URL = ""
process.env.DATABASE_ANON_KEY = ""
```

Name the variables the way the project names them. The point is that the production path has nothing to connect to.

---

### Request helper

One helper builds every request, so a test reads as its scenario rather than as request plumbing. The sandbox user id
travels as a header, which is what lets one suite exercise several fixture users against the same handler.

```typescript
import { NextRequest } from "next/server"

type RequestOptions = {
  method?: string
  body?: Record<string, unknown>
  headers?: Record<string, string>
  sandboxUserId?: string
}

export function createTestRequest(url: string, options: RequestOptions = {}): NextRequest {
  const { method = "GET", body, headers = {}, sandboxUserId } = options
  const fullUrl = url.startsWith("http") ? url : `http://localhost:3000${url}`
  const requestHeaders: Record<string, string> = { ...headers }

  if (sandboxUserId) {
    requestHeaders["x-sandbox-user-id"] = sandboxUserId
  }

  const init: { method: string; headers: Record<string, string>; body?: string } = {
    method,
    headers: requestHeaders,
  }

  if (body) {
    init.body = JSON.stringify(body)
    requestHeaders["content-type"] = "application/json"
  }

  return new NextRequest(fullUrl, init)
}

export async function parseResponse(response: Response) {
  const json = await response.json()
  return { status: response.status, json }
}
```

---

### A test using the harness

Import the handler by name from its route file and call it directly. There is no server to start and no port to
allocate, which is why the whole suite stays under a second.

```typescript
import { describe, it, expect } from "vitest"
import { createTestRequest, parseResponse } from "../../helpers"
import { GET } from "@/app/api/user/messages/route"

describe("GET /api/user/messages", () => {
  it("includes partnerName for every conversation in sandbox mode", async () => {
    const req = createTestRequest("/api/user/messages", { sandboxUserId: "user-001" })
    const res = await GET(req)
    const { status, json } = await parseResponse(res)

    expect(status).toBe(200)
    for (const conversation of json.data) {
      expect(conversation).toHaveProperty("partnerName")
    }
  })
})
```

A loop over an empty array asserts nothing, so a fixture user with at least one conversation is part of the test's setup
rather than an optional extra.

---

### Equivalents on other stacks

| Stack | Harness |
| --- | --- |
| Django | `django.test.Client` with the sandbox flag in test settings |
| FastAPI | `TestClient(app)` with a dependency override for the datastore |
| Spring Boot | `MockMvc` under `@SpringBootTest`, with a test profile that activates the sandbox beans |
| Go | `httptest.NewRecorder()` against the handler function |
| Express | `supertest(app)` with the sandbox flag set in the test bootstrap |
