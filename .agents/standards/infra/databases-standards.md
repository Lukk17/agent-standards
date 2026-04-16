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