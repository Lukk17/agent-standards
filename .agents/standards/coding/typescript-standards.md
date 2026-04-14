# TypeScript Standards

Applies to all TypeScript projects (Node.js backends, frontend frameworks, CLIs). Universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Compiler Configuration

Always use strict mode in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true
  }
}
```

Never disable `strict` or any of its constituent flags (`noImplicitAny`, `strictNullChecks`, etc.) on a per-file basis.

---

## Type System

- Never use `any`. If a type is unknown at the boundary (e.g., external API response), use `unknown` and narrow it explicitly.
- Prefer `interface` for object shapes that may be extended; use `type` for unions, intersections, and aliases.
- Use **Zod** for runtime validation at all system boundaries (API request bodies, environment variables, external API responses).
  - Derive TypeScript types from Zod schemas: `type MyDto = z.infer<typeof MyDtoSchema>`.
  - Never write a type and a Zod schema separately for the same shape.
- Use discriminated unions for modeling state variants; avoid optional fields as state indicators.

---

## Naming (TypeScript conventions)

- Files: `kebab-case.ts` (e.g., `user-service.ts`).
- Classes, interfaces, type aliases, enums: `PascalCase`.
- Functions, variables, object properties: `camelCase`.
- Constants: `UPPER_SNAKE_CASE` for module-level primitives.
- Boolean variables must start with `is`, `has`, or `can`.
- Enum members: `PascalCase`.

---

## Functions and Methods

- Prefer `function` declarations for top-level named functions; use arrow functions for callbacks and inline expressions.
- Always declare explicit return types for public functions and class methods.
- Use optional chaining (`?.`) and nullish coalescing (`??`) instead of manual null checks.
- Avoid deep nesting; use guard clauses and early returns.
- Public functions must be concise; extract complex logic into private helpers.

---

## Async

- Use `async`/`await` for all asynchronous code. Do not use `.then()/.catch()` chains in application code.
- Always handle promise rejections: either `await` with try/catch at the boundary, or attach a top-level error handler.
- Never use `Promise<any>`; type the resolved value explicitly.

---

## Modules

- Use ES module syntax (`import`/`export`); never use CommonJS `require()` in TypeScript source files.
- Use absolute path aliases (configured in `tsconfig.json` `paths`) for imports within the project; avoid long relative paths (`../../..`).
- Export only what is part of a module's public API; keep internal implementations unexported.

---

## Error Handling

- Use a centralized error-handling middleware (Express) or exception filter (NestJS) as the single error boundary.
- Create typed custom error classes extending `Error` for domain errors.
- Never swallow errors with empty catch blocks.
- Log errors with structured context (error message, stack, request ID where applicable).

---

## Environment Variables

- Use Zod (or `envalid`) to validate and parse all environment variables at application startup.
- Fail fast with a descriptive error if required environment variables are missing.
- Never access `process.env` directly in business logic; export a typed `env` config object.

---

## Testing

These rules extend `testing-standards.md`:

- Use **Vitest** as the test runner for all new projects (faster, ESM-native, compatible with Jest API).
- Use `@testing-library` for UI component tests (React, Vue, etc.).
- Use `msw` (Mock Service Worker) for mocking HTTP calls in tests — do not mock `fetch` or `axios` directly.
- Type all mocks explicitly; never use `jest.fn()` / `vi.fn()` without a typed signature.
- Test files must be co-located with source files using `.test.ts` or `.spec.ts` suffix, or placed in a `__tests__/` directory at the same level.
