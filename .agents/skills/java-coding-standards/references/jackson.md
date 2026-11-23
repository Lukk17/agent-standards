# Jackson

Jackson setup for a Spring Boot service. Open this when a JSON field is not binding, or when a mapper is being configured.

---

### Jackson

Configure the object mapper once, centrally, and let every component share it. A mapper configured per class produces payloads that disagree with each other.

- On Spring Boot 4 the mapper is a Jackson 3 `JsonMapper`, in the `tools.jackson` packages, except the annotations, which keep their `com.fasterxml.jackson.annotation` package. Jackson 3 has `java.time` support built into databind, writes dates as ISO-8601 strings, and ignores unknown properties by default, so it needs no module registration and no YAML for any of the three.
- A tolerant reader is the point of that last default: it survives a producer adding a field, which is the normal way a compatible API evolves. Do not turn `FAIL_ON_UNKNOWN_PROPERTIES` back on for inbound DTOs.
- On a Jackson 2 project, which Spring Boot 4 still supports but has deprecated, a hand-built `ObjectMapper` has to register `JavaTimeModule` and set `WRITE_DATES_AS_TIMESTAMPS` and `FAIL_ON_UNKNOWN_PROPERTIES` to false explicitly, because plain Jackson 2 defaults both to true.
- Use `@JsonProperty` wherever the JSON name and the Java name differ, so a field rename in Java does not silently break the wire contract.
- Never serialise a domain entity directly. A DTO is the contract, and an entity exposed as JSON leaks the schema, the lazy proxies, and every field somebody adds later.
