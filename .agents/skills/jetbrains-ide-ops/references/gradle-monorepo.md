# Gradle Monorepo Layout

How one IntelliJ project shows a whole repository that holds several independent Gradle builds, what decides the
module names the IDE shows, and how to reopen the project after `.idea/` was edited outside the IDE. Load this file
when linking a new build, when module names do not match the directories, or when the Gradle tool window shows a
module twice. The rules live in [SKILL.md](../SKILL.md).

---

### The root module shows the whole tree

A Gradle import only shows the directories the linked builds own. A monorepo also holds contracts, docs, scripts, a
Flutter client and infrastructure that no build claims, and without a module over them they are simply absent from
the Project tree. The fix is one plain module whose content root is the repository directory.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<module type="JAVA_MODULE" version="4">
  <component name="NewModuleRootManager" inherit-compiler-output="true">
    <exclude-output />
    <content url="file://$MODULE_DIR$">
      <excludeFolder url="file://$MODULE_DIR$/pha-client/build" />
    </content>
    <orderEntry type="inheritedJdk" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>
```

The file is `.idea/<project>.iml`, and `$MODULE_DIR$` for a file directly inside `.idea/` resolves to the project
directory, which is what makes the content root the repository. It is the only entry in `.idea/modules.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://$PROJECT_DIR$/.idea/pharmacy.iml" filepath="$PROJECT_DIR$/.idea/pharmacy.iml" />
    </modules>
  </component>
</project>
```

Nothing regenerates either file, so both are committed, and a `modules.xml` that names only this module never points
at a file another machine lacks. Exclude build output directories of the tools that have no IDE plugin here, such as
a Flutter `build/`, or the root module indexes them.

---

### Each build is linked separately

`.idea/gradle.xml` carries one `GradleProjectSettings` block per independent build, each naming its
`externalProjectPath` and the set of module directories it produces. IntelliJ imports every linked build on first
open, so a fresh clone needs no hand step: the root module gives the tree, the linked builds give the Java modules.

```xml
<GradleProjectSettings>
  <option name="externalProjectPath" value="$PROJECT_DIR$/pha-cloud/gateway" />
  <option name="resolveModulePerSourceSet" value="false" />
  <option name="modules">
    <set>
      <option value="$PROJECT_DIR$/pha-cloud/gateway" />
    </set>
  </option>
</GradleProjectSettings>
```

Do not open a sub-build directory as its own project to get at its modules. Open the monorepo root, and add a block
here when a build joins the repository.

---

### Name the module and the project identically, in lowercase

`.idea/.name` holds the title the IDE shows in the window and in the recent projects list, and it overrides the
checkout folder name whatever that folder is called. Name it in lowercase and give the root module the same name, so
`.idea/.name` reads `pharmacy` and the module file is `.idea/pharmacy.iml`. A capitalised module beside a lowercase
project name is two spellings of one thing, and on a case-insensitive filesystem it is also a trap, described in
[windows-traps.md](windows-traps.md).

---

### One module per Gradle project or one per source set

`resolveModulePerSourceSet` in each `GradleProjectSettings` block decides whether a Gradle project imports as one IDE
module or as a `.main` and `.test` pair, plus one module per custom source set. The setting was removed from the UI
in 2019.2 and is still honoured when written by hand into `.idea/gradle.xml`. JetBrains calls it deprecated and
unmaintained: in [IDEA-222172](https://youtrack.jetbrains.com/issue/IDEA-222172), open, a JetBrains developer wrote
on 2019-09-07:

```text
Separate module per source set is the only supported option now. The previous option can be enabled but it will no longer be maintained
```

and on 2020-12-31 in the same issue:

```text
the support for this option is no longer maintained and there are no plans to improve such set ups
```

With `false` the IDE shows `pha-pharma.pha-pharma-drug` instead of `pha-pharma.pha-pharma-drug.main` and
`pha-pharma.pha-pharma-drug.test`. The cost is that the main and test classpaths merge into one module, and a custom
source set such as `testFixtures` loses its own dependencies, which is
[IDEA-235646](https://youtrack.jetbrains.com/issue/IDEA-235646), answered and closed: a dependency declared only on
a custom configuration is reported as an unresolved import while the Gradle build itself succeeds.

This is a per-project choice, not a default. Take the flat names when the repository has no custom source sets that
carry dependencies of their own and the shorter module list is worth more than a separate test classpath. Keep the
default when any module declares a `testFixtures` or an integration test source set with its own dependencies.

---

### What to check after switching

Every module name changes when the setting flips, and the IDE rewrites only the run configurations it happened to
have open. A Spring Boot run configuration carries `<module name="...">`, and one pinned to `<project>.main` breaks
silently the day that module disappears. Grep every run configuration and compare each name against the module list
the IDE shows after the reimport.

```bash
grep -rn "<module name=" --include=*.run.xml .
```

The Spring Boot form and why it carries a module name are in [run-configurations.md](run-configurations.md).

---

### Three names describe one module

Three names describe the same module, and the IDE gets confusing when they diverge: the directory on disk, the
Gradle root project name in that build's `settings.gradle.kts`, and the module entry the IDE shows. A repository can
hold `apps/inventory-api` on disk with `rootProject.name` set to `inventory-api` while the IDE shows
`inventory-service_main`, which leaves someone hunting the project tree for a module under a name no directory
carries. Keep all three equal, and when one moves, move the other two in the same change.

Two display quirks explain most of the remaining confusion.

IntelliJ appends a bracketed path to a module that was imported as a separate Gradle project, so a module shows in
the tree as `name [apps.name]`. Setting `useQualifiedModuleNames` to `false` inside that build's
`GradleProjectSettings` block removes the suffix without restructuring the build.

Docker Desktop strips the Compose project name prefix from a container name when it renders a row. With a project
named `ascend`, a container named `ascend-agent` appears as just `agent`, while a sibling named `audio-scribe`
appears in full because its name does not begin with the project prefix. Nothing is misconfigured when that happens,
and it confuses people badly.

---

### Reopen cold after editing .idea by hand

The IDE holds the module model in memory and writes it back over `.idea/modules.xml` on save or on exit, so an edit
made while the project is open is lost. It also caches its Gradle import outside the project directory, so a module
renamed on disk lingers in the Gradle tool window under its old name and the panel shows duplicates even though every
file in the project is clean. Do not edit the cache directory, which is rewritten on exit for the same reason as the
interpreter registry in [windows-traps.md](windows-traps.md). Walk this order instead.

1. Close the project in the IDE first. An IDE terminal session dies with the project, so run the edit from a shell
   outside the IDE.
2. Make the edit to `.idea/` and verify it with the check-ignore commands in
   [version-control.md](version-control.md).
3. Delete `external_build_system` under the project's cache directory, so the reopen imports every Gradle module
   fresh, exactly like a fresh clone. On Windows the path is
   `%LOCALAPPDATA%\JetBrains\<IDE version>\projects\<name>.<hash>\external_build_system`, where `<IDE version>` is a
   directory such as `IntelliJIdea2026.2` and `<name>.<hash>` is the lowercase project name followed by a short hash.
4. Reopen the project and read the module list back from the Project Structure dialog or from the Gradle tool
   window, and compare it against every `<module name="...">` in the run configurations.

Invalidate caches and restart clears more than step 3 does and takes longer, so reach for it only when the module
list is still wrong after a cold reopen.
