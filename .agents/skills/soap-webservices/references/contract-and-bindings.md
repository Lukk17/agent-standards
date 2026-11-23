# Contract, Bindings and Versioning

Contents:

- [Contract-First Design and File Storage](#contract-first-design-and-file-storage)
- [JAXB Binding Files and Translation Documentation](#jaxb-binding-files-and-translation-documentation)
- [WSDL Versioning](#wsdl-versioning)

Companion reference for the [soap-webservices](../SKILL.md) skill. Load it when storing a partner WSDL or XSD, writing a JAXB binding file, recording a translation, or versioning a WSDL. Javadoc on an endpoint is in [javadoc.md](javadoc.md).

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

### WSDL Versioning

- Treat the WSDL as an immutable contract once published. Changes require a new WSDL version in a new subdirectory
  (e.g., `wsdl/providerName/v2/`).
- Additive changes (new optional XSD elements) are permitted without a version bump only if they do not break existing
  generated code.
- Coordinate WSDL version upgrades with the integration partner before updating the dependency in `build.gradle.kts`.
- Keep the previous WSDL version's generated client code available until all consumers have migrated.
