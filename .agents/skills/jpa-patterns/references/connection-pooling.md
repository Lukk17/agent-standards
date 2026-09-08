# HikariCP Connection Pooling

Sizing, configuring, and watching the connection pool that sits between a Spring Boot service and its database.
Open this when the service runs out of connections, when a deploy changes the instance size, or when you are
setting the pool up for the first time.

---

### Size the pool from cores, not from hope

A pool larger than the database can serve does not add throughput, it adds queueing inside the database. Start from
the formula and adjust only with a measurement.

```text
maximumPoolSize = (number_of_cores * 2) + effective_spindle_count
```

Use `effective_spindle_count = 1` for an SSD-backed database. A four-core application server against an SSD
database gives `(4 * 2) + 1 = 9`, which rounds up to 10.

Count cores on the database host rather than the application host when the two differ, because the pool exists to
avoid overwhelming the database.

---

### Baseline configuration

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      validation-timeout: 5000
```

Keep `max-lifetime` shorter than any idle-connection timeout enforced by the database or by a proxy in front of it,
otherwise the pool hands out a connection the far end has already closed.

Multiply the pool size by the number of running instances before comparing it against the database `max_connections`
limit. Ten instances at ten connections each is a hundred connections, and a database configured for a hundred has
nothing left for a migration or an operator session.

---

### Watch utilisation, alert before exhaustion

Expose Hikari metrics through Micrometer.

```yaml
management:
  metrics:
    enable:
      hikaricp: true
```

Alert when `hikaricp.connections.active` divided by `hikaricp.connections.max` stays above 0.8 for more than thirty
seconds. Sustained high utilisation means the next traffic bump produces connection-timeout errors rather than slow
responses, so the alert has to fire before the pool is empty.

Watch `hikaricp.connections.pending` alongside it. A non-zero pending count means threads are already waiting, and
the cause is almost always a long transaction rather than a small pool. Fix the transaction first, and resize only
when the transactions are already short.
