# Project Layout and Code Smells

Where classes live in a layered Spring Boot project, and the recurring smells worth fixing the moment you see them.
Open this when starting a module, when a package has become a dumping ground, or during a review pass.

---

### Package layout

```text
src/main/java/com/example/app/
  config/
  controller/
  service/
  repository/
  domain/
  dto/
  util/
src/main/resources/
  application.yml
src/test/java/... (mirrors main)
```

The test tree mirrors the main tree exactly, so a reader finds the test for a class from its package path alone,
and a missing test is visible as a missing file rather than as a coverage number.

Two failure modes to watch. A `util` package that becomes the place anything unclassified lands is a sign that some
of those classes belong to a domain concept nobody has named yet. And a `service` package holding thirty classes
usually wants splitting by feature rather than by technical role.

Where the project has chosen ports and adapters instead, `hexagonal-architecture` owns the layout and this
technical-layer structure does not apply. Pick one and use it consistently across the codebase, because two
conventions side by side leave every reader guessing which one a given class follows.

---

### Code smells to fix on sight

| Smell | Why it hurts | Fix |
| --- | --- | --- |
| Long parameter list | Callers pass arguments positionally and swap two of the same type without a compile error. | A DTO, a record, or a builder. |
| Deep nesting | The reader has to hold every enclosing condition in mind to understand the innermost line. | Early returns and guard clauses. |
| Magic number | The value's meaning lives only in the head of whoever typed it. | A named constant. |
| Static mutable state | Tests interfere with each other, and threads race invisibly. | Dependency injection. |
| Silent catch block | A failure becomes a wrong answer instead of an error. | Log and act, or rethrow with context. |
| Comment explaining a block | The code failed to explain itself and the comment will go stale. | Extract a well-named method. |
| Boolean parameter | The call site reads `process(order, true)` and says nothing. | Two methods, or an enum. |
