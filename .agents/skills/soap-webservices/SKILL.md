---
name: soap-webservices
description: 'Contract-first SOAP in Java: WSDL, JAXB bindings, CXF code generation, WS-Security. Use when the user says "generate Java classes from this WSDL" or "our SOAP client hangs". Not for REST design, use `api-design`.'
metadata:
  version: "1.1.0"
---

# SOAP Web Service Standards

Rules for integrating with SOAP services from a Java application, where the contract is a WSDL owned by someone else and the generated code is a build artifact. Everything here assumes contract-first: the schema is the truth and the Java types follow it.

Written for Java 21 LTS as the minimum and Java 25 LTS as the recommended target, the `jakarta.*` namespace throughout (Jakarta XML Web Services 4, JAXB 4), Apache CXF 4 and Spring-WS with WSS4J, and Resilience4j 2. The Spring-WS and CXF line for each Spring generation is in the client runtime reference.

---

### When not to activate

- REST or GraphQL contract design, use `api-design`.
- Spring Boot service structure around the SOAP client, or authentication of your own HTTP endpoints, use `springboot-patterns`.
- Java language style in the hand-written code, use `java-coding-standards`.

---

### Reference map

| Task | Open |
| --- | --- |
| Storing the WSDL and XSD, writing `.xjb` bindings, the translation table, WSDL versioning | [contract-and-bindings.md](references/contract-and-bindings.md) |
| XXE, TLS, pooling, the `Service` singleton, WS-Security, faults, logging, retries, tests, MTOM, with code | [client-runtime.md](references/client-runtime.md) |
| Wiring XJC and CXF code generation into a Gradle Kotlin DSL build | [code-generation.md](references/code-generation.md) |
| Writing or reviewing a Javadoc block | [javadoc.md](references/javadoc.md) |
| Before calling a SOAP integration or its review done | [checklist.md](references/checklist.md) |

---

### Rules

1. WSDL and XSD are the source of truth, stored under `src/main/resources/wsdl/` and `src/main/resources/xsd/`, grouped by provider and version. Java is generated from them, never the reverse.
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
