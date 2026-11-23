# FastAPI

Conventions for services built on FastAPI for HTTP. This is an optional layer on top of the language rules in the hub: open it only when the project actually uses FastAPI. Settings are in [pydantic-settings.md](pydantic-settings.md) and the database layer is in [sqlalchemy-and-alembic.md](sqlalchemy-and-alembic.md).

---

### Contents

- [Framework choice](#framework-choice)
- [Map domain errors to responses at the boundary](#map-domain-errors-to-responses-at-the-boundary)
- [Manage startup and shutdown with lifespan](#manage-startup-and-shutdown-with-lifespan)
- [Inject dependencies rather than importing globals](#inject-dependencies-rather-than-importing-globals)
- [Log through the logging module, never print](#log-through-the-logging-module-never-print)
- [Lay the service out by layer](#lay-the-service-out-by-layer)
- [Test an async FastAPI app through ASGITransport](#test-an-async-fastapi-app-through-asgitransport)
- [Override a dependency instead of patching it](#override-a-dependency-instead-of-patching-it)

---

### Framework choice

FastAPI is the default for a new HTTP service, and FastMCP is the default for a new MCP server. Flask and Django are
fully supported where a project already uses them: an existing Flask or Django service is not a defect and does not
need a migration to satisfy this skill. Apply the framework's own idioms in that case, and treat the rest of this
file as FastAPI-specific.

---

### Map domain errors to responses at the boundary

Business logic raises domain exceptions and knows nothing about HTTP. One exception handler per domain error turns it
into a response, so status codes live in exactly one layer. The body is `application/problem+json` in the RFC 9457
shape that `api-design` owns.

Pass:

```python
@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    problem = {
        "type": "https://example.com/errors/not-found",
        "title": "Not Found",
        "status": 404,
        "detail": str(exc),
        "instance": request.url.path,
    }
    return JSONResponse(status_code=404, content=problem, media_type="application/problem+json")

async def load_user(user_id: str) -> User:
    try:
        return await user_repo.get(user_id)
    except TimeoutError as exc:
        raise ServiceUnavailableError("user service timeout") from exc
```

Fail:

```python
async def load_user(user_id: str) -> JSONResponse:
    user = await user_repo.get(user_id)
    if user is None:
        return JSONResponse(status_code=404, content={"detail": "not found"})
    return JSONResponse(content=user.model_dump())
```

A `try`/`except` inside business logic is fine for an expected, recoverable failure. Returning a `JSONResponse` from
it is not, and neither is `except: pass`.

---

### Manage startup and shutdown with lifespan

`lifespan` is the supported hook. `@app.on_event` is deprecated and gives no ordering guarantee between startup and
the first request.

Pass:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan)
```

Fail:

```python
@app.on_event("startup")
async def startup() -> None:
    await db.connect()
```

The startup readiness banner is emitted from inside this same `lifespan`, after the dependency probes and before the
`yield`. The convention itself belongs to `observability-and-logging`.

---

### Inject dependencies rather than importing globals

FastAPI's `Depends` gives a request-scoped dependency that a test can override, which a module-level global cannot.

Pass:

```python
async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session

@router.get("/users/{user_id}")
async def read_user(user_id: str, session: Annotated[AsyncSession, Depends(get_session)]) -> UserOut:
    return await UserService(session).get(user_id)
```

A stateless client with no per-request state, such as an HTTP client or a mail gateway wrapper, may be constructed
once at module level under a descriptive name. Anything holding a connection or a transaction goes through `Depends`.

---

### Log through the logging module, never print

`print` writes to stdout with no level, no timestamp, and no way to filter it in production.

```python
logging.basicConfig(format="[MyService] %(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
```

Log discipline beyond this, meaning levels, correlation IDs, and what must never be logged, belongs to
`observability-and-logging`.

---

### Lay the service out by layer

```text
src/myapp/__init__.py
src/myapp/main.py
src/myapp/domain/
src/myapp/application/
src/myapp/infrastructure/
tests/
pyproject.toml
```

`main.py` is the sole entry point. Imports are absolute, so a module can be moved without rewriting its neighbours:
`from myapp.domain.user import User`.

---

### Test an async FastAPI app through ASGITransport

`httpx.AsyncClient` over `ASGITransport` runs the real application, middleware and dependency overrides included,
with no server to start and no port to collide.

```python
@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client

async def test_create_user_returns_201(client: AsyncClient):
    response = await client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

    assert response.status_code == 201
    assert response.json()["name"] == "Alice"

async def test_get_missing_user_returns_404(client: AsyncClient):
    assert (await client.get("/users/nonexistent")).status_code == 404
```

For a synchronous app, `fastapi.testclient.TestClient` wraps the same transport and needs no async fixture.

---

### Override a dependency instead of patching it

FastAPI's `dependency_overrides` swaps a dependency for the whole app, which is cleaner than patching a module path
and is undone by clearing the mapping.

```python
@pytest.fixture
def client_with_fake_clock() -> Iterator[TestClient]:
    app.dependency_overrides[get_clock] = lambda: FrozenClock("2026-01-01T00:00:00Z")
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
```
