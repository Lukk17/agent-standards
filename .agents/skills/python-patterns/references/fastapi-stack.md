# Optional Stack Reference: FastAPI and FastMCP

Conventions for services built on FastAPI for HTTP and FastMCP for MCP servers. This is an optional layer on top of
the language rules in the hub: open it only when the project actually uses that stack.

---

### Framework choice

FastAPI is the default for a new HTTP service, and FastMCP is the default for a new MCP server. Flask and Django are
fully supported where a project already uses them: an existing Flask or Django service is not a defect and does not
need a migration to satisfy this skill. Apply the framework's own idioms in that case, and treat the rest of this
file as FastAPI-specific.

---

### Map domain errors to responses at the boundary

Business logic raises domain exceptions and knows nothing about HTTP. One exception handler per domain error turns it
into a response, so status codes live in exactly one layer.

Pass:

```python
@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})

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

### Read configuration through pydantic-settings

Settings are typed, validated at startup, and sourced from the environment. A missing or malformed variable fails the
process immediately rather than at the first request that needs it.

```python
class Settings(BaseSettings):
    database_url: str
    secret_key: SecretStr
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
```

Wrap every credential in `SecretStr` so it cannot leak through a repr or a log line.

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

### Talk to the database through SQLAlchemy and Alembic

Use the async engine and session, express queries as Core expressions or ORM operations, and change schema only
through a migration.

```python
engine = create_async_engine(settings.database_url)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
```

Two rules have no exceptions. Every schema change is an Alembic revision, never a hand-applied statement against a
live database. Every query is built from expressions, never from an interpolated SQL string, which is how injection
gets in.

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
