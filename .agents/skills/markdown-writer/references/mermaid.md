# Mermaid Diagrams

Companion reference for the [markdown-writer](../SKILL.md) skill. Load it when adding or repairing a diagram in a document, for the diagram types to use, the size limit, and the pass and fail example.

---

### Draw diagrams in Mermaid

Prefer Mermaid over an image, because it renders natively on most hosts and it diffs. Use `graph TB` with subgraphs
for a system overview and keep it under a dozen nodes, splitting into two diagrams rather than growing one. Use
`sequenceDiagram` for the happy path of one canonical request, with dashed arrows for async hops, and leave error
branches to `docs/`. Add `accTitle` and `accDescr` to any diagram in a portfolio-facing document.

Pass:

```text
graph TB
  Client --> API
  API --> DB[(Postgres)]
```

Fail:

```text
![architecture](docs/img/architecture-v3-final.png)
```

In a translated copy of a document, the node labels that carry an identifier stay untranslated, as [multilingual.md](multilingual.md) describes.
