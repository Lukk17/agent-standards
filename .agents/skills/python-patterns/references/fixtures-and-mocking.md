# Fixtures, Parametrization, and Mocking

The full pytest catalogue behind the hub rules: fixture forms and scopes, shared fixtures in `conftest.py`,
parametrization variants, and every patching technique worth using. Open this when a hub rule points here.

---

### Basic fixture

A fixture is a named factory that pytest injects by parameter name. Anything more than a literal belongs in one.

```python
@pytest.fixture
def sample_user() -> User:
    return User(id="1", name="Alice", email="alice@example.com")

def test_user_display_name(sample_user):
    assert sample_user.display_name == "Alice"
```

---

### Setup and teardown with yield

Everything after the `yield` runs once the test finishes, on the passing and the failing path alike.

```python
@pytest.fixture
def database() -> Iterator[Database]:
    db = Database(":memory:")
    db.create_tables()
    yield db
    db.close()
```

Put teardown that must survive a fixture error in `request.addfinalizer` or in the object's own context manager
instead, because code after a `yield` that never happened does not run.

---

### Fixture scopes

Scope trades isolation for speed. Widen it only for something genuinely expensive and genuinely read-only.

| Scope | Runs | Use for |
| --- | --- | --- |
| `function` (default) | Once per test | Anything with mutable state |
| `class` | Once per test class | A shared client the class only reads |
| `module` | Once per module | A schema-loaded database the module only reads |
| `session` | Once per run | A container, a compiled asset, a spun-up server |

```python
@pytest.fixture(scope="session")
def postgres_container() -> Iterator[Container]:
    container = start_postgres()
    yield container
    container.stop()
```

A session-scoped fixture that mutates is the most common cause of order-dependent failures. If a test writes to it,
either roll the write back inside the test or drop the scope back to `function`.

---

### Parametrized fixture

Parameters on the fixture run every test that requests it once per value, which is how one suite covers several
backends.

```python
@pytest.fixture(params=["sqlite", "postgres"])
def db(request) -> Iterator[Database]:
    with make_database(request.param) as database:
        yield database
```

---

### Autouse fixture

Autouse applies to every test in scope without being requested. Reserve it for resetting global state, because an
invisible dependency is hard to debug.

```python
@pytest.fixture(autouse=True)
def reset_config() -> Iterator[None]:
    Config.reset()
    yield
    Config.cleanup()
```

---

### Shared fixtures in conftest.py

`tests/conftest.py` is discovered automatically by every test below it, so a fixture defined there needs no import.
Fixtures can depend on other fixtures by name.

```python
@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app(testing=True)) as test_client:
        yield test_client

@pytest.fixture
def auth_headers(client) -> dict[str, str]:
    token = client.post("/api/login", json={"username": "test", "password": "test"}).json()["token"]
    return {"Authorization": f"Bearer {token}"}
```

Keep `conftest.py` to fixtures and hooks. Test functions there run once per directory and confuse everybody.

---

### Parametrization variants

The basic form takes the argument names and a list of tuples.

```python
@pytest.mark.parametrize(("a", "b", "expected"), [(2, 3, 5), (0, 0, 0), (-1, 1, 0)])
def test_add(a, b, expected):
    assert add(a, b) == expected
```

Add `ids` whenever the values do not read well in a failure report.

```python
@pytest.mark.parametrize(
    ("email", "valid"),
    [("user@example.com", True), ("invalid", False)],
    ids=["valid", "missing-at"],
)
def test_email_validation(email, valid):
    assert is_valid_email(email) is valid
```

Stacked decorators produce the cartesian product, which grows faster than people expect. Two lists of five cases is
twenty-five tests.

```python
@pytest.mark.parametrize("currency", ["EUR", "USD"])
@pytest.mark.parametrize("amount", [0, 1, 1_000_000])
def test_format_money(currency, amount):
    assert format_money(amount, currency).endswith(currency)
```

Mark a single case without splitting the table using `pytest.param`.

```python
@pytest.mark.parametrize(
    "value",
    [1, 2, pytest.param(3, marks=pytest.mark.xfail(reason="rounding bug, TICKET-412"))],
)
def test_double(value):
    assert double(value) == value * 2
```

---

### Patch a function where it is used

`patch` replaces the name in the module that looks it up, not the module that defines it. Patching the definition
leaves the already-imported reference untouched and the test passes against the real function.

Pass:

```python
@patch("mypackage.service.external_api_call")
def test_service_handles_success(api_mock):
    api_mock.return_value = {"status": "success"}

    assert run_service()["status"] == "success"
    api_mock.assert_called_once()
```

Fail:

```python
@patch("thirdparty.client.external_api_call")
def test_service_handles_success(api_mock): ...
```

---

### Raise from a mock with side_effect

`side_effect` takes an exception, a callable, or an iterable of successive return values.

```python
@patch("mypackage.service.api_call", autospec=True)
def test_retries_then_succeeds(api_mock):
    api_mock.side_effect = [ConnectionError("boom"), {"status": "ok"}]

    assert run_with_retry()["status"] == "ok"
    assert api_mock.call_count == 2
```

---

### Use autospec so signature drift breaks the test

A plain `Mock` accepts any call. `autospec=True` builds the mock from the real object, so a renamed parameter fails
the test instead of passing forever.

Pass:

```python
@patch("mypackage.repository.UserRepository", autospec=True)
def test_create_user(repo_cls):
    repo = repo_cls.return_value
    repo.save.return_value = User(id="1", name="Alice")

    assert UserService(repo).create_user(name="Alice").name == "Alice"
    repo.save.assert_called_once()
```

Fail:

```python
@patch("mypackage.repository.UserRepository")
def test_create_user(repo_cls):
    repo_cls.return_value.save.return_value = User(id="1", name="Alice")
```

---

### Mock a context manager and a property

A patched `open` needs `mock_open`, which wires up `__enter__` and `__exit__` for you.

```python
@patch("builtins.open", new_callable=mock_open, read_data="file content")
def test_reads_file(open_mock):
    assert read_file("test.txt") == "file content"
    open_mock.assert_called_once_with("test.txt")
```

A property is replaced on the type, not on the instance.

```python
@pytest.fixture
def mock_config() -> Mock:
    config = Mock()
    type(config).debug = PropertyMock(return_value=True)
    return config
```

---

### Mock async callables with AsyncMock

`patch` picks `AsyncMock` automatically for an async target, and `AsyncMock` is required when constructing one by
hand. Assert with the await-aware methods.

```python
@patch("mypackage.service.fetch_profile", new_callable=AsyncMock)
async def test_profile_is_cached(fetch_mock):
    fetch_mock.return_value = {"id": "1"}

    await load_profile("1")
    await load_profile("1")

    fetch_mock.assert_awaited_once_with("1")
```

---

### Async fixtures

An async fixture is declared like any other and awaited by pytest-asyncio once `asyncio_mode = "auto"` is set.

```python
@pytest.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
```

---

### Assert on calls, not on internals

`assert_called_once_with` pins the contract between the code and its dependency. Reaching into `mock.call_args[0][2]`
pins the argument order as well, which turns a harmless refactor into a red build.

Pass:

```python
charge_mock.assert_called_once_with(amount=42.0, currency="EUR")
```

Fail:

```python
assert charge_mock.call_args[0][0] == 42.0
```
