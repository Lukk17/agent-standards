# Entity and DTO Mapping with MapStruct

Object mapping for a Spring Boot service. Open this when writing a converter between an entity and a DTO.

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
