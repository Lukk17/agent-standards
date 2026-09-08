---
name: jpa-patterns
description: "JPA and Hibernate patterns for Spring Boot: entity mapping, fetch strategy, N+1 prevention, projections, transaction boundaries, auditing, indexing, pagination, and HikariCP pooling. Use when you say \"design this entity\", \"why does this query run two hundred times\", \"add a JOIN FETCH\", \"size the Hikari pool\", or \"write a @DataJpaTest for this repository\". Not for the REST layer above the repository, use `springboot-patterns`."
license: Apache-2.0
---

# JPA and Hibernate Patterns

Data modeling, repositories, and query performance for the persistence layer of a Spring Boot service. Every rule
here assumes Java 21 LTS as the minimum with Java 25 LTS as the recommended target, Spring Boot 3.x, and the
Hibernate 6 that ships with it.

---

### When to activate

- Designing JPA entities and table mappings.
- Defining relationships and choosing a fetch strategy.
- Chasing N+1 queries, slow reads, or a query that loads far more than it needs.
- Setting transaction boundaries, auditing, or soft deletes on the data layer.
- Setting up pagination, sorting, or a custom repository method.
- Tuning HikariCP or deciding whether a second-level cache earns its keep.

---

### When not to activate

- Controllers, DTOs, validation, and the API contract above the service, use `springboot-patterns`.
- Java language style, naming, and immutability, use `java-coding-standards`.
- Writing the repository tests themselves, use `springboot-tdd`.
- Schema change and rollout mechanics, use `database-migrations`.
- PostgreSQL query planning and index internals, use `postgres-patterns`.

---

### Map entities explicitly

Declare column nullability, length, and uniqueness on the entity, and name every index you rely on. A mapping that
leans on Hibernate defaults produces a schema nobody predicted, and a review cannot tell an intended nullable
column from a forgotten one.

Pass: constraints and indexes are on the mapping, enums are stored as strings, audit fields come from the auditing
listener.

```java
@Entity
@Table(name = "markets", indexes = {
  @Index(name = "idx_markets_slug", columnList = "slug", unique = true)
})
@EntityListeners(AuditingEntityListener.class)
public class MarketEntity {
  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @Column(nullable = false, length = 200)
  private String name;

  @Column(nullable = false, unique = true, length = 120)
  private String slug;

  @Enumerated(EnumType.STRING)
  private MarketStatus status = MarketStatus.ACTIVE;

  @CreatedDate private Instant createdAt;
  @LastModifiedDate private Instant updatedAt;
}
```

Fail: `@Enumerated(EnumType.ORDINAL)`, which renumbers itself the moment somebody inserts a constant in the middle
of the enum. Auditing itself needs one `@EnableJpaAuditing` on a configuration class.

---

### Keep associations lazy and fetch what you need per query

Every association defaults to lazy, and the query that needs the children asks for them. An eager collection loads
on every read path including the ones that never touch it, and the cost is invisible until production.

Pass: lazy mapping, then one `join fetch` in the query that actually needs the children.
```java
@OneToMany(mappedBy = "market", cascade = CascadeType.ALL, orphanRemoval = true)
private List<PositionEntity> positions = new ArrayList<>();
```

```java
@Query("select m from MarketEntity m left join fetch m.positions where m.id = :id")
Optional<MarketEntity> findWithPositions(@Param("id") Long id);
```

Fail: `fetch = FetchType.EAGER` on a collection, which turns one list endpoint into one query per row.

Treat a detected N+1 as a blocking defect rather than a follow-up. Turn on `hibernate.generate_statistics` in
integration tests to assert the query count, and watch the same paths in an APM tool in production, because SQL
logging alone will not survive real traffic volume.

---

### Project the columns a read path uses

A read that needs three columns should select three columns. Loading whole entities to build a summary drags every
mapped column and every eager association behind it.

Pass: an interface projection, returned as a page.
```java
public interface MarketSummary {
  Long getId();
  String getName();
  MarketStatus getStatus();
}
```

```java
Page<MarketSummary> findAllBy(Pageable pageable);
```

Fail: loading full entities and mapping them in memory just to render a name and a status.

A repository may return Spring Data's `Page`, but the public API must wrap it in a project DTO such as the
`PageResponse` in `springboot-patterns` rather than serializing `Page` itself.

---

### Javadoc

Default to none. A Javadoc block is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most Javadoc blocks have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@return` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param orderId the wholesale order identifier` is noise, delete it.
3. `@return` only when it is non-obvious.
4. `@throws` always, for every exception a caller can act on. Unchecked exceptions never appear in the signature, so
   this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```java
// GOOD: says the thing the signature cannot, in one line each
/**
 * Loads the order together with its lines in a single query.
 *
 * @return empty when the order exists but is soft-deleted
 */
@EntityGraph(attributePaths = "lines")
Optional<Order> findWithLinesById(OrderId id);

// BAD: restates the method name and the return type
/**
 * Finds an order with lines by id.
 *
 * @param id the id
 * @return an Optional of Order
 */
Optional<Order> findWithLinesById(OrderId id);
```

---

### Put one transaction around one unit of work

Annotate service methods, mark read paths `readOnly = true`, and keep a multi-step write inside a single
`@Transactional` boundary so the steps commit or roll back together. Two writes in two transactions leave the second
failure with a committed half.

Pass: one boundary, entity mutated inside it, no explicit save needed for a managed entity.

```java
@Transactional
public Market updateStatus(Long id, MarketStatus status) {
  MarketEntity entity = repo.findById(id)
      .orElseThrow(() -> new EntityNotFoundException("Market"));
  entity.setStatus(status);
  return Market.from(entity);
}
```

Fail: a write sequence with no shared boundary, and a remote call held open inside the transaction.

Choose propagation deliberately, and keep transactions short. A transaction that waits on an HTTP call holds a
pooled connection for the length of somebody else's outage.

---

### Page with a stable sort

Every paged query needs an explicit sort, otherwise the database is free to return rows in a different order per
page and a row can appear twice or never.

Pass: page request with a sort, and keyset pagination for deep scrolling.
```java
PageRequest page = PageRequest.of(pageNumber, pageSize, Sort.by("createdAt").descending());
Page<MarketEntity> markets = repo.findByStatus(MarketStatus.ACTIVE, page);
```

Fail: `PageRequest.of(page, size)` with no sort on a table that takes concurrent inserts.

For cursor-style paging, order by the key and carry the last value forward with `id > :lastId` rather than paying
for a growing offset.

---

### Index for the queries you actually run

Add an index for each common filter, including foreign keys, and use composite indexes whose column order matches
the query. Batch writes with `saveAll` and a configured `hibernate.jdbc.batch_size` instead of a loop of single
inserts.

Pass: a composite index on `(status, created_at)` behind a query that filters on status and orders by date.

Fail: an index per column, none of which the planner can use for the composite filter the endpoint runs.

---

### Cache only what you can invalidate

The first-level cache lives for one `EntityManager`, so never hold entities across transactions and mutate them
later. Add a second-level cache only for read-heavy, rarely-changing entities, and only once the eviction path is
written and tested.

Pass: a reference table cached with an explicit region and eviction on write.

Fail: caching a mutable aggregate with no invalidation, which serves stale data until the next deploy.

---

### Migrate schema through Flyway or Liquibase

Version every schema change as a migration and never let Hibernate auto DDL touch a real environment. Keep
migrations additive, and plan a column drop as a separate release after the code stops reading it.

Pass: `spring.jpa.hibernate.ddl-auto=validate`, with the schema owned by migrations.

Fail: `ddl-auto=update` in production, which silently rewrites the schema on a deploy.

---

### Test data access against the real engine

Use `@DataJpaTest` with Testcontainers so the test runs against the database the service actually uses. H2 accepts
SQL that PostgreSQL rejects, so a green H2 suite proves very little.

Pass: Testcontainers Postgres, with `logging.level.org.hibernate.SQL=DEBUG` and
`logging.level.org.hibernate.orm.jdbc.bind=TRACE` on so query counts and bound parameters are visible.

Fail: an in-memory H2 database standing in for PostgreSQL.

---

### Reference material

| Open this | For |
| --- | --- |
| [references/connection-pooling.md](references/connection-pooling.md) | HikariCP settings, pool sizing formula, and pool monitoring alerts. |

---

### Related skills

| Skill | What it owns |
| --- | --- |
| `springboot-patterns` | Controllers, DTOs, service layering, and the API contract. |
| `java-coding-standards` | Java naming, immutability, and exception style. |
| `springboot-tdd` | The shape of the repository and integration tests. |
| `database-migrations` | Migration authoring, rollback, and zero-downtime schema change. |
| `postgres-patterns` | PostgreSQL-specific indexing and query planning. |
| `observability-and-logging` | Metrics and tracing for the queries this layer issues. |

---

### Checklist

- [ ] Every column declares nullability and length, and enums are stored as strings.
- [ ] No association is eager, and every read path that needs children fetches them explicitly.
- [ ] Read paths project the columns they use rather than loading whole entities.
- [ ] Every multi-step write shares one transaction, and read paths are `readOnly = true`.
- [ ] Every paged query has an explicit sort.
- [ ] Indexes match the filters and the sort order the endpoints actually use.
- [ ] The schema is owned by migrations, and auto DDL is set to validate.
- [ ] Repository tests run against the production database engine through Testcontainers.
