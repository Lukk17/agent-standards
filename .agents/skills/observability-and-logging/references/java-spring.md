# Logging and Health in Java and Spring Boot

Contents:

- [Log through one abstraction](#log-through-one-abstraction)
- [Use levels that mean something](#use-levels-that-mean-something)
- [Never log a secret](#never-log-a-secret)
- [Keep logging out of control flow](#keep-logging-out-of-control-flow)
- [Health checks under Spring Boot Actuator](#health-checks-under-spring-boot-actuator)
- [Emit one startup readiness block](#emit-one-startup-readiness-block)

The Java form of the logging and health rules: the SLF4J call for each rule, the Spring Boot Actuator health paths, and the startup readiness block built and emitted once. Open this when the service is written in Java. The reasoning behind each rule is in [rules-and-examples.md](rules-and-examples.md).

---

### Log through one abstraction

Pass:

```java
private static final Logger log = LoggerFactory.getLogger(OrderService.class);
```

Fail:

```java
private static final org.apache.logging.log4j.core.Logger log = new Log4jContextFactory().getContext().getLogger("x");
```

---

### Use levels that mean something

Pass:

```java
log.atWarn().setMessage("payment declined, retrying").addKeyValue("orderId", orderId).addKeyValue("attempt", attempt).log();
```

Fail, the wrong level and nothing to filter on:

```java
log.error("payment declined");
```

---

### Never log a secret

Pass:

```java
log.atInfo().setMessage("token issued").addKeyValue("subject", subject).addKeyValue("tokenSuffix", "***" + tokenSuffix).log();
```

Fail:

```java
log.info("token issued: {}", accessToken);
```

---

### Keep logging out of control flow

Pass:

```java
if (log.isDebugEnabled()) {
    log.atDebug().setMessage("cart snapshot").addKeyValue("snapshot", renderExpensiveSnapshot(cart)).log();
}
```

Fail:

```java
log.debug("cart snapshot=" + renderExpensiveSnapshot(cart));
```

---

### Health checks under Spring Boot Actuator

Spring Boot Actuator serves the liveness and readiness checks under its own paths rather than the generic `/health` and `/ready`.

Pass:

```text
GET /actuator/health/liveness    200 while the process runs, touches no dependency
GET /actuator/health/readiness   200 once startup finished and this instance's own pools are open, 503 otherwise
```

Fail:

```text
GET /api/v1/health/full   one versioned endpoint that checks every shared dependency and answers both probes
```

---

### Emit one startup readiness block

Emit the block from a listener for `ApplicationReadyEvent`, per `springboot-patterns`, in one call. The placeholder substitutes the entire string.

Pass:

```java
log.info("\n{}", buildStartupLog());
```

Fail:

```java
buildStartupLog().lines().forEach(log::info);
```

The builder must return one multi-line String. Building the block through repeated `log.info(line)` calls is the same bug from a different angle, as [startup-readiness-log.md](startup-readiness-log.md) explains.

Wrong (Java, per-line emission):

```java
log.info("----------------------------------------------------------");
log.info("    Application '{}' is running!", appName);
log.info("");
log.info("    Access URLs:");
log.info("      Local:     {}", localUrl);
log.info("      Hostname:  {}", hostnameUrl);
// ...one log call per line, each gets its own timestamp + level + logger prefix,
// and a Coordinator / scheduler / pool thread can log between any two of these.
```

Right (Java, build then emit once):

```java
String block = String.join("\n",
    "----------------------------------------------------------",
    "    Application '" + appName + "' is running!",
    "",
    "    Access URLs:",
    "      Local:     " + localUrl,
    "      Hostname:  " + hostnameUrl,
    // ... rest of sections
    "----------------------------------------------------------"
);
log.info("\n{}", block);
// One prefix line, the rest of the block flows under it at column 0. Atomic;
// nothing can interleave between sections.
```
