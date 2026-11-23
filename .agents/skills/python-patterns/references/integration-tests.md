# Suite Layout and Integration Tests

Where test files live, and how to exercise an HTTP app or a database for real rather than through a mock. Open this
when adding the first integration test to a project or when a hub rule points here. Testing a FastAPI app through its real
transport is in [fastapi.md](fastapi.md), and the session fixture that rolls the database back is in
[sqlalchemy-and-alembic.md](sqlalchemy-and-alembic.md).

---

### Contents

- [Lay the suite out by kind](#lay-the-suite-out-by-kind)
- [Group with a class only when the tests share setup](#group-with-a-class-only-when-the-tests-share-setup)
- [Run the real engine, not SQLite standing in for Postgres](#run-the-real-engine-not-sqlite-standing-in-for-postgres)
- [Assert on behaviour, not on the response shape you happen to get](#assert-on-behaviour-not-on-the-response-shape-you-happen-to-get)

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

Mark each module with a module-level `pytestmark` rather than decorating the individual tests, so every test in the
file carries the marker.

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

### Run the real engine, not SQLite standing in for Postgres

SQLite will happily accept SQL that Postgres rejects, so a suite that passes on SQLite proves nothing about
production. Start the real engine once per session with a container.

```python
@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:18") as container:
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
