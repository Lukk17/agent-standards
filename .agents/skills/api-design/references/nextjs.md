# Endpoint example in Next.js

The create-user endpoint as a Next.js route handler in TypeScript, called by an authenticated administrator: a 400 problem body when the `Idempotency-Key` header is missing or the body is not JSON, schema validation, a 422 problem body on failure, and a 201 with a `Location` header on success. Read this when you want a concrete shape to copy rather than the rule behind it. The same endpoint in Django REST Framework is in [django-rest.md](django-rest.md), and in Go in [go.md](go.md).

---

### TypeScript, Next.js route handler

```typescript
import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";

const createUserSchema = z.object({
  email: z.email(),
  name: z.string().min(1).max(100),
});

export async function POST(req: NextRequest) {
  const idempotencyKey = req.headers.get("Idempotency-Key");
  if (!idempotencyKey) {
    return NextResponse.json({
      type: "https://example.com/errors/idempotency-key-missing",
      title: "Idempotency-Key Required",
      status: 400,
      detail: "Send an Idempotency-Key header so this request is safe to retry",
    }, { status: 400, headers: { "Content-Type": "application/problem+json" } });
  }

  const body: unknown = await req.json().catch(() => undefined);
  if (body === undefined) {
    return NextResponse.json({
      type: "https://example.com/errors/invalid-json",
      title: "Invalid Request Body",
      status: 400,
      detail: "The request body is not valid JSON",
    }, { status: 400, headers: { "Content-Type": "application/problem+json" } });
  }

  const parsed = createUserSchema.safeParse(body);

  if (!parsed.success) {
    return NextResponse.json({
      type: "https://example.com/errors/validation",
      title: "Validation Failed",
      status: 422,
      detail: "Request validation failed",
      errors: parsed.error.issues.map((i) => ({ detail: i.message, pointer: `#/${i.path.join("/")}` })),
    }, { status: 422, headers: { "Content-Type": "application/problem+json" } });
  }

  const user = await createUser(parsed.data, idempotencyKey);

  return NextResponse.json({ data: user }, { status: 201, headers: { Location: `/api/v1/users/${user.id}` } });
}
```
