# Testing a Spring Boot Service

Test-first development with JUnit 6, Mockito, MockMvc, `@DataJpaTest`, Testcontainers, and a JaCoCo gate. Open this when starting a feature, fixing a bug, deciding which slice a piece of behaviour belongs in, or when the coverage gate is failing the build. The coverage gate, its threshold and which tests count toward it, is defined once in `tdd-workflow` under Coverage gate. This file only wires that gate into JaCoCo.

---

### Contents

- Write the failing test first
- Unit tests with JUnit 6 and Mockito
- Shape of a test class
- Web layer tests with MockMvc
- Integration tests with the real context
- Persistence tests against the production engine
- Assert with AssertJ
- Build test data through builders
- Enforce coverage in the build
- Checklist

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

### Unit tests with JUnit 6 and Mockito

Test service logic in isolation with mocked collaborators, and cover the error and edge paths alongside the happy
one. A suite that only tests the happy path is a suite that goes green during an outage.

```java
@ExtendWith(MockitoExtension.class)
class MarketServiceTest {
  @Mock MarketRepository repo;
  @InjectMocks MarketService service;

  @Test
  void create_withValidRequest_savesMarket() {
    // given
    CreateMarketRequest request = new CreateMarketRequest("name", "desc", Instant.now(), List.of("cat"));
    when(repo.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // when
    Market result = service.create(request);

    // then
    assertThat(result.name()).isEqualTo("name");
    verify(repo).save(any());
  }

  @Test
  void create_whenRepositoryFails_propagatesException() {
    // given
    CreateMarketRequest request = new CreateMarketRequest("name", "desc", Instant.now(), List.of("cat"));
    when(repo.save(any())).thenThrow(new DataAccessResourceFailureException("db down"));

    // when & then
    assertThatThrownBy(() -> service.create(request))
        .isInstanceOf(DataAccessResourceFailureException.class);
    verify(repo).save(any());
  }

  @Test
  void create_withEmptyCategories_stillCreatesMarket() {
    // given
    CreateMarketRequest request = new CreateMarketRequest("name", "desc", Instant.now(), List.of());
    when(repo.save(any())).thenAnswer(invocation -> invocation.getArgument(0));

    // when
    Market result = service.create(request);

    // then
    assertThat(result.categories()).isEmpty();
  }
}
```

Pass: setup, action, and assertion in every test body, one behaviour per test, `@ParameterizedTest` for variants.

Fail: a partial mock of the class under test, or a test that asserts nothing beyond "no exception was thrown".

The phases are marked with the bare `// given`, `// when` and `// then` comments, or `// when & then` when the action is the assertion, and nothing else is a comment in a test, per the test comment rule in `tdd-workflow`.

---

### Shape of a test class

Let Mockito build the subject. Whenever the constructor takes only collaborators a mock can stand in for, the class carries `@ExtendWith(MockitoExtension.class)`, each collaborator is a `@Mock` field and the subject is an `@InjectMocks` field. A hand-written `service = new MarketService(repo, publisher)` in a `@BeforeEach` repeats the constructor in every test class and breaks each of them when a collaborator is added. Construct the subject yourself only when the constructor also needs plain values that are not mocks: a limit, a `Duration`, a `Set` of allowed values, a fixed `Clock`, or a real `ObjectMapper`. Even then keep the collaborators as `@Mock` fields.

Pass: `@Mock AuditLogRepository auditLogRepository;` and `@InjectMocks AuditRetentionService auditRetentionService;`.

Fail: `@BeforeEach void setUp() { service = new AuditRetentionService(repository, publisher); }` with both arguments mocks.

Use Lombok in test helpers and fixtures wherever it removes boilerplate: `@NoArgsConstructor(access = AccessLevel.PRIVATE)` on a holder of static fixture factories, `@Getter` or `@Builder` on a fixture type with many fields, and a record where the fixture is plain data. A hand-written private constructor and a page of getters in a test helper is the boilerplate Lombok exists to delete.

Keep a test class to one behaviour area. Past about 300 lines it is testing several, so split it into focused classes named for the behaviour, such as `ExpenseMapperToDomainTest` and `ExpenseMapperToResponseTest`, sharing their builders and canned data through one `<Subject>TestFixtures` class. A `*BranchTest` written to raise branch coverage folds into the behaviour class whose branch it covers, because coverage is a property of the behaviour tests, not a separate suite. The size rule and the split are owned by `tdd-workflow`.

Give a test its meaning through its name or `@DisplayName`, never through a comment: no divider banner, no section label such as `// --- helpers ---` or `// 7.1 happy path`, no comment at the top of the file saying what it tests.

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
    when(marketService.list(any())).thenReturn(new PageResponse<>(List.of(), 0, 20, 0, 0));

    mockMvc.perform(get("/api/v1/markets"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray());
  }
}
```

Pass: `@MockitoBean` for a mocked Spring bean, and `@MockitoSpyBean` for a spy.

Fail: `@MockBean` or `@SpyBean`, which Spring Boot 4 removed, so they no longer compile, and a full `@SpringBootTest` context for a test that only checks a status code.

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
    mockMvc.perform(post("/api/v1/markets")
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

Pass: a shared `@TestConfiguration` that declares each container as a bean annotated `@ServiceConnection`, so Spring Boot derives the connection details from the container itself.

```java
@TestConfiguration(proxyBeanMethods = false)
class TestContainersConfig {

  private static final String POSTGRES_IMAGE = "postgres:<version-tag>@sha256:<digest>";

  @Bean
  @ServiceConnection
  PostgreSQLContainer postgres() {
    return new PostgreSQLContainer(DockerImageName.parse(POSTGRES_IMAGE).asCompatibleSubstituteFor("postgres"));
  }
}
```

Pin every Testcontainers image the way `docker-patterns` pins a base image, to an exact version tag plus its `@sha256:` digest, so a moved tag never changes the database a green test ran against. A digest-pinned name no longer looks like the official image to the module's compatibility check, so wrap it in `DockerImageName.parse(image).asCompatibleSubstituteFor("<official image name>")`. The one exception is LocalStack: pin it to an exact version tag without a digest, because `LocalStackContainer` reads the tag to decide how it starts and which services it exposes, and a digest-qualified name hides it.

Use `@DynamicPropertySource` only for a property no service connection covers.

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
    <execution>
      <id>check</id>
      <phase>verify</phase>
      <goals><goal>check</goal></goals>
      <configuration>
        <rules>
          <rule>
            <element>BUNDLE</element>
            <limits>
              <limit>
                <counter>LINE</counter>
                <value>COVEREDRATIO</value>
                <minimum>0.90</minimum>
              </limit>
              <limit>
                <counter>BRANCH</counter>
                <value>COVEREDRATIO</value>
                <minimum>0.70</minimum>
              </limit>
            </limits>
          </rule>
        </rules>
      </configuration>
    </execution>
  </executions>
</plugin>
```

On Gradle the task that fails the build is `jacocoTestCoverageVerification`, not `jacocoTestReport`, which only
writes the report. Give it the same rule and hang it on `check`:

```kotlin
tasks.jacocoTestCoverageVerification {
  violationRules {
    rule {
      limit { counter = "LINE"; minimum = "0.90".toBigDecimal() }
      limit { counter = "BRANCH"; minimum = "0.70".toBigDecimal() }
    }
  }
}
tasks.check { dependsOn(tasks.jacocoTestCoverageVerification) }
```

Take the plugin version from the project version catalog rather than pinning it per module, per
`build-dependency-management`.

Pass: `mvn verify` or `./gradlew check` fails when line coverage drops below 90 percent or branch coverage below 70.

Fail: a coverage report generated and ignored, or a threshold lowered to make a red build green.

The pipeline that runs this suite alongside the build, static analysis, and scan gates is in
[verification-pipeline.md](verification-pipeline.md).

---

### Checklist

- [ ] Every behaviour change started with a test that failed for the right reason.
- [ ] Error and edge cases are covered, not just the happy path.
- [ ] Mocked Spring beans use `@MockitoBean` or `@MockitoSpyBean`, never the removed `@MockBean` or `@SpyBean`.
- [ ] Unit tests build the subject with `@InjectMocks` unless its constructor needs plain values.
- [ ] No comment in a test but the bare given, when and then markers, and no test class past about 300 lines.
- [ ] Test fixtures use Lombok or records rather than hand-written boilerplate.
- [ ] Every Testcontainers image is pinned to a version tag and a digest through `asCompatibleSubstituteFor`, LocalStack to an exact tag only.
- [ ] Slices are used where they fit, and `@SpringBootTest` only where the wiring is the subject.
- [ ] Repository tests run against the production database engine through Testcontainers.
- [ ] Assertions are AssertJ throughout, with `jsonPath` for response bodies.
- [ ] Test data comes from builders rather than repeated constructor calls.
- [ ] The coverage gate fails the build, and nobody lowered the threshold to pass it.
