# Spring and Lombok Rules

The form the Java rules take in a project that uses Spring or Lombok: injection and logging through Lombok, one `@ControllerAdvice`, typed configuration, tunables, the shared blank check and the virtual-thread switch. Open this when the code in front of you carries a Spring or a Lombok annotation, or when configuration values are being read ad hoc across the codebase. The rules that hold for any Java project are in [core-rules.md](core-rules.md).

---

### Contents

- [Rules](#rules)
- [Inject through the constructor, log through Lombok](#inject-through-the-constructor-log-through-lombok)
- [Handle domain exceptions in one ControllerAdvice](#handle-domain-exceptions-in-one-controlleradvice)
- [Configuration binding](#configuration-binding)
- [Which literals are tunables](#which-literals-are-tunables)
- [Use the shared blank check](#use-the-shared-blank-check)
- [Virtual threads in Spring Boot](#virtual-threads-in-spring-boot)

---

### Rules

1. Inject through the constructor with `@RequiredArgsConstructor` and take the logger from `@Slf4j`, never an `@Autowired` field. `@Builder` only for complex construction, `@Value` for value objects, `@Getter` or `@Setter` only where neither a record nor `@Value` fits.
2. One `@ControllerAdvice` turns domain and technical exceptions into responses, so business methods hold no try-catch.
3. No tunable literal in code. A cron, delay, duration, timeout, limit, bucket size, origin or business maximum binds from `application.yml` into a validated `@ConfigurationProperties` record, a cron through a `${...}` placeholder, because a value in code needs a release to change. Only algorithm and protocol constants stay, such as the AES-GCM 96-bit IV and 128-bit tag or a header name.
4. `StringUtils.hasText` from Spring, or one small shared helper where Spring is off the classpath, never a hand-rolled `s == null || s.isBlank()`, because the copies drift.

---

### Inject through the constructor, log through Lombok

Lombok removes boilerplate that carries no decisions. `@RequiredArgsConstructor` for injection, `@Slf4j` for the
logger, `@Builder` where construction is genuinely complex, `@Value` for immutable value objects, and `@Getter` or
`@Setter` only where neither a record nor `@Value` fits.

Pass: final fields, one generated constructor, no annotation on the field.

```java
@Service
@Slf4j
@RequiredArgsConstructor
public class MarketService {
  private final MarketRepository marketRepository;
}
```

Fail: field injection, which hides the dependency from every constructor call and from every test.

```java
@Autowired
private MarketRepository marketRepository;
```

Take the logger from `@Slf4j`.

Pass: `log.info("fetch_market slug={}", slug);` inside a class annotated `@Slf4j`.

Fail: a logger built by hand with `LoggerFactory.getLogger(MarketService.class)`.

---

### Handle domain exceptions in one ControllerAdvice

One `@ControllerAdvice` translates domain and technical exceptions into responses, so business methods stay free of try-catch blocks. How the exceptions themselves are named, thrown and wrapped is in [core-rules.md](core-rules.md).

---

### Configuration binding

Bind configuration into a typed, validated `@ConfigurationProperties` object. Reading `@Value` placeholders or
environment variables from scattered classes means a missing value surfaces as a null at the moment it is first
used, which can be hours after startup.

```java
@Validated
@ConfigurationProperties(prefix = "market")
public record MarketProperties(@NotBlank String baseUrl, @Positive int maxPageSize) {}
```

A record makes the properties immutable and gives constructor binding for free. The validation annotations turn a
misconfigured environment into a startup failure with a message naming the property, which is the cheapest possible
place to find it.

Keep one properties type per prefix, and inject the type rather than the individual values, so a component's
configuration surface is visible in its constructor.

---

### Which literals are tunables

A value someone might reasonably change per environment or per incident is a tunable, and a tunable never lives in Java, neither as a literal nor as a `static final` constant. That covers cron expressions, fixed delays, durations, time to live and timeouts, retry counts, cache and rate-limit bucket sizes, CORS origins and other allow-lists, interceptor order, and business maximums such as how many cost items or dashboard cards a request may carry. Changing one of them in code needs a build and a release, while changing it in `application.yml` needs a restart, and a profile file can vary it.

```yaml
app:
  jobs:
    audit-retention-cron: "0 15 3 * * *"
  rate-limit:
    public-write:
      capacity: 10
      refill-period: 1m
  expenses:
    max-cost-items: 5
```

```java
@Scheduled(cron = "${app.jobs.audit-retention-cron}")
void purgeExpiredAuditEntries() { ... }
```

Bind each group into a validated record (`@Positive`, `@NotEmpty`, `@DurationMin`), register it with `@EnableConfigurationProperties`, and add a binding test that loads the real `application.yml`, so a typo fails a test rather than a deployment. A module without Spring on its classpath, such as a pure domain module, takes the value through its constructor from the configuration class that builds it, and never reads the environment itself.

What stays a constant is a value the algorithm or the protocol fixes, where changing it is a bug rather than tuning: the AES-GCM 96-bit IV and 128-bit authentication tag (NIST SP 800-38D), a key length the cipher mandates, an HTTP header name, a problem type URI, a path prefix that is part of the public contract.

Pass: `@Scheduled(cron = "${app.jobs.audit-retention-cron}")`, and `private static final int GCM_TAG_LENGTH_BITS = 128;`.

Fail: `@Scheduled(cron = "0 15 3 * * *")`, `private static final int MAX_COST_ITEMS = 5;`, and a CORS origin list written into a `@Configuration` class.

---

### Use the shared blank check

A hand-written `value == null || value.isBlank()` repeated across a codebase drifts: one copy trims, one does not, one forgets the null. Use `org.springframework.util.StringUtils.hasText(value)` where Spring is on the classpath, and one small shared helper in a module where it is not, such as a pure domain module.

Pass: `if (!StringUtils.hasText(translation)) { ... }`

Fail: `if (translation == null || translation.trim().isEmpty()) { ... }` in a validator, and a slightly different copy in the next one.

---

### Virtual threads in Spring Boot

Spring Boot switches the web server and the task executors over with one property.

```yaml
spring:
  threads:
    virtual:
      enabled: true
```

When a virtual thread is the right choice, and where it still pins its carrier, is in [concurrency.md](concurrency.md).
