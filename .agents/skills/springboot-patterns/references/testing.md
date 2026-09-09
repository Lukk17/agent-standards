# Testing a Spring Boot Service

Test-first development with JUnit 5, Mockito, MockMvc, `@DataJpaTest`, Testcontainers, and a JaCoCo gate. Open this
when starting a feature, fixing a bug, deciding which slice a piece of behaviour belongs in, or when the coverage
gate is failing the build. The target is around 90% coverage of real logic across unit and integration tests, and
100% where it genuinely adds value.

---

### Write the failing test first

Red, green, refactor, in that order. A test written after the code passes on the first run, which proves nothing
about whether it would catch the regression it exists for.

1. Write a test that fails for the right reason.
2. Write the least code that makes it pass.
3. Refactor with the suite green.
4. Keep the JaCoCo gate enforced rather than advisory.

Every test satisfies FIRST: Fast, running in milliseconds. Isolated, with no dependence on another test or on
shared state. Repeatable, giving the same result on every machine. Self-validating, a single pass or fail with no
manual inspection. Timely, written alongside or before the code. FIRST governs this whole workflow.

Pass: the new test fails, then the implementation makes it pass.

Fail: the implementation lands first and the test is written to match whatever it already does.

---

### Unit tests with JUnit 5 and Mockito

Test service logic in isolation with mocked collaborators, and cover the error and edge paths alongside the happy
one. A suite that only tests the happy path is a suite that goes green during an outage.

```java
@ExtendWith(MockitoExtension.class)
class MarketServiceTest {
  @Mock MarketRepository repo;
  @InjectMocks MarketService service;

  @Test
  void createsMarket() {
    CreateMarketRequest req = new CreateMarketRequest("name", "desc", Instant.now(), List.of("cat"));
    when(repo.save(any())).thenAnswer(inv -> inv.getArgument(0));

    Market result = service.create(req);

    assertThat(result.name()).isEqualTo("name");
    verify(repo).save(any());
  }

  @Test
  void create_whenRepositoryFails_propagatesException() {
    CreateMarketRequest req = new CreateMarketRequest("name", "desc", Instant.now(), List.of("cat"));
    when(repo.save(any())).thenThrow(new DataAccessResourceFailureException("db down"));

    assertThatThrownBy(() -> service.create(req))
        .isInstanceOf(DataAccessResourceFailureException.class);
    verify(repo).save(any());
  }

  @Test
  void create_withEmptyCategories_stillCreatesMarket() {
    CreateMarketRequest req = new CreateMarketRequest("name", "desc", Instant.now(), List.of());
    when(repo.save(any())).thenAnswer(inv -> inv.getArgument(0));

    Market result = service.create(req);

    assertThat(result.categories()).isEmpty();
  }
}
```

Pass: setup, action, and assertion in every test body, one behaviour per test, `@ParameterizedTest` for variants.

Fail: a partial mock of the class under test, or a test that asserts nothing beyond "no exception was thrown".

Label the test phases only if the project labels them at all, per the Test Structure section of `coding-standards`.

---

### Web layer tests with MockMvc

`@WebMvcTest` loads the controller, the argument resolvers, and the validation, and nothing else. Use it to assert
status codes, response shape, and validation behaviour.

```java
@WebMvcTest(MarketController.class)
class MarketControllerTest {
  @Autowired MockMvc mockMvc;
  @MockitoBean MarketService marketService;

  @Test
  void returnsMarkets() throws Exception {
    when(marketService.list(any())).thenReturn(Page.empty());

    mockMvc.perform(get("/api/markets"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray());
  }
}
```

Pass: `@MockitoBean` for a mocked Spring bean, which is the supported annotation on Boot 3.4 and newer.

Fail: `@MockBean`, which is deprecated, and a full `@SpringBootTest` context for a test that only checks a status
code.

---

### Integration tests with the real context

`@SpringBootTest` wires the whole application. Reserve it for behaviour that only appears when the layers are
connected, because every one of these tests costs a context startup.

```java
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class MarketIntegrationTest {
  @Autowired MockMvc mockMvc;

  @Test
  void createsMarket() throws Exception {
    mockMvc.perform(post("/api/markets")
        .contentType(MediaType.APPLICATION_JSON)
        .content("""
          {"name":"Test","description":"Desc","endDate":"2030-01-01T00:00:00Z","categories":["general"]}
        """))
      .andExpect(status().isCreated());
  }
}
```

Pass: a handful of integration tests covering the wiring, with the detail pushed down into slices.

Fail: every test written as `@SpringBootTest`, which turns a five-second suite into a five-minute one.

---

### Persistence tests against the production engine

Run repository tests against the database the service actually uses. H2 accepts SQL that PostgreSQL rejects, so a
green H2 suite says nothing about production.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(TestContainersConfig.class)
class MarketRepositoryTest {
  @Autowired MarketRepository repo;

  @Test
  void savesAndFinds() {
    MarketEntity entity = new MarketEntity();
    entity.setName("Test");
    repo.save(entity);

    Optional<MarketEntity> found = repo.findByName("Test");
    assertThat(found).isPresent();
  }
}
```

Pass: Testcontainers with reusable containers for Postgres and Redis, wired through `@DynamicPropertySource` so the
container's JDBC URL reaches the Spring context.

Fail: the embedded in-memory database that `@DataJpaTest` substitutes by default.

Entity and query design behind these tests is in [jpa.md](jpa.md).

---

### Assert with AssertJ

One fluent assertion library across the suite keeps failure messages readable and stops reviewers from switching
dialects mid-file.

Pass: `assertThat(...)` for values, `jsonPath` for response bodies, `assertThatThrownBy(...)` for exceptions.

Fail: a mix of JUnit `assertEquals`, Hamcrest matchers, and AssertJ in the same class.

---

### Build test data through builders

A builder with sensible defaults lets each test state only the field it cares about, so the intent of the test
survives a change to the constructor.

```java
class MarketBuilder {
  private String name = "Test";
  MarketBuilder withName(String name) { this.name = name; return this; }
  Market build() { return new Market(null, name, MarketStatus.ACTIVE); }
}
```

Pass: one shared builder or test data factory per aggregate.

Fail: a twelve-argument constructor call copied into thirty test methods.

---

### Enforce coverage in the build

Coverage is a gate, not a report nobody opens. Fail the build below the threshold, and measure real logic rather
than padding the number with generated accessors.

```xml
<plugin>
  <groupId>org.jacoco</groupId>
  <artifactId>jacoco-maven-plugin</artifactId>
  <version>0.8.14</version>
  <executions>
    <execution>
      <goals><goal>prepare-agent</goal></goals>
    </execution>
    <execution>
      <id>report</id>
      <phase>verify</phase>
      <goals><goal>report</goal></goals>
    </execution>
  </executions>
</plugin>
```

Take the plugin version from the project version catalog rather than pinning it per module, per
`build-dependency-management`.

Pass: `mvn verify` or `./gradlew test jacocoTestReport` fails when coverage drops below the threshold.

Fail: a coverage report generated and ignored, or a threshold lowered to make a red build green.

The pipeline that runs this suite alongside the build, static analysis, and scan gates is in
[verification-pipeline.md](verification-pipeline.md).

---

### Checklist

- [ ] Every behaviour change started with a test that failed for the right reason.
- [ ] Error and edge cases are covered, not just the happy path.
- [ ] Mocked Spring beans use `@MockitoBean`, never the deprecated `@MockBean`.
- [ ] Slices are used where they fit, and `@SpringBootTest` only where the wiring is the subject.
- [ ] Repository tests run against the production database engine through Testcontainers.
- [ ] Assertions are AssertJ throughout, with `jsonPath` for response bodies.
- [ ] Test data comes from builders rather than repeated constructor calls.
- [ ] The coverage gate fails the build, and nobody lowered the threshold to pass it.
