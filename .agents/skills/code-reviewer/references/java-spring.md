# Standards Checklist: Java and Spring Boot

The standards checklist items for a diff that touches Java or Spring Boot code, or its tests. Run them in Step 3, after the items in SKILL.md that every diff gets. Every item names the skill that owns the rule and its reasoning, so a finding can cite it.

---

### Java and Spring Boot

- [ ] No cryptic abbreviation (`b0to30`, `r`, `s`, `buf`, `zis`), and a bucketed concept is an enum. `java-coding-standards`
- [ ] No tunable literal or constant in code: crons, delays, durations, timeouts, limits, bucket sizes, origins and business maximums bind from `application.yml` into a validated `@ConfigurationProperties` record, crons through `${...}`. Only algorithm and protocol constants stay. `java-coding-standards`
- [ ] No `@Query` JPQL or native string, `@NamedQuery`, `@Modifying` or `EntityManager.createQuery(String)`: reads are Specifications or derived methods, aggregates use the Criteria API, an ArchUnit rule guards it, and only whole-table backup tooling is allowlisted. `springboot-patterns`
- [ ] No record, class, enum or interface nested in a production class: each in its own file under `dto`, `model` or `exception`. `java-coding-standards`
- [ ] Every endpoint carries the composable OpenAPI response meta-annotations, the success code is honest (201, 202, 204, 302 where real), and errors reference the project's own problem schema as `application/problem+json`. `springboot-patterns`
- [ ] Every wrapped method, constructor or record parameter list is followed by a blank line before the body. `code-formatter`
- [ ] `Set` where the code checks membership or needs uniqueness, `List` only where order matters. `java-coding-standards`
- [ ] `StringUtils.hasText` or the project's shared helper, never a hand-rolled `s == null || s.isBlank()`. `java-coding-standards`
- [ ] No hand-written format sniffing or parsing where an installed library already decides. `review-duplication`

---

### Tests

- [ ] Mockito subjects use `@ExtendWith(MockitoExtension.class)`, `@Mock` and `@InjectMocks` unless the constructor needs plain values such as a limit, a `Duration`, a `Set`, a `Clock` or a real `ObjectMapper`. `springboot-patterns`
- [ ] Test helpers and fixtures use Lombok or records, not hand-written constructors and getters. `springboot-patterns`
- [ ] No test class past about 300 lines: split by behaviour, sharing one `<Subject>TestFixtures`, and no `*BranchTest` beside its behaviour class. `tdd-workflow`
- [ ] Testcontainers images are pinned to a version tag and a digest through `DockerImageName.parse(image).asCompatibleSubstituteFor("<official name>")`, LocalStack to an exact tag without a digest. `springboot-patterns`
- [ ] Test data is seeded through entities and repositories, raw SQL only to prove database-level behaviour. `springboot-patterns`
