# Python Standards

Applies to all Python code. Universal rules in `universal-coding-standards.md` apply in addition to these.

---

## Project Structure

- All application source files live under a `src/` directory in the project root.
- Every package must contain an `__init__.py` file.
- Always use absolute imports starting from `src`: `from src.module import SomeClass`.
- `main.py` (at project root or `src/`) acts as the orchestrator and sole entry point.

---

## Type System

- Use Type Hints (PEP 484) for all function signatures and variable declarations.
- Use `Pydantic` (v2) models for data validation, serialization, and settings management.
  - Use `BaseModel` for request/response schemas.
  - Use `BaseSettings` (from `pydantic-settings`) for application configuration loaded from environment variables.
- Never use `Any` as a type hint; if truly dynamic, use `object` and document why.

---

## Frameworks

- Use **FastAPI** for HTTP web APIs.
- Use **FastMCP** for Model Context Protocol (MCP) server implementations.
- Do not use Flask or Django for new projects.

---

## Async

- Use `async`/`await` for all I/O-bound operations (HTTP calls, database queries, file I/O).
- Do not use blocking calls inside async functions; use async libraries or `run_in_executor` if a blocking call is unavoidable.

---

## Singletons and Services

- Prefer singleton service instances initialized once at module level using a descriptive name:
  ```python
  user_service = UserService()
  ```
- Do not use global mutable state for anything other than initialized singletons.

---

## Naming (PEP 8)

- Functions and variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Boolean variables must start with `is_`, `has_`, or `can_`.

---

## Error Handling

- Handle exceptions using FastAPI `exception_handler` decorators or centralized middleware.
- Do not scatter `try/except` blocks throughout business logic.
- Never swallow exceptions silently (bare `except: pass` is forbidden).

---

## Logging

Logging format must follow this pattern:

```
[ServiceName] %(asctime)s %(levelname)s %(message)s
```

Use Python's standard `logging` module configured at application startup. Do not use `print` for operational output.

---

## Code Style

- Avoid deep nesting; use guard clauses and early returns.
- Logic must be self-documenting; avoid comments that restate code.
- Maximum line length: 120 characters (project-level `pyproject.toml` or `.flake8` configuration).

---

## Testing

These rules extend `testing-standards.md`:

- Use **pytest** within a `venv` for all tests.
- Run all tests at once: `pytest` from the project root — never run single test files to validate.
- Check for an existing `venv` before creating one.
- Use `pytest-asyncio` for testing async functions.
- Use `httpx.AsyncClient` with FastAPI's `app` for API integration tests (no running server needed).
