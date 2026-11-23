# Spring Boot Checklist

Run it before calling a Spring Boot change, or a review of one, done. The checklists for one area sit at the end of [jpa.md](jpa.md), [security.md](security.md), [testing.md](testing.md) and [verification-pipeline.md](verification-pipeline.md).

- [ ] Controllers parse and return, services hold behaviour, repositories reach the database, nothing skips a layer.
- [ ] No entity and no Spring Data `Page` appears in a response body.
- [ ] Every error response is a `ProblemDetail` from one `@ControllerAdvice`.
- [ ] Outbound HTTP goes through `RestClient`, with a retry, a circuit breaker, and explicit timeouts.
- [ ] `@Transactional` sits on service methods only, with `readOnly = true` on query paths.
- [ ] Every cache has a TTL, a size bound, and an eviction path.
- [ ] Every sensitive path carries an authorization rule, and every request body is a validated DTO.
- [ ] No association is eager, every paged query has a sort, and no N+1 is left as a follow-up.
- [ ] Every behaviour change started with a test that failed for the right reason, in the narrowest slice.
- [ ] No `@Query` string, every read a `Specification` or derived method, guarded by ArchUnit.
- [ ] Every endpoint has the OpenAPI response meta-annotations, honest codes and the problem schema.
- [ ] Repository tests run on the production engine through digest-pinned Testcontainers.
- [ ] The verification pipeline ran in order and every gate is green before the pull request opens.
