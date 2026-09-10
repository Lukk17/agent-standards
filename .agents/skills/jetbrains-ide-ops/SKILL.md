---
name: jetbrains-ide-ops
description: 'JetBrains IDE project configuration for a multi-module monorepo: run configurations under `.run/`, which `.idea/` files are committed and which are ignored, the root module and per-build Gradle links, module naming, and the rename checklist that keeps the IDE, Compose and monitoring naming the same thing. Use when you say "add a run configuration for this service", "this run configuration shows as Unknown", "the interpreter field is empty", "the Gradle window shows the module twice", "which .idea files do we commit", or "I renamed a module, what else has to change". Not for the Dockerfile or Compose file itself, use `docker-patterns`, and not for ignore patterns outside `.idea/`, use `git-workflow`.'
---

# JetBrains IDE Ops

How IntelliJ IDEA and PyCharm project files behave in a monorepo of several independent builds: which files are
authored and which are generated, what a run configuration has to say to actually run, and what a rename has to
touch so the IDE, Compose and monitoring keep naming the same thing. Everything here was read out of live projects
rather than out of the dialog, because the dialog hides the half that goes wrong.

Baseline: IntelliJ IDEA 2026.2 on Windows 11 (verified locally). The XML shapes are stable across recent releases,
the cache directory under `%LOCALAPPDATA%` is the part that moves with the version.

| Task | Open |
|---|---|
| Creating or repairing a run configuration, or one shows as Unknown or with an empty interpreter | [run-configurations.md](references/run-configurations.md) |
| Deciding which `.idea/` files are committed, or a committed `modules.xml` has gone wrong on another machine | [version-control.md](references/version-control.md) |
| Linking several Gradle builds under one root, module naming, per-source-set import, reopening after a hand edit | [gradle-monorepo.md](references/gradle-monorepo.md) |
| Renaming a module, a service or an image, and checking nothing that names it was missed | [rename-checklist.md](references/rename-checklist.md) |
| Working on Windows: case-insensitive paths, CRLF after a scripted edit, the interpreter registry | [windows-traps.md](references/windows-traps.md) |

---

### When to activate

- Editing anything under a `.run/` directory or under `.idea/`
- Creating or repairing an IntelliJ or PyCharm run configuration
- A run configuration appears under Unknown, or its interpreter field comes up empty
- Module names in the project tree do not match the directories on disk, or the Gradle tool window shows duplicates
- Deciding which `.idea/` files belong in version control, or repairing a half-committed set
- Renaming a module, container or image, and keeping IDE-built image names in step with Compose

---

### When not to activate

- Writing the Dockerfile or the Compose file a run configuration points at, use `docker-patterns`
- Ignore patterns and staging discipline outside `.idea/`, use `git-workflow`
- The Gradle build itself, its version catalog and its plugins, use `build-dependency-management`
- Spring profiles and application configuration a run configuration activates, use `springboot-patterns`
- The human-facing setup section that tells a developer how to open the project, use `markdown-writer`

---

### Never guess an option name

The IDE reads a run configuration by matching each option name against the ones the platform knows, and it drops any
name it does not recognise. There is no error, no warning and no log line. The file on disk keeps the invented option
and the IDE behaves as if it was never written, so the configuration looks right in the editor and does nothing when
run. Copy a working example written by the same IDE version, or create the configuration once through the dialog and
read the XML the IDE wrote. Verifying costs a minute. Guessing cost three wrong attempts in one session.

Pass:

```xml
<option name="upForceRecreate" value="true" />
```

Fail:

```xml
<option name="commandLineOptions" value="--build --force-recreate" />
```

The failing form runs, and the stack it brings up is indistinguishable from a plain `up`. Every configuration type
with its verified XML is in [run-configurations.md](references/run-configurations.md).

---

### Commit what the IDE reads, ignore what a build tool regenerates

Gradle and Maven regenerate the module files on every import, so a committed copy coexists with the generated one and
the project tree shows every module twice, or worse, under a second name. The files nothing regenerates are the ones
to commit: the root module, `gradle.xml`, `misc.xml`, `vcs.xml`, `.name` and every run configuration. Watch for the
half-done state, where `modules.xml` is committed and the module files it points at are ignored: a fresh clone gets a
registry naming files that never arrive, and the IDE invents placeholder modules to satisfy it.

Pass:

```text
.idea/modules.xml lists .idea/pharmacy.iml only, and that file is committed beside it.
```

Fail:

```text
.idea/modules.xml lists 28 files under .idea/modules/, and .gitignore excludes that directory.
```

The per-file table, the vendor guidance behind it and the check-ignore verification are in
[version-control.md](references/version-control.md).

---

### Close the IDE before editing its files by hand

The IDE holds the module model, the interpreter registry and its Gradle import in memory and writes each of them back
on save or on exit. An edit made to `.idea/modules.xml` or to `jdk.table.xml` while the project is open is overwritten
without notice, and an IDE terminal session dies with the project. Close the project, edit, clear the import cache,
then reopen and read the module list back. The full procedure is in
[gradle-monorepo.md](references/gradle-monorepo.md).

---

### Related skills

- `docker-patterns` owns the Dockerfile and the Compose file the Docker run configurations point at
- `git-workflow` owns ignore patterns and staging discipline outside `.idea/`
- `build-dependency-management` owns the Gradle build the IDE imports
- `springboot-patterns` owns the profiles a Spring Boot run configuration activates
- `observability-and-logging` owns the scrape job and dashboard names the rename checklist walks
- `markdown-writer` owns the human-facing setup section that points a developer at `.run/`

---

### Checklist

- [ ] Every option name in a run configuration was copied from a working file or from XML the IDE wrote
- [ ] Every path inside a run configuration uses `$PROJECT_DIR$`, never an absolute path
- [ ] `.idea/modules.xml` lists only modules whose `.iml` is committed beside it
- [ ] `git check-ignore -v` confirmed each `.idea/` path in both directions
- [ ] Every `<module name="...">` in a run configuration names a module the IDE currently shows
- [ ] IDE `imageTag` values match the Compose `image` lines for the same services
- [ ] The IDE was closed before `.idea/` was edited by hand, and reopened cold afterwards
- [ ] After a rename, every item on the checklist was walked in order and the misses were fixed
