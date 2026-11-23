# Zod

The Zod 4 form of two core rules. Open it when the service validates with Zod. The reasoning behind each rule is in [core-rules.md](core-rules.md).

---

### Configuration schema

Parse the whole environment once at startup against a Zod schema and export the result as the only way to read configuration.

```typescript
// PASS: one schema, parsed once, exported as the only way to read configuration
const schema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
  PORT: z.coerce.number().default(3000),
})
export const config = schema.parse(process.env)
```

Fail: `const port = Number(process.env.PORT) || 3000` repeated in four files, with no check that `JWT_SECRET` exists.

---

### Schema failure in the error handler

Inside `toProblemResponse` in [core-rules.md](core-rules.md#return-every-error-through-one-handler-as-problemjson), after the `ApiError` line and before the unhandled error lines, a `z.ZodError` becomes a 422 problem body with one entry per failed field.

```typescript
  if (error instanceof z.ZodError) {
    const errors = error.issues.map((i) => ({ field: i.path.join('.'), message: i.message, code: i.code }))
    return problem(422, 'Validation Failed', `${errors.length} field(s) failed validation`, path, { errors })
  }
```
