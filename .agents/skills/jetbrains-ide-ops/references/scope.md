# Scope

Companion reference for the [jetbrains-ide-ops](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

JetBrains IDE project configuration for a multi-module monorepo: run configurations under `.run/`, which `.idea/` files are committed, Gradle module links, module naming and the rename checklist.

- Editing anything under a `.run/` directory or under `.idea/`
- Creating or repairing an IntelliJ or PyCharm run configuration
- A run configuration appears under Unknown, or its interpreter field comes up empty
- Module names in the project tree do not match the directories on disk, or the Gradle tool window shows duplicates
- Deciding which `.idea/` files belong in version control, or repairing a half-committed set
- Renaming a module, container or image, and keeping IDE-built image names in step with Compose
- The user says "add a run configuration for this service", "which .idea files do we commit", "I renamed a module, what else has to change", "this run configuration shows as Unknown", "the interpreter field is empty" or "the Gradle window shows the module twice"

---

### When not to activate

- Writing the Dockerfile or the Compose file a run configuration points at, use `docker-patterns`
- Ignore patterns and staging discipline outside `.idea/`, use `git-workflow`
- The Gradle build itself, its version catalog and its plugins, use `build-dependency-management`
- Spring profiles and application configuration a run configuration activates, use `springboot-patterns`
- The human-facing setup section that tells a developer how to open the project, use `markdown-writer`

---

### Related skills

- `docker-patterns` owns the Dockerfile and the Compose file the Docker run configurations point at
- `git-workflow` owns ignore patterns and staging discipline outside `.idea/`
- `build-dependency-management` owns the Gradle build the IDE imports
- `springboot-patterns` owns the profiles a Spring Boot run configuration activates
- `observability-and-logging` owns the scrape job and dashboard names the rename checklist walks
- `markdown-writer` owns the human-facing setup section that points a developer at `.run/`
