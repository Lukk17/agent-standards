### AI SQL and Database Migrations Standards

---

### Core Execution Directives

- Treat all LLM generated SQL schemas, migration scripts, and indexing strategies as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every database modification task.
- Append a Zero-Trust directive demanding mandatory web searches for current Flyway or Liquibase documentation and SQL dialect syntax.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every SQL data type, configuration parameter, and CLI command provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

### Schema Design and Integrity

- Design database changes to be strictly backwards compatible with the current application code version to enable zero-downtime deployments. [Confidence: 100%]
- Never generate destructive SQL commands such as DROP TABLE or DROP COLUMN in standard migration scripts unless explicitly authorized and paired with a data migration strategy. [Confidence: 100%]
- Require explicit naming conventions for all constraints like foreign keys and primary keys. Do not let the database engine auto-generate constraint names, as this breaks cross-environment migrations. [Confidence: 100%]
- Enforce parameterized queries or ORM equivalents in the application layer interacting with these schemas to prevent SQL injection. [Confidence: 100%]

---

### Flyway Automation Architecture

- Prefix all Flyway migration script files strictly using the Versioned format like V1__Description.sql or Repeatable format like R__Description.sql. [Confidence: 100%]
- Link: https://www.red-gate.com/products/flyway/community/
- Quote: continual
- Do not modify a Flyway versioned migration script after it has been executed and committed. Flyway calculates checksums, and modifying an applied script will cause subsequent pipeline runs to fail. [Confidence: 100%]
- Use Flyway repeatable migrations for views, stored procedures, and functions to keep version history clean. [Confidence: 100%]

---

### Liquibase Automation Architecture

- Group Liquibase changelogs using a root file like changelog-root.yaml that includes nested changelogs organized by release or object type to ensure scalability. [Confidence: 100%]
- Link: https://docs.liquibase.com/community/implementation-guide-5-0
- Quote: to
- Use Liquibase contexts and labels to control which changesets are deployed to specific environments like test versus production. [Confidence: 100%]
- Require every changeset to have a defined rollback block. For SQL-based changelogs, explicitly write the compensating SQL command. [Confidence: 100%]
- Store database credentials securely and pass them to Liquibase using environment variables at runtime instead of hardcoding them in properties files. [Confidence: 100%]
- Link: https://docs.liquibase.com/concepts/liquibase-security.html
- Quote: email,

---

### CI/CD Migration Execution

- Execute database migrations strictly within the automated CI/CD pipeline. Do not allow manual execution of migration scripts against production databases. [Confidence: 100%]
- Separate migration execution from application startup in production environments. Run migrations as a pre-deployment pipeline step using the CLI tool or Docker image. [Confidence: 100%]
- Implement dry-run capabilities to output the exact SQL that will run against production for DBA review before applying changes. [Confidence: 100%]

---

### Indexing Strategy

- Create indexes on all foreign key columns; the database engine does not do this automatically (PostgreSQL, MySQL). [Confidence: 100%]
- Create composite indexes for columns that are consistently queried together; order columns from highest to lowest cardinality.
- Run `EXPLAIN ANALYZE` (PostgreSQL) or `EXPLAIN` (MySQL) on every new query that touches more than 10,000 rows before merging; include the output in the PR description.
- Remove unused indexes — they slow down writes without benefiting reads; audit with `pg_stat_user_indexes` (`idx_scan = 0`).

---

### Query Optimisation

- Never return unbounded result sets; all list queries must include a `LIMIT` (or ORM pagination equivalent). [Confidence: 100%]
- Detect N+1 query patterns using query logging or APM tools (Hibernate statistics, Django Debug Toolbar, Datadog); treat N+1s as blocking defects.
- Set a query timeout at the connection/session level to prevent runaway queries from consuming all database connections. Recommended: 30 seconds for API requests, 5 minutes for batch jobs.

---

### Connection Pooling

- Use a connection pool for all production database connections; never open a raw connection per request. [Confidence: 100%]
  - Java/Spring: **HikariCP** (default in Spring Boot) — configure `maximumPoolSize`, `minimumIdle`, `connectionTimeout`.
  - Python/SQLAlchemy: configure `pool_size`, `max_overflow`, `pool_timeout`.
  - External (any language): **PgBouncer** in transaction mode for high-concurrency PostgreSQL workloads.
- Formula for `maximumPoolSize`: `(number_of_cores * 2) + effective_spindle_count`; validate with load testing.
- Monitor pool exhaustion: alert when the pool is > 80% utilised for more than 30 seconds.

---

### NoSQL Standards

When using document databases (MongoDB, DynamoDB, Firestore):

- Design schemas for the query patterns, not the data shape (embed vs reference based on read access patterns).
- Define TTL indexes for data with a natural expiry (sessions, rate-limit counters, temporary tokens). [Confidence: 100%]
- Choose consistency level deliberately: use strong consistency for financial and inventory data; eventual consistency only for non-critical reads.
- For DynamoDB: define access patterns before designing the table; use a single-table design with composite keys where appropriate.

---

### Backup and Restore

- Automate daily full backups and hourly incremental/WAL-level backups for all production databases. [Confidence: 100%]
- Define RTO (Recovery Time Objective) and RPO (Recovery Point Objective) targets per service; validate them in quarterly restore drills.
- Store backups in a separate cloud account or region from the primary database to survive account-level incidents.
- Encrypt all backup files at rest using AES-256; verify decryption as part of the restore drill.

---

### Data Retention

- Define a data retention period for every table or collection that stores time-bounded data (logs, events, sessions, audit records).
- Implement automated archival or deletion jobs that run on a schedule; document the retention periods in `docs/DATA_RETENTION.md`.
- For GDPR compliance, ensure personal data can be deleted within 30 days of a deletion request without leaving ghost records in backups or logs.

---

### Read Replicas

- Route read-only queries (reports, search, analytics) to a read replica to reduce load on the primary.
- Always write to and read immediately after write from the primary to avoid stale-read bugs (propagation lag).
- Document which services read from replicas; clearly label replica data sources in the codebase.

---

### Database Monitoring

- Enable `pg_stat_statements` (PostgreSQL) or `performance_schema` (MySQL) to capture slow query statistics.
- Alert on: average query duration > 500ms, connection pool > 80% utilised, replication lag > 30 seconds, disk usage > 80%.
- Set up automated `VACUUM ANALYZE` (PostgreSQL) on a regular schedule to prevent table bloat from impacting performance.