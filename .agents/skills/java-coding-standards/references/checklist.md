# Java Coding Standards Checklist

Run it before calling a Java change or a Java review done. The items that name a Spring or a Lombok annotation apply where the project uses that library.

- [ ] Names say what the thing is, with no cryptic abbreviation, and booleans read as questions.
- [ ] No type is nested in a production class, and no class runs past about 300 lines.
- [ ] No tunable is a literal or a constant, and every tunable binds through a validated `@ConfigurationProperties` record.
- [ ] `Set` where membership or uniqueness is the point, and `StringUtils.hasText` instead of a hand-rolled blank check.
- [ ] Every dependency arrives through the constructor, and no field carries `@Autowired`.
- [ ] Data types are records or final-field classes, with no setter that nothing needs.
- [ ] `Optional` appears only as a return type, and never after `.isPresent()` plus `.get()`.
- [ ] Stream pipelines are short, or extracted into named methods.
- [ ] Explicit types instead of `var`, except where the right-hand side already names the type.
- [ ] Domain exceptions are unchecked, named, and handled in one `@ControllerAdvice`.
- [ ] No raw types anywhere.
- [ ] Nullability annotations are present on public signatures and enforced in CI.
- [ ] Logging goes through `@Slf4j` with parameterised messages, never concatenation.
- [ ] Javadoc follows the `coding-standards` Doc Comments rules, with `@throws` on every unchecked exception a caller can act on.
