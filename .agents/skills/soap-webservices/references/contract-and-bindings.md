# Contract, Bindings and Versioning

Contents:

- [Contract-First Design and File Storage](#contract-first-design-and-file-storage)
- [JAXB Binding Files and Translation Documentation](#jaxb-binding-files-and-translation-documentation)
- [Javadoc](#javadoc)
- [WSDL Versioning](#wsdl-versioning)

Companion reference for the [soap-webservices](../SKILL.md) skill. Load it when storing a partner WSDL or XSD, writing a JAXB binding file, recording a translation, writing Javadoc on an endpoint, or versioning a WSDL.

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

### WSDL Versioning

- Treat the WSDL as an immutable contract once published. Changes require a new WSDL version in a new subdirectory
  (e.g., `wsdl/providerName/v2/`).
- Additive changes (new optional XSD elements) are permitted without a version bump only if they do not break existing
  generated code.
- Coordinate WSDL version upgrades with the integration partner before updating the dependency in `build.gradle.kts`.
- Keep the previous WSDL version's generated client code available until all consumers have migrated.
