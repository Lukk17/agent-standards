---
name: python-testing
description: pytest practice for Python projects, covering the red-green-refactor loop, test structure and naming, fixtures, mocking boundaries, parametrization, async tests, and the coverage gate. Use when writing tests for new Python code, fixing a flaky pytest suite, mocking an external API, converting copy-pasted tests into a parametrized table, or raising coverage on a module. Not for production Python idioms and typing, use `python-patterns`.
---

# Python Testing Patterns

How a Python test suite is written and kept honest: the order tests are written in, what a single test may assert,
what may be mocked, and what the coverage gate means. Fixture, mocking, configuration, and integration depth lives in
the reference files listed near the bottom.

Baseline: Python 3.13 or newer, with 3.14 the current release, and the current stable pytest.

---

### When to activate

- Writing tests for new or changed Python code.
- Adding coverage to a module that has none.
- Diagnosing a flaky, slow, or order-dependent pytest suite.
- Deciding what to mock and what to exercise for real.
- Setting up pytest configuration, markers, or the coverage gate for a project.

---

### When not to activate

- Writing the production code the tests cover. Use `python-patterns`.
- Applying the language-neutral red-green-refactor discipline and the test pyramid. Use `tdd-workflow`.
- Driving a browser through a user journey. Use `e2e-testing`.
- Exercising a whole running stack as a capability sweep. Use `e2e-runbooks`.
- Building regression tests aimed at agent-introduced defects. Use `ai-regression-testing`.

---

### Write the failing test first

The failing run is the evidence that the test can fail. A test written after the code passes on the first run and
proves nothing, because nothing has ever shown it would catch the bug.

Pass, in this order:

```python
def test_apply_discount_reduces_total():
    assert Cart(items=[Item("book", 20.0)]).apply(Coupon(percent=10)) == 18.0
```

Fail:

```python
def test_apply_discount():
    assert True
```

Run the test and read the failure before writing the implementation. A test that errors on an import or a typo has
not been seen to fail for the right reason.

---

### Give each test one behaviour and three phases

Every test sets up state, performs one action, then asserts the observable outcome. Which words label the three
phases is the project's choice, not this skill's: `Given`/`When`/`Then` and `Arrange`/`Act`/`Assert` are the two
common spellings, and a project may have its own. Read how the project's existing tests are already labelled and
match it. Only pick a convention when the project has none, and then stay consistent within it.

Pass:

```python
def test_apply_discount_reduces_total():
    cart = Cart(items=[Item("book", 20.0), Item("pen", 5.0)])
    coupon = Coupon(percent=10)

    total = cart.apply(coupon)

    assert total == 22.5
```

Fail:

```python
def test_cart():
    cart = Cart(items=[Item("book", 20.0)])
    assert cart.total == 20.0
    assert cart.apply(Coupon(percent=10)) == 18.0
    assert cart.remove("book").total == 0.0
```

The failing version reports one name for three behaviours, so the report never says which one broke.

---

### Name the test after the behaviour, not the function

The name is what a failing CI job shows. `test_login` says a thing was touched.
`test_login_with_expired_token_returns_401` says what stopped being true.

Pass:

```python
def test_withdraw_more_than_balance_raises_insufficient_funds(): ...
```

Fail:

```python
def test_withdraw_2(): ...
```

---

### Assert with plain `assert` and `pytest.raises`

pytest rewrites the assert statement and prints both sides on failure, so helper assertion methods buy nothing.
Expected exceptions go through `pytest.raises` with a `match`, which pins the message as well as the type.

Pass:

```python
with pytest.raises(ValueError, match="invalid email"):
    User(email="nope")
```

Fail:

```python
try:
    User(email="nope")
    assert False
except ValueError:
    pass
```

---

### Cover around 90 percent of the real logic

The target is around 90 percent line coverage of the real logic in the codebase, and 100 percent on critical paths
where it genuinely adds value. Do not add exclusion patterns to dodge meaningful tests: coverage measures real logic,
not padding. Excluding generated output such as protobuf stubs is legitimate, excluding a hand-written module because
it is awkward to test is not.

```bash
pytest --cov=mypackage --cov-report=term-missing
```

A coverage gate that fails is a signal to add the missing test, never a signal to lower the threshold.

---

### Mock only what you cannot run

Mock a third-party payment API or an email gateway, because you cannot run them. Do not mock the database when an
in-memory engine or a transactional session fixture will exercise the real query. Mocking the thing under test only
proves the mock was called.

Pass:

```python
@patch("mypackage.payment_gateway.charge")
def test_checkout_calls_gateway(charge_mock):
    charge_mock.return_value = {"status": "approved"}

    result = checkout(Order(total=42.0))

    assert result.paid is True
    charge_mock.assert_called_once_with(amount=42.0)
```

Fail:

```python
@patch("mypackage.Database.connect")
def test_user_query(connect_mock):
    connect_mock.return_value.query.return_value = [{"name": "Alice"}]
    assert get_users()[0]["name"] == "Alice"
```

Patch where the name is used, not where it is defined, and prefer `autospec=True` so a signature change breaks the
test instead of passing silently. The catalogue is in
[references/fixtures-and-mocking.md](references/fixtures-and-mocking.md).

---

### Parametrize instead of copying a test

One parametrized test reports one failure per case with the case in the name, so a broken input is identifiable
without reading the diff. Give the cases explicit `ids` when the values do not read well.

Pass:

```python
@pytest.mark.parametrize(
    ("email", "valid"),
    [("user@example.com", True), ("invalid", False), ("@no-local.com", False)],
    ids=["valid", "missing-at", "missing-local-part"],
)
def test_email_validation(email, valid):
    assert is_valid_email(email) is valid
```

Fail:

```python
def test_email_valid():
    assert is_valid_email("user@example.com") is True

def test_email_invalid():
    assert is_valid_email("invalid") is False
```

---

### Isolate every test

A test that depends on another test's leftovers passes alone and fails under `-p no:randomly`, in parallel, or in a
different order. Build state in a fixture, and let pytest's `tmp_path` own anything on disk.

Pass:

```python
def test_report_is_written(tmp_path):
    target = tmp_path / "report.csv"

    write_report(target, rows=[("a", 1)])

    assert target.read_text() == "a,1\n"
```

Fail:

```python
def test_report_is_written():
    write_report("report.csv", rows=[("a", 1)])
    assert open("report.csv").read() == "a,1\n"
```

`tmp_path` is a `pathlib.Path` and is cleaned up automatically. Prove isolation occasionally by running the suite
shuffled, and treat any order-dependent failure as a defect in the test, not in the runner.

---

### Test async code in auto mode

Set `asyncio_mode = "auto"` once in configuration and every `async def` test runs without a per-test marker. Async
callables are mocked with `AsyncMock` and asserted with `assert_awaited_once`, because a plain `Mock` returns a
coroutine nobody awaits.

Pass:

```python
async def test_fetch_user_returns_profile(async_client):
    response = await async_client.get("/users/1")

    assert response.status_code == 200
```

Fail:

```python
def test_fetch_user_returns_profile():
    assert asyncio.run(fetch_user("1")).status_code == 200
```

---

### Register markers and keep slow tests separable

An unregistered marker is a typo waiting to silently skip nothing. Register every marker in configuration, run with
`--strict-markers`, and keep the slow and integration sets addressable so the fast loop stays fast.

Pass:

```bash
pytest -m "not slow"
```

Fail:

```bash
pytest --disable-warnings
```

Silencing warnings hides the deprecation that will break the suite at the next upgrade. Fix the warning instead.

---

### Run the whole suite from the project root

`pytest` from the root is the command that decides whether a change is good. Scoping to one file is a debugging
convenience, never the evidence that a fix works, because the regression it caused is in the file you skipped.

Pass:

```bash
pytest
```

Fail:

```bash
pytest tests/test_users.py::test_create
```

---

### Reference files

| Open this | For |
| --- | --- |
| [references/fixtures-and-mocking.md](references/fixtures-and-mocking.md) | Fixture scopes, conftest, autouse, patching, autospec, async mocks |
| [references/pytest-config.md](references/pytest-config.md) | pyproject configuration, markers, CLI flags, coverage, CI |
| [references/integration-tests.md](references/integration-tests.md) | Suite layout, FastAPI clients, database sessions, test classes |

---

### Related skills

- `python-patterns` for the production code under test.
- `tdd-workflow` for the language-neutral red-green-refactor loop and the test pyramid.
- `e2e-testing` for browser journeys and the flaky-test policy.
- `ai-regression-testing` for tests aimed at agent-introduced regressions.
- `coding-standards` for the shared engineering floor, including the FIRST properties.

---

### Checklist

- Every new behaviour has a test that was seen to fail before the code was written.
- Each test asserts one behaviour and reads as setup, action, assertion.
- Test names state the behaviour and the expected outcome.
- Expected failures use `pytest.raises` with a `match`, never a bare `try`/`except`.
- Only genuinely external services are mocked, and every patch uses `autospec=True` where it can.
- Repeated tests that differ only by input are parametrized with readable `ids`.
- No test depends on another test, on the working directory, or on leftover files.
- Async tests run under `asyncio_mode = "auto"` and mock async callables with `AsyncMock`.
- All markers are registered and `--strict-markers` is on.
- Coverage of real logic is around 90 percent, with no exclusion added to dodge a test.
- `pytest` passes from the project root, not just the file that was edited.
