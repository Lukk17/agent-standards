# SOAP Web Services Checklist

Run it before calling a SOAP integration, or a review of one, done.

- [ ] The WSDL and XSD live under `src/main/resources/`, grouped by provider and version, and are never hand-edited.
- [ ] Every naming fix goes through a `.xjb` binding file and is recorded in the translation table.
- [ ] Generated sources land in the build directory and are absent from version control.
- [ ] DTD and external entity processing are disabled on every unmarshaller.
- [ ] TLS is enforced, with explicit connect and read timeouts on the HTTP client.
- [ ] The `Service` object is a singleton, and the transport uses a connection pool.
- [ ] WS-Security passwords use digest mode, and private keys live in a keystore or KMS.
- [ ] Faults are split into business and system categories, no SOAP fault is retried, and only transport failures (502, 503, 504, timeouts) are.
- [ ] Message logging redacts credentials, personal data, and financial identifiers.
- [ ] Tests stub the endpoint with WireMock and cover a business fault, a system fault, a timeout, and a malformed response.
