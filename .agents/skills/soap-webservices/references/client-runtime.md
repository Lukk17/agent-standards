# Client Runtime, Security and Testing

Contents:

- [Security Practices](#security-practices)
- [SOAP Service Singleton](#soap-service-singleton)
- [WS-Security](#ws-security)
- [SOAP Fault Taxonomy](#soap-fault-taxonomy)
- [Message Logging with PII Redaction](#message-logging-with-pii-redaction)
- [Resilience4j, Retry and Circuit Breaker](#resilience4j-retry-and-circuit-breaker)
- [Testing SOAP Integrations](#testing-soap-integrations)
- [MTOM for Binary Payloads](#mtom-for-binary-payloads)

Companion reference for the [soap-webservices](../SKILL.md) skill. Load it when hardening the XML parser, configuring transport, wiring WS-Security, mapping faults, logging messages, adding retries, stubbing an endpoint in tests, or sending binary payloads with MTOM.

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

- The client is the CXF-generated JAX-WS port, so every interceptor below is a CXF one attached to that port through
  `ClientProxy.getClient(port)`. Spring-WS interceptors such as `Wss4jSecurityInterceptor` plug into a
  `WebServiceTemplate`, not a JAX-WS port, and do not apply here.
- Use WS-Security through CXF's `WSS4JOutInterceptor` when the integration partner requires message-level security
  beyond transport TLS.
- For username/password authentication, use `UsernameToken` with PasswordDigest mode. Never transmit passwords in
  plaintext in the SOAP header.
- For high-security integrations, use X.509 certificate signing and encryption of the SOAP body. Store private keys in a
  KMS or Java KeyStore (`PKCS12`). Never store private keys in plaintext files.
- Configure `WSS4JOutInterceptor` example, with the password supplied by a callback that reads it from the vault:

```java
Map<String, Object> props = Map.of(
    ConfigurationConstants.ACTION, ConfigurationConstants.USERNAME_TOKEN,
    ConfigurationConstants.USER, "serviceUser",
    ConfigurationConstants.PASSWORD_TYPE, WSConstants.PW_DIGEST,
    ConfigurationConstants.PW_CALLBACK_REF, vaultPasswordCallback);
ClientProxy.getClient(port).getOutInterceptors().add(new WSS4JOutInterceptor(props));
```

---

### SOAP Fault Taxonomy

- Always catch `SOAPFaultException` at the service client boundary and map it to a typed application exception before
  propagating to business logic. Never let raw `SOAPFaultException` reach an HTTP API response.
- Log the full fault code, fault string, and detail element at `WARN` level after redacting any PII in the detail
  element. Use `ERROR` level only for unexpected system faults.
- Distinguish two categories of faults in integration documentation:
  - Business faults: invalid invoice number, unknown customer ID, insufficient balance. Non-retryable.
  - System faults: an internal server error reported as a SOAP fault. Non-retryable, because the server received the
    request and may have acted on it.
- Translate all faults to a standardised error envelope before returning to the caller.

---

### Message Logging with PII Redaction

- Log all outbound SOAP requests and inbound responses at `DEBUG` level using CXF's `LoggingFeature` on the client
  port, and name the elements to mask with `setSensitiveElementNames` and `setSensitiveProtocolHeaderNames`.
- Before writing to logs, redact:
  - Authentication credentials in WS-Security headers
  - PII fields (names, addresses, tax IDs, NINs)
  - Financial data (account numbers, card numbers)
- In production, enable full message logging only when a debug flag is active via environment variable. Do not log
  complete SOAP envelopes by default.

---

### Resilience4j, Retry and Circuit Breaker

- Wrap all outbound SOAP client calls with a Resilience4j circuit breaker and retry policy.
- The retry policy itself (deadline per attempt, attempt budget, backoff with jitter, retryable statuses) is owned by
  `backend-patterns`. This section applies it to SOAP.
- At most 3 attempts, meaning one call and two retries, with exponential backoff and jitter. Resilience4j counts the
  initial call as the first attempt.
- Retryable conditions: transient transport failures only, meaning HTTP 502, 503 and 504 and connection or read
  timeouts. The client boundary maps each of them to a typed `SoapTransportException`.
- Non-retryable conditions: every SOAP fault, business or system. SOAP 1.1 returns every fault as HTTP 500, so an
  HTTP 500 is classified by its fault code and never retried on its status code.

```java
RetryConfig retryConfig = RetryConfig.custom()
    .maxAttempts(3)
    .waitDuration(Duration.ofMillis(500))
    .intervalFunction(IntervalFunction.ofExponentialRandomBackoff(500, 2.0, 0.5))
    .retryOnException(e -> e instanceof SoapTransportException)
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
