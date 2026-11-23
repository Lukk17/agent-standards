# SQLAlchemy and Alembic

The database layer of a service: the async engine and session, schema changes through migrations, and the session fixture that lets a test run against the real database. Open this when a change touches a query, a schema or a database test.

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
