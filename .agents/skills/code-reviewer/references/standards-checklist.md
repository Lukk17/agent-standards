# Standards Checklist

Contents:

- [How to run it](#how-to-run-it)
- [Comments and size](#comments-and-size)
- [Java and Spring Boot](#java-and-spring-boot)
- [Tests](#tests)
- [Web](#web)
- [Python](#python)
- [CI, images and dependencies](#ci-images-and-dependencies)
- [Repository hygiene](#repository-hygiene)

The rules a project owner has had to repeat in review, as one explicit pass. Every item names the skill that owns the rule and its reasoning, so a finding can cite it. Load this file in Step 3 of every review and run each section the diff touches.

---

### How to run it

Walk the diff once per section below that applies to the files it touches. A violation is a finding like any other: lead with `path:line`, name the item, and give the concrete fix. Grade it Major when it repeats across the diff or would need a release to undo, such as a tunable in code or a floating image tag, and Minor when it is one local instance. Report every instance, not the first one, because "there are many more like this" is the comment a review exists to prevent. When the project's `AGENTS.md` states a stricter or different rule, the project wins, and the finding cites the project file instead.

---

### Comments and size

- [ ] No divider banner, section label or file-header comment saying what the file holds, in source, styles or tests. `coding-standards`
- [ ] No comment restating the code, no long comment block, only a short non-obvious why. `coding-standards`
- [ ] No class, module, component, hook or test file past about 300 lines without a split by responsibility. `coding-standards`
- [ ] No cryptic abbreviation (`b0to30`, `r`, `s`, `buf`, `zis`), and a bucketed concept is an enum. `java-coding-standards`
- [ ] No JSDoc explaining `T` and `D` where a descriptive type parameter such as `TRow` or `TDraft` would do. `coding-standards`

---

### Java and Spring Boot

- [ ] No tunable literal or constant in code: crons, delays, durations, timeouts, limits, bucket sizes, origins and business maximums bind from `application.yml` into a validated `@ConfigurationProperties` record, crons through `${...}`. Only algorithm and protocol constants stay. `java-coding-standards`
- [ ] No `@Query` JPQL or native string, `@NamedQuery`, `@Modifying` or `EntityManager.createQuery(String)`: reads are Specifications or derived methods, aggregates use the Criteria API, an ArchUnit rule guards it, and only whole-table backup tooling is allowlisted. `springboot-patterns`
- [ ] No record, class, enum or interface nested in a production class: each in its own file under `dto`, `model` or `exception`. `java-coding-standards`
- [ ] Every endpoint carries the composable OpenAPI response meta-annotations, the success code is honest (201, 202, 204, 302 where real), and errors reference the project's own problem schema as `application/problem+json`. `springboot-patterns`
- [ ] Every wrapped method, constructor or record parameter list is followed by a blank line before the body. `code-formatter`
- [ ] `Set` where the code checks membership or needs uniqueness, `List` only where order matters. `java-coding-standards`
- [ ] `StringUtils.hasText` or the project's shared helper, never a hand-rolled `s == null || s.isBlank()`. `java-coding-standards`
- [ ] No hand-written format sniffing or parsing where an installed library already decides. `review-duplication`

---

### Tests

- [ ] The only comments are the bare `// Given`, `// When`, `// Then` and `// When & Then` markers, and meaning lives in the test name or `@DisplayName`. `tdd-workflow`
- [ ] Mockito subjects use `@ExtendWith(MockitoExtension.class)`, `@Mock` and `@InjectMocks` unless the constructor needs plain values such as a limit, a `Duration`, a `Set`, a `Clock` or a real `ObjectMapper`. `springboot-patterns`
- [ ] Test helpers and fixtures use Lombok or records, not hand-written constructors and getters. `springboot-patterns`
- [ ] No test class past about 300 lines: split by behaviour, sharing one `<Subject>TestFixtures`, and no `*BranchTest` beside its behaviour class. `tdd-workflow`
- [ ] Testcontainers images are pinned to a version tag and a digest through `DockerImageName.parse(image).asCompatibleSubstituteFor("<official name>")`, LocalStack to an exact tag without a digest. `springboot-patterns`
- [ ] Test data is seeded through entities and repositories, raw SQL only to prove database-level behaviour. `springboot-patterns`

---

### Web

- [ ] No user-facing string in code, admin pages, metadata titles, aria labels, placeholders and toasts included: every one is a key in each locale's catalogue, at least English plus the product's language. `react-patterns`
- [ ] Identifiers and catalogue keys are English, and no component, page or layout holds a locale literal such as `"pl"` or `"pl-PL"`: the locale comes from the one i18n config module with an environment-driven default. `react-patterns`
- [ ] The project's AST copy guard runs in lint, and new copy did not slip past it with a pragma outside tests. `react-patterns`
- [ ] API modules past the size limit are folders with one file per concern, and a barrel exists only where import paths or mocks need it. `coding-standards`

---

### Python

- [ ] A script is a thin command-line entry calling single-responsibility modules of pure functions, each with pytest tests. `python-patterns`
- [ ] No long comment block in a module or above a function. `python-patterns`

---

### CI, images and dependencies

- [ ] Every `uses:` in a workflow or composite action is a full 40-character commit SHA with a `# vX.Y.Z` comment, resolved with `git ls-remote --tags` from the dereferenced `^{}` line. Check a few against the tag rather than trusting them. `deployment-patterns`
- [ ] No `runs-on: ubuntu-latest` or other `-latest` runner label. `deployment-patterns`
- [ ] Every container image, in a Dockerfile, a compose file, a `${VAR:-default}`, a CI `services:` block or a test, is an exact version tag plus `@sha256:` digest, and no release publishes or consumes `:latest`. `docker-patterns`
- [ ] No Dependabot version updates, Renovate configuration or other bump bot was added, unless the owner asked for it. `build-dependency-management`

---

### Repository hygiene

- [ ] No AI review scratch document (`*-review-findings.md`), agent plan, status file or run log is committed. `git-workflow`
- [ ] Committed generated files, lock files and OpenAPI-generated types included, are marked `linguist-generated=true` in `.gitattributes`, and lock files stay committed. `git-workflow`
