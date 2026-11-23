# Scope

Companion reference for the [soap-webservices](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Generating Java classes from a partner WSDL or XSD.
- Writing or reviewing a SOAP client, including its timeouts, pooling, and retry policy.
- Adding WS-Security, whether UsernameToken or X.509 signing and encryption.
- Mapping SOAP faults onto application exceptions, or designing the fault taxonomy.
- Stubbing a SOAP endpoint for tests, or handling MTOM attachments.
- The user says "generate Java classes from this WSDL", "call a partner SOAP service", "add WS-Security UsernameToken", "our SOAP client hangs" or "stub a SOAP endpoint in tests".

---

### When not to activate

- REST or GraphQL contract design: use `api-design`.
- Spring Boot service structure around the SOAP client: use `springboot-patterns`.
- Java language style in the hand-written code: use `java-coding-standards`.
- Gradle version catalogues and dependency admission: use `build-dependency-management`.
- Authentication of your own HTTP endpoints: use `springboot-patterns`.

---

### Related skills

- `api-design` when the same domain is also exposed over HTTP and JSON.
- `springboot-patterns` for the service and repository layers around the generated client.
- `java-coding-standards` for the hand-written mapping and exception classes, and the hand-written code that consumes the generated types.
- `build-dependency-management` for pinning CXF, JAXB, and WSS4J versions in one place, and the `jaxb` and `cxfTools` configuration versions of the code generation build centrally.
- `application-security-review` before an integration handles credentials, payments, or personal data.
- `observability-and-logging` for correlating a SOAP call with the request that triggered it.
