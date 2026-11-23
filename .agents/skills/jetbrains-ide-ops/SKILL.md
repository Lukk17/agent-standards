---
name: jetbrains-ide-ops
description: 'JetBrains IDE monorepo files: run configurations, `.idea/` commits, Gradle modules, renames. Use when the user says "add a run configuration" or "which .idea files do we commit". Not for Compose, use `docker-patterns`.'
metadata:
  version: "1.1.0"
---

# JetBrains IDE Ops

How IntelliJ IDEA and PyCharm project files behave in a monorepo of several independent builds: which files are authored and which are generated, what a run configuration has to say to actually run, and what a rename has to touch so the IDE, Compose and monitoring keep naming the same thing. Everything here was read out of live projects rather than out of the dialog, because the dialog hides the half that goes wrong.

Written for IntelliJ IDEA on Windows 11. The XML shapes are stable across releases, and the cache directory under `%LOCALAPPDATA%` is the part that moves with the version.

| Task | Open |
|---|---|
| Creating or repairing a run configuration, or one shows as Unknown or with an empty interpreter | [run-configurations.md](references/run-configurations.md) |
| Deciding which `.idea/` files are committed, or a committed `modules.xml` has gone wrong on another machine | [version-control.md](references/version-control.md) |
| Linking several Gradle builds under one root, module naming, per-source-set import, reopening after a hand edit | [gradle-monorepo.md](references/gradle-monorepo.md) |
| Renaming a module, a service or an image, and checking nothing that names it was missed | [rename-checklist.md](references/rename-checklist.md) |
| Working on Windows: case-insensitive paths, CRLF after a scripted edit, the interpreter registry | [windows-traps.md](references/windows-traps.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before calling a change to `.run/` or `.idea/` done | [checklist.md](references/checklist.md) |

---

### When not to activate

- Writing the Dockerfile or the Compose file a run configuration points at, use `docker-patterns`
- Ignore patterns and staging discipline outside `.idea/`, use `git-workflow`
- The Gradle build itself, its version catalog and its plugins, use `build-dependency-management`

---

### Rules

1. Never guess an option name. The IDE drops any option name it does not recognise, with no error, no warning and no log line, so the configuration looks right in the editor and does nothing when run. Copy a working example written by the same IDE version, or create the configuration once through the dialog and read the XML the IDE wrote.
2. Commit what the IDE reads and ignore what a build tool regenerates. The files nothing regenerates are the ones to commit: the root module, `gradle.xml`, `misc.xml`, `vcs.xml`, `.name` and every run configuration. Never commit a `modules.xml` that points at ignored module files.
3. Close the IDE before editing its files by hand. The IDE holds the module model, the interpreter registry and its Gradle import in memory and writes each of them back on save or on exit, so an edit made while the project is open is overwritten without notice. Close the project, edit, clear the import cache, then reopen and read the module list back.
