# Suite Layout and Integration Tests

Where test files live, and how to exercise an HTTP app or a database for real rather than through a mock. Open this
when adding the first integration test to a project or when a hub rule points here.

---

### Lay the suite out by kind

Splitting by kind lets the fast set run on every save and the slow set run in CI, without a naming convention nobody
remembers.

```text
tests/conftest.py
tests/unit/test_models.py
tests/unit/test_services.py
tests/integration/test_api.py
tests/integration/test_repository.py
tests/e2e/test_checkout_journey.py
```

Mark the directories rather than the individual tests, so a new file inherits the marker.

```python
pytestmark = pytest.mark.integration
```

---

### Group with a class only when the tests share setup

A class earns its keep when several tests want the same fixture and the same name prefix. It is not a place to hold
state between tests: attributes set in one test are not visible to the next unless a fixture puts them there, and
relying on that ordering is the flake the hub rule warns about.

Pass:

```python
class TestCalculator:
    @pytest.fixture
    def calculator(self) -> Calculator:
        return Calculator()

    def test_add_returns_sum(self, calculator):
        assert calculator.add(2, 3) == 5

    def test_divide_by_zero_raises(self, calculator):
        with pytest.raises(ZeroDivisionError):
            calculator.divide(10, 0)
```

Fail:

```python
class TestCalculator:
    def test_add_stores_result(self):
        self.result = Calculator().add(2, 3)

    def test_result_is_five(self):
        assert self.result == 5
```

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

---

### Roll the database back instead of mocking it

A nested transaction rolled back after each test gives real SQL, real constraints, and real isolation, at a fraction
of the cost of recreating the schema.

```python
@pytest.fixture
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

def test_created_user_is_retrievable(db_session):
    db_session.add(User(name="Alice", email="alice@example.com"))
    db_session.flush()

    retrieved = db_session.query(User).filter_by(name="Alice").one()

    assert retrieved.email == "alice@example.com"
```

Use `flush` rather than `commit` inside the test so the outer transaction stays open and the rollback still works.

---

### Run the real engine, not SQLite standing in for Postgres

SQLite will happily accept SQL that Postgres rejects, so a suite that passes on SQLite proves nothing about
production. Start the real engine once per session with a container.

```python
@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17") as container:
        yield container.get_connection_url()
```

Pin the image to the major version production runs. A test suite that silently follows `latest` becomes a change
nobody reviewed.

---

### Assert on behaviour, not on the response shape you happen to get

An integration test that snapshots the entire JSON body fails on every additive field. Assert on the status and the
fields the contract actually promises.

Pass:

```python
assert response.status_code == 201
assert response.json()["email"] == "alice@example.com"
```

Fail:

```python
assert response.json() == {"id": 1, "name": "Alice", "email": "alice@example.com", "created_at": "2026-01-01"}
```
