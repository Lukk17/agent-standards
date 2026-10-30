---
name: soap-webservices
description: 'Contract-first SOAP integration in Java: WSDL and XSD as the source of truth, JAXB bindings, CXF code generation, XXE prevention, WS-Security, fault taxonomy, PII-safe logging, retries and MTOM. Use when the user says "generate Java classes from this WSDL", "call a partner SOAP service", "add WS-Security UsernameToken" or "our SOAP client hangs". Not for REST contracts, use `api-design`.'
---

# SOAP Web Service Standards

Rules for integrating with SOAP services from a Java application, where the contract is a WSDL owned by someone else
and the generated code is a build artifact. Everything here assumes contract-first: the schema is the truth and the
Java types follow it.

Written for Java 21 LTS as the minimum and Java 25 LTS as the recommended target, the `jakarta.*` namespace throughout (Jakarta XML Web Services 4, JAXB 4), Apache CXF 4 and Spring-WS with WSS4J, and Resilience4j 2. Match the line to the Spring generation: on Spring Boot 4 and Spring Framework 7 use Spring-WS 5 and the CXF 4.2 line, and on Spring Boot 3 and Spring Framework 6 use Spring-WS 4 and the CXF 4.1 line, because each of those lines is built against that one Spring generation.

---

### When to activate

- Generating Java classes from a partner WSDL or XSD.
- Writing or reviewing a SOAP client, including its timeouts, pooling, and retry policy.
- Adding WS-Security, whether UsernameToken or X.509 signing and encryption.
- Mapping SOAP faults onto application exceptions, or designing the fault taxonomy.
- Stubbing a SOAP endpoint for tests, or handling MTOM attachments.
- The user says "stub a SOAP endpoint in tests".

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
| Storing the WSDL and XSD, writing `.xjb` bindings, the translation table, Javadoc, WSDL versioning | [references/contract-and-bindings.md](references/contract-and-bindings.md) |
| XXE, TLS, pooling, the `Service` singleton, WS-Security, faults, logging, retries, tests, MTOM, with code | [references/client-runtime.md](references/client-runtime.md) |
| Wiring XJC and CXF code generation into a Gradle Kotlin DSL build | [references/code-generation.md](references/code-generation.md) |

---

### Rules

1. WSDL and XSD are the source of truth, stored under `src/main/resources/wsdl/` and `src/main/resources/xsd/`, grouped by provider and version (`wsdl/providerName/v2/`). Java is generated from them, never the reverse.
2. Never edit a third-party WSDL or XSD. Fix naming in a JAXB binding file (`.xjb`), and record every translation and each partner's WS-Security profile in `docs/TRANSLATIONS.md`.
3. Javadoc defaults to none. When needed: one sentence of prose (cap five lines), one-line tags, `@throws` for every exception a caller can act on.
4. Disable DTDs and external entities on every unmarshaller to prevent XXE.
5. Enforce TLS, reject plain HTTP, and set explicit connect and read timeouts. Pool the HTTP transport.
6. Build the `Service` once as a singleton and obtain or pool `Port` instances from it.
7. WS-Security goes through CXF's `WSS4JOutInterceptor` on the JAX-WS port, not Spring-WS interceptors. UsernameToken uses PasswordDigest with the password from a vault callback, and X.509 private keys live in a KMS or a PKCS12 keystore, never a plaintext file.
8. Catch `SOAPFaultException` at the client boundary and map it to a typed exception and a standard error envelope. Never let a raw fault reach an HTTP response. Log the fault at `WARN` with PII redacted, `ERROR` only for unexpected system faults.
9. Log messages at `DEBUG` through CXF `LoggingFeature`, masking credentials, PII and financial data. Full envelopes in production only behind an environment debug flag.
10. Wrap every call in a Resilience4j circuit breaker and retry: at most 3 attempts with exponential backoff and jitter, retrying only HTTP 502, 503, 504 and timeouts mapped to `SoapTransportException`. Never retry a SOAP fault, including an HTTP 500. The policy itself is owned by `backend-patterns`.
11. Stub endpoints with WireMock, never real services, and test a business fault, a system fault, a timeout and a malformed response.
12. Use MTOM for binary payloads over 10 KB, with a server-side size limit and MIME type validation.
13. A published WSDL is immutable: a breaking change is a new version folder, coordinated with the partner, and the old generated client stays until every consumer migrates.

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
- [ ] Faults are split into business and system categories, no SOAP fault is retried, and only transport failures
      (502, 503, 504, timeouts) are.
- [ ] Message logging redacts credentials, personal data, and financial identifiers.
- [ ] Tests stub the endpoint with WireMock and cover a business fault, a system fault, a timeout, and a malformed
      response.
