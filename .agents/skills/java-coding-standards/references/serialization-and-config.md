# Serialization, Configuration Binding, and Mapping

Jackson setup, typed configuration, and object mapping for a Spring Boot service. Open this when a JSON field is
not binding, when configuration values are being read ad hoc across the codebase, or when writing a converter
between an entity and a DTO.

---

### Jackson

Configure the object mapper once, centrally, and let every component share it. A mapper configured per class
produces payloads that disagree with each other.

- Register `JavaTimeModule` globally so `Instant`, `LocalDate`, and friends serialise as ISO-8601 strings rather
  than numeric arrays. Spring Boot's auto-configuration does this when the module is on the classpath, and a
  hand-built mapper has to do it explicitly.
- Set `FAIL_ON_UNKNOWN_PROPERTIES` to false for inbound DTOs. A tolerant reader survives a producer adding a field,
  which is the normal way a compatible API evolves.
- Use `@JsonProperty` wherever the JSON name and the Java name differ, so a field rename in Java does not silently
  break the wire contract.
- Never serialise a domain entity directly. A DTO is the contract, and an entity exposed as JSON leaks the schema,
  the lazy proxies, and every field somebody adds later.

```yaml
spring:
  jackson:
    deserialization:
      fail-on-unknown-properties: false
    serialization:
      write-dates-as-timestamps: false
```

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
