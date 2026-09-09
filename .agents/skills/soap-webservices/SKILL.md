---
name: soap-webservices
description: Contract-first SOAP integration in Java, covering WSDL and XSD as the source of truth, JAXB binding files, CXF code generation, XXE prevention, WS-Security, fault taxonomy, PII-safe logging, Resilience4j retries, and MTOM. Use when you say "generate Java classes from this WSDL", "call a partner SOAP service", "add WS-Security UsernameToken", "stub a SOAP endpoint in tests", or "our SOAP client hangs". Not for REST contracts, use `api-design`.
---

# SOAP Web Service Standards

Rules for integrating with SOAP services from a Java application, where the contract is a WSDL owned by someone else
and the generated code is a build artifact. Everything here assumes contract-first: the schema is the truth and the
Java types follow it.

Baseline versions, current as of September 2026: Java 21 LTS, the `jakarta.*` namespace throughout (Jakarta XML Web
Services 4, JAXB 4), Apache CXF 4, Spring-WS 4 with WSS4J, and Resilience4j 2.

---

### When to activate

- Generating Java classes from a partner WSDL or XSD.
- Writing or reviewing a SOAP client, including its timeouts, pooling, and retry policy.
- Adding WS-Security, whether UsernameToken or X.509 signing and encryption.
- Mapping SOAP faults onto application exceptions, or designing the fault taxonomy.
- Stubbing a SOAP endpoint for tests, or handling MTOM attachments.

---

### When not to activate

- REST or GraphQL contract design: use `api-design`.
- Spring Boot service structure around the SOAP client: use `springboot-patterns`.
- Java language style in the hand-written code: use `java-coding-standards`.
- Gradle version catalogues and dependency admission: use `build-dependency-management`.
- Authentication of your own HTTP endpoints: use `springboot-patterns`.

---

### Reference map

| Task | Open |
| --- | --- |
| Wiring XJC and CXF code generation into a Gradle Kotlin DSL build | [references/code-generation.md](references/code-generation.md) |

---

### Contract-First Design and File Storage

- Adopt a contract-first approach: WSDL and XSD files are the absolute source of truth. Java code is always generated
  from the contract, never the reverse.
- Store all external WSDL and XSD files strictly in:
  - `src/main/resources/wsdl/`
  - `src/main/resources/xsd/`
- Group schema files by external provider and API version using subdirectories (e.g., `wsdl/providerName/v2/`).
- Do not modify third-party WSDL or XSD files directly to fix naming issues. Use JAXB binding files (`.xjb`) for all
  customisations.

---

### JAXB Binding Files and Translation Documentation

- Use JAXB binding files to map non-English element names to English Java equivalents during code generation:

```xml
<jaxb:bindings version="3.0"
    xmlns:jaxb="https://jakarta.ee/xml/ns/jaxb"
    xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <jaxb:bindings schemaLocation="service.xsd" node="/xs:schema">
    <jaxb:bindings node="//xs:element[@name='Invoice']">
      <jaxb:class name="InvoiceDocument"/>
    </jaxb:bindings>
    <jaxb:bindings node="//xs:element[@name='Amount']">
      <jaxb:property name="totalAmount"/>
    </jaxb:bindings>
  </jaxb:bindings>
</jaxb:bindings>
```

- Log every translation applied via binding files in `docs/TRANSLATIONS.md` at the project root using the following
  structure:

| Source Schema | Original Element | Mapped Name | Description |
|---|---|---|---|
| `service.xsd` | `Invoice` | `InvoiceDocument` | Accounts payable invoice document |
| `service.xsd` | `Amount` | `totalAmount` | Monetary amount, minor units |

- Document the WS-Security profile variant required by each integration partner in `docs/TRANSLATIONS.md` alongside the
  translation table.

---

### Javadoc

Default to none. A Javadoc block is usually a sign that the code failed to explain itself. Before writing one, extract
the unclear block into a well-named method, rename the parameters so they carry their own meaning, and tighten the
types. Do that first and most Javadoc blocks have nothing left to say, which is the outcome you want. Code that
explains itself cannot go stale, a comment can.

When one is still genuinely needed, the prose is capped at five lines and is usually one. Every tag line is capped at
one line, `@param` and `@return` and `@throws` alike, and only appears when it genuinely adds something: if the note
does not fit on a single line, shorten it or drop the tag. Four rules decide what goes in.

1. Prose. One sentence saying what it does, then only what a caller cannot infer from the signature. Nothing more.
2. `@param` only when the name and the type do not already convey it, meaning units, nullability, a valid range, or
   who owns the argument afterwards. `@param orderId the wholesale order identifier` is noise, delete it.
3. `@return` only when it is non-obvious.
4. `@throws` always, for every exception a caller can act on. Unchecked exceptions never appear in the signature, so
   this one is genuinely contract rather than decoration.

Going past the five-line prose cap is allowed only when the contract genuinely cannot be stated in fewer lines, for
example a documented state machine, an ordering requirement, or a concurrency guarantee. It is an exception you
justify in review, not a budget to spend. The one-line cap on a tag line has no exception at all: shorten it or delete
it.

```java
// GOOD: one sentence, then only what the signature cannot say
/**
 * Maps the inbound reservation request onto the domain and returns the ack.
 *
 * @throws ReservationFault when the warehouse cannot cover the request
 */
@PayloadRoot(namespace = NS, localPart = "ReserveRequest")
public ReserveResponse reserve(@RequestPayload ReserveRequest request) { ... }

// BAD: restates the signature and the annotation
/**
 * Handles the reserve request.
 *
 * @param request the reserve request
 * @return the reserve response
 */
public ReserveResponse reserve(@RequestPayload ReserveRequest request) { ... }
```

---

### Security Practices

#### XXE Prevention

- Disable Document Type Definitions (DTDs) and external entity processing on all XML unmarshallers to prevent XXE
  injection attacks:

```java
SAXParserFactory spf = SAXParserFactory.newInstance();
spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
spf.setFeature("http://xml.org/sax/features/external-general-entities", false);
spf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
```

#### TLS Enforcement

- Enforce TLS/HTTPS for all SOAP endpoint communications. Reject plain HTTP connections.
- Set explicit connect and read timeouts on the underlying HTTP client to prevent thread starvation from unresponsive
  SOAP servers.

#### Connection Pooling

- Configure HTTP connection pooling (Apache HttpClient `PoolingHttpClientConnectionManager` or CXF's `HTTPConduit`) for
  the underlying transport layer to improve throughput under concurrent load.

---

### SOAP Service Singleton

- Instantiate the heavy SOAP `Service` class once (as a Spring Bean or application-scoped singleton) to avoid the high
  cost of repeatedly parsing the WSDL on every request.
- Inject the `Service` singleton and obtain `Port` instances from it per-request, or pool and reuse `Port` instances in
  a thread-safe manner.

---

### WS-Security

- Use WS-Security (WSS4J / Spring-WS `Wss4jSecurityInterceptor`) when the integration partner requires message-level
  security beyond transport TLS.
- For username/password authentication, use `UsernameToken` with PasswordDigest mode. Never transmit passwords in
  plaintext in the SOAP header.
- For high-security integrations, use X.509 certificate signing and encryption of the SOAP body. Store private keys in a
  KMS or Java KeyStore (`PKCS12`). Never store private keys in plaintext files.
- Configure `Wss4jSecurityInterceptor` example:

```java
Wss4jSecurityInterceptor interceptor = new Wss4jSecurityInterceptor();
interceptor.setSecurementActions("UsernameToken");
interceptor.setSecurementUsername("serviceUser");
interceptor.setSecurementPassword(passwordFromVault);
interceptor.setSecurementPasswordType(WSConstants.PW_DIGEST);
```

---

### SOAP Fault Taxonomy

- Always catch `SOAPFaultException` at the service client boundary and map it to a typed application exception before
  propagating to business logic. Never let raw `SOAPFaultException` reach an HTTP API response.
- Log the full fault code, fault string, and detail element at `WARN` level after redacting any PII in the detail
  element. Use `ERROR` level only for unexpected system faults.
- Distinguish two categories of faults in integration documentation:
  - Business faults: invalid invoice number, unknown customer ID, insufficient balance. Non-retryable.
  - System faults: service unavailable, timeout, internal server error. Retryable with backoff.
- Translate all faults to a standardised error envelope before returning to the caller.

---

### Message Logging with PII Redaction

- Log all outbound SOAP requests and inbound responses at `DEBUG` level using a Spring-WS `PayloadLoggingInterceptor` or
  a custom `ClientInterceptor`.
- Before writing to logs, redact:
  - Authentication credentials in WS-Security headers
  - PII fields (names, addresses, tax IDs, NINs)
  - Financial data (account numbers, card numbers)
- In production, enable full message logging only when a debug flag is active via environment variable. Do not log
  complete SOAP envelopes by default.

---

### Resilience4j, Retry and Circuit Breaker

- Wrap all outbound SOAP client calls with a Resilience4j circuit breaker and retry policy.
- Configure exponential backoff with jitter on retry. Maximum of 3 retries for transient faults.
- Retryable conditions: HTTP 5xx responses, `SOAPFaultException` with a system fault code, connection timeouts.
- Non-retryable conditions: business fault codes (invalid input, authorisation failure).

```java
RetryConfig retryConfig = RetryConfig.custom()
    .maxAttempts(3)
    .waitDuration(Duration.ofMillis(500))
    .intervalFunction(IntervalFunction.ofExponentialRandomBackoff(500, 2.0, 0.5))
    .retryOnException(e -> e instanceof SoapSystemFaultException)
    .build();
```

---

### Testing SOAP Integrations

- Use WireMock (`WireMockExtension` for JUnit 5) to stub SOAP endpoints in unit and integration tests. Never call real
  external SOAP services in automated tests.
- Store WireMock response stubs (raw SOAP XML files) under `src/test/resources/wiremock/` versioned alongside the WSDL.
- Use SoapUI or ReadyAPI for exploratory integration testing against the real partner endpoint during development and
  certification.
- Write at least one test for each fault taxonomy category: expected business fault, unexpected system fault, timeout,
  and malformed response.

---

### MTOM for Binary Payloads

- Use MTOM (Message Transmission Optimization Mechanism) for transmitting binary payloads (PDFs, images, signed
  documents) larger than 10 KB to avoid base64 encoding overhead.
- Configure `jakarta.xml.ws.soap.MTOMFeature` on the service port when MTOM is required:

```java
MTOMFeature mtomFeature = new MTOMFeature(true, 10240); // threshold 10 KB
MyService port = service.getMyServicePort(mtomFeature);
```

- Enforce a maximum attachment size limit on the server side and validate MIME types of received attachments to prevent
  abuse.

---

### WSDL Versioning

- Treat the WSDL as an immutable contract once published. Changes require a new WSDL version in a new subdirectory
  (e.g., `wsdl/providerName/v2/`).
- Additive changes (new optional XSD elements) are permitted without a version bump only if they do not break existing
  generated code.
- Coordinate WSDL version upgrades with the integration partner before updating the dependency in `build.gradle.kts`.
- Keep the previous WSDL version's generated client code available until all consumers have migrated.

---

### Related skills

- `api-design` when the same domain is also exposed over HTTP and JSON.
- `springboot-patterns` for the service and repository layers around the generated client.
- `java-coding-standards` for the hand-written mapping and exception classes.
- `build-dependency-management` for pinning CXF, JAXB, and WSS4J versions in one place.
- `security-review` before an integration handles credentials, payments, or personal data.
- `observability-and-logging` for correlating a SOAP call with the request that triggered it.

---

### Checklist

- [ ] The WSDL and XSD live under `src/main/resources/`, grouped by provider and version, and are never hand-edited.
- [ ] Every naming fix goes through a `.xjb` binding file and is recorded in the translation table.
- [ ] Generated sources land in the build directory and are absent from version control.
- [ ] DTD and external entity processing are disabled on every unmarshaller.
- [ ] TLS is enforced, with explicit connect and read timeouts on the HTTP client.
- [ ] The `Service` object is a singleton, and the transport uses a connection pool.
- [ ] WS-Security passwords use digest mode, and private keys live in a keystore or KMS.
- [ ] Faults are split into business and system categories, and only system faults are retried.
- [ ] Message logging redacts credentials, personal data, and financial identifiers.
- [ ] Tests stub the endpoint with WireMock and cover a business fault, a system fault, a timeout, and a malformed
      response.
