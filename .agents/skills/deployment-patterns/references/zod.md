# Environment validation with Zod

The TypeScript form of the rule that the process validates its whole environment against a schema before it serves. The rule and its reasoning are in [rules-and-examples.md](rules-and-examples.md#configuration-from-the-environment-validated-at-startup).

---

### Pass and Fail

Pass:

```typescript
const envSchema = z.object({
  NODE_ENV: z.enum(["development", "staging", "production"]),
  PORT: z.coerce.number().default(3000),
  DATABASE_URL: z.url(),
  JWT_SECRET: z.string().min(32),
});

export const env = envSchema.parse(process.env);
```

Fail:

```typescript
const port = Number(process.env.PORT) || 3000;
const dbUrl = process.env.DATABASE_URL!;
```
