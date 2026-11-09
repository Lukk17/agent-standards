# Serialization, Configuration Binding, and Mapping

Jackson setup, typed configuration, and object mapping for a Spring Boot service. Open this when a JSON field is not binding, when configuration values are being read ad hoc across the codebase, or when writing a converter between an entity and a DTO.

---

### Jackson

Configure the object mapper once, centrally, and let every component share it. A mapper configured per class produces payloads that disagree with each other.

- On Spring Boot 4 the mapper is a Jackson 3 `JsonMapper`, in the `tools.jackson` packages, except the annotations, which keep their `com.fasterxml.jackson.annotation` package. Jackson 3 has `java.time` support built into databind, writes dates as ISO-8601 strings, and ignores unknown properties by default, so it needs no module registration and no YAML for any of the three.
- A tolerant reader is the point of that last default: it survives a producer adding a field, which is the normal way a compatible API evolves. Do not turn `FAIL_ON_UNKNOWN_PROPERTIES` back on for inbound DTOs.
- On a Jackson 2 project, which Spring Boot 4 still supports but has deprecated, a hand-built `ObjectMapper` has to register `JavaTimeModule` and set `WRITE_DATES_AS_TIMESTAMPS` and `FAIL_ON_UNKNOWN_PROPERTIES` to false explicitly, because plain Jackson 2 defaults both to true.
- Use `@JsonProperty` wherever the JSON name and the Java name differ, so a field rename in Java does not silently break the wire contract.
- Never serialise a domain entity directly. A DTO is the contract, and an entity exposed as JSON leaks the schema, the lazy proxies, and every field somebody adds later.

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

A value someone might reasonably change per environment or per incident is a tunable, and a tunable never lives in Java, neither as a literal nor as a `static final` constant. That covers cron expressions, fixed delays, durations, time to live and timeouts, retry counts, cache and rate-limit bucket sizes, CORS origins and other allow-lists, interceptor order, and business maximums such as how many cost items or dashboard cards a request may carry. Changing one of them in code needs a build and a release; changing it in `application.yml` needs a restart, and a profile file can vary it.

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

### Entity and DTO mapping

Prefer a compile-time mapper such as MapStruct. It generates plain Java, so the mapping is explicit, fast, and
verified by the compiler rather than by reflection at runtime, and a field added on one side without the other
becomes a build error.

```java
@Mapper(componentModel = "spring")
public interface MarketMapper {
  MarketResponse toResponse(MarketEntity entity);
}
```

Hand-write a mapper only where the generated one would be wrong, the common case being managed audit fields that a
full mapping would overwrite. When you do, keep it in the same package as the generated mappers so nobody has to
guess which convention a given type follows.

Avoid reflective bean-copy utilities. They compile against nothing, fail silently on a rename, and copy fields
nobody intended to expose.
