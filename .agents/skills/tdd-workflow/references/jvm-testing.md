# JVM Testing Forms

Contents:

- [JUnit test naming](#junit-test-naming)
- [Test comments and display names](#test-comments-and-display-names)
- [Test data factory](#test-data-factory)
- [Contract testing with Spring Cloud Contract](#contract-testing-with-spring-cloud-contract)
- [Mutation testing with PIT](#mutation-testing-with-pit)
- [Coverage configuration with JaCoCo](#coverage-configuration-with-jacoco)
- [Testcontainers](#testcontainers)

The rules of this skill in the form a JVM project uses: JUnit, JaCoCo, PIT, Spring Cloud Contract and Testcontainers. Open it when the project is Java or another JVM language. The rule behind each section, with its reasoning, is in [loop-and-rules.md](loop-and-rules.md) or [advanced-testing.md](advanced-testing.md).

---

### JUnit test naming

Pass: the `<method>_<scenario>_<expectedResult>` form, which is the same rule spelled differently and is idiomatic in
JUnit codebases. Use it when the project already uses it, not as a second convention alongside the first.

```java
@Test
void calculateTotal_withEmptyCart_returnsZero() { }

@Test
void processPayment_whenCardDeclined_throwsPaymentException() { }
```

The two forms are alternatives, never a mix inside one codebase.

---

### Test comments and display names

The only comments in a test are the bare `// Given`, `// When`, `// Then` and `// When & Then` markers. What a test proves belongs in its name, or in `@DisplayName` where the name alone cannot carry it.

Pass:

```java
@Test
@DisplayName("a note longer than the limit is rejected before the decision is stored")
void decide_withOversizedNote_isRejected() {
    // Given
    var decision = decisionWithNoteOfLength(NOTE_LIMIT + 1);

    // When & Then
    assertThatThrownBy(() -> service.decide(decision)).isInstanceOf(NoteTooLongException.class);
    verifyNoInteractions(repository);
}
```

Fail:

```java
// ---- validation ----
@Test
void decide_withOversizedNote_isRejected() {
    var decision = decisionWithNoteOfLength(NOTE_LIMIT + 1); // one over the limit
    assertThatThrownBy(() -> service.decide(decision)).isInstanceOf(NoteTooLongException.class);
}
```

---

### Test data factory

The factory pattern from [advanced-testing.md](advanced-testing.md#test-data-factory) in Java, with one static method per named state.

```java
public final class OrderTestFactory {

  public static Order valid() {
    return Order.builder()
      .id(UUID.randomUUID())
      .customerId("cust-001")
      .items(List.of(OrderItem.of("SKU-1", 2, BigDecimal.valueOf(9.99))))
      .status(OrderStatus.PENDING)
      .build();
  }

  public static Order cancelled() {
    return valid().toBuilder().status(OrderStatus.CANCELLED).build();
  }
}
```

---

### Contract testing with Spring Cloud Contract

Use Spring Cloud Contract for JVM-to-JVM service pairs, and Pact in polyglot estates. A contract for one endpoint:

```groovy
Contract.make {
  request {
    method 'GET'
    url '/api/users/123'
  }
  response {
    status 200
    body([id: '123', name: 'Alice'])
    headers { contentType(applicationJson()) }
  }
}
```

---

### Mutation testing with PIT

PIT covers the JVM. Gate CI at a minimum mutation score of 70 percent.

```xml
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <configuration>
    <mutationThreshold>70</mutationThreshold>
    <coverageThreshold>80</coverageThreshold>
  </configuration>
</plugin>
```

---

### Coverage configuration with JaCoCo

The gate is the same as in the skill: 90 percent line coverage of real logic, 70 percent branch coverage minimum.

```xml
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
```

---

### Testcontainers

Every integration test that touches a database, message queue, cache, or cloud service runs it as a container the test
owns.

```java
import org.testcontainers.postgresql.PostgreSQLContainer;

@Testcontainers
@SpringBootTest
class OrderRepositoryTest {

  @Container
  @ServiceConnection
  static PostgreSQLContainer postgres = new PostgreSQLContainer(
      DockerImageName.parse("postgres:<version-tag>@sha256:<digest>").asCompatibleSubstituteFor("postgres"));
}
```

Pin the image to a version tag and its digest, wrapped in `asCompatibleSubstituteFor` so the module still accepts it. `springboot-patterns` explains the wrapper and the LocalStack exception, which is pinned by tag alone. `@ServiceConnection` hands Spring Boot the URL, the username and the password together. Outside Spring Boot, register
the URL, username and password from the container yourself, because the container creates its own user and a URL alone
fails authentication. The class shown is the Testcontainers 2 one, which moved each module into its own package and
dropped the generic type parameter.
