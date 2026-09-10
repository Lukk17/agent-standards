# Version Control for .idea

Which files under `.idea/` are committed, which are ignored, why each one falls where it does, and what the half-done
state looks like from the next machine. Load this file when writing the ignore rules for a JetBrains project or when
a committed `modules.xml` has produced duplicate modules on somebody else's clone. The rules live in
[SKILL.md](../SKILL.md).

---

### The rule behind the table

Commit a file if the IDE reads it and nothing regenerates it. Ignore a file if a build tool import rewrites it, or if
it holds one developer's state. A file that is regenerated and also committed exists twice from the IDE's point of
view, and two definitions of one module is exactly how a project tree ends up showing a module under two names.

---

### Commit and ignore, per file

| Path | Commit or ignore | Why |
|---|---|---|
| `.idea/.name` | commit | The title the IDE shows. It overrides the checkout folder name, so it has to travel with the project |
| `.idea/gradle.xml` | commit | Which Gradle builds are linked and how each is imported. Hand-authored, nothing regenerates it |
| `.idea/misc.xml` | commit | Project JDK, language level and the external storage switch. Hand-authored |
| `.idea/vcs.xml` | commit | Maps the project root to its VCS. Without it a fresh clone has no VCS integration until somebody clicks |
| `.idea/modules.xml` | commit, root module entry only | The module registry. It may name only modules whose `.iml` is committed beside it |
| `.idea/<project>.iml` | commit | The root module that shows the whole tree. Hand-authored, nothing regenerates it |
| `.idea/runConfigurations/` | commit | Shared run configurations in the older location |
| every `.run/` directory | commit | Shared run configurations, one file each, at the root and inside modules |
| `.idea/modules/` | ignore | The `.iml` files Gradle import generates, one per imported module, rewritten on every sync |
| `.idea/compiler.xml` | ignore | Annotation processor and bytecode settings the import derives from the build |
| `.idea/libraries/` | ignore | Library descriptors the import derives from the dependency graph |
| `.idea/workspace.xml` | ignore | One developer's open editors, tool window layout and local history |
| `.idea/shelf/` | ignore | One developer's shelved changes |
| `.idea/dataSources*` | ignore | Database connections, which can carry credentials |
| plugin-personal files | ignore | `aws.xml`, `sonarlint.xml`, `git_toolbox_*.xml`, `developer-tools.xml` and the like, per-machine plugin state |

An `.iml` for a Python module is the one file the table does not name, and it goes the other way: nothing regenerates
it, so it is committed. Since a blanket ignore of `*.iml` is the normal starting point, each Python module file needs
its own negation entry.

---

### What JetBrains says

The vendor page is
[How to manage projects under Version Control Systems](https://intellij-support.jetbrains.com/hc/en-us/articles/206544839),
read on 2026-09-09. It lists `workspace.xml`, `usage.statistics.xml` and the `shelf` directory as user-specific, and
under items to exclude from sharing it says:

```text
.iml files and .idea/modules.xml file for the Gradle or Maven based projects since these files will be generated on import
```

The same list names `XML files under .idea/libraries in case they are generated from Gradle or Maven project`. The
table above follows that page, with one refinement: `modules.xml` is committed here because it carries the
hand-authored root module, and it is kept clean of every generated entry so the vendor's reason for excluding it
does not apply.

---

### The half-done state, as it happened

A monorepo committed `.idea/modules.xml` listing 28 `.iml` files under `.idea/modules/`, and `.gitignore` excluded
that directory. On the next machine IntelliJ read the registry, found no file behind any of the 28 entries, and
created a placeholder module for each missing file. The Gradle import then ran, found each of its module names
already taken by a module it had not created, and de-duplicated by prefixing the Gradle group, so
`pha-pharma-messaging.main` gained a twin named `com.revdevs.pha-pharma.pha-pharma-messaging.main`. Every Java
module showed twice, once empty and once real.

JetBrains has the same diagnosis on record. In
[IDEA-263842](https://youtrack.jetbrains.com/issue/IDEA-263842), open, a JetBrains developer wrote on 2021-03-09:

```text
Looks like it happens b/c the old module iml files are not properly loaded and are ignored by the IDE and it creates new module files and tries de-duplicate them which lead to module names renaming with the name containing the groupID.
```

The de-duplication order is in the platform source, in
[ModuleNameGenerator.kt](https://github.com/JetBrains/intellij-community/blob/master/platform/external-system-impl/src/com/intellij/openapi/externalSystem/service/project/nameGenerator/ModuleNameGenerator.kt),
which concatenates three generators from the same package: `SimpleNameGenerator` offers the bare name and then
`group` plus delimiter plus name, `PathNameGenerator` offers up to three parent directory names prefixed to it, and
`NumericNameGenerator` offers `name~1` through `name~5`. The first candidate not already taken wins, which is why a
placeholder holding the bare name produces the group-prefixed twin and not a `~1` suffix.

Either commit both `modules.xml` and every file it names, or commit neither. The root-module pattern in
[gradle-monorepo.md](gradle-monorepo.md) is how a committed `modules.xml` stays honest.

---

### External storage does not keep modules.xml quiet

`<component name="ExternalStorageConfigurationManager" enabled="true" />` in `.idea/misc.xml` moves the imported
module definitions out of the project into the IDE system directory, under
`projects/<name>.<hash>/external_build_system/`. That is the setting behind the Store generated project files
externally checkbox, and it is why a fresh clone has no `.idea/modules/` at all.

Even so, IntelliJ appends an entry to `.idea/modules.xml` for any imported module that gains a custom content root,
source root, exclude or facet, and writes that fragment as an `AdditionalModuleElements` component into
`.idea/modules/<name>.iml`. The usual trigger is the annotation processor output folder the IDE's own compiler adds
to a module after a build. The mechanism is
[IJPL-8604](https://youtrack.jetbrains.com/issue/IJPL-8604), fixed in 2023, whose description says:

```text
Custom content roots, source roots, excludes are saved into the separate AdditionalModuleElements component of the iml file.
```

So a tracked `modules.xml` shows local noise after builds, and those appended entries must never be staged. Review
the diff of `.idea/modules.xml` before every commit that touches `.idea/`, and stage the root module line only.

---

### Verify per path rather than trusting the pattern

A negation rule in `.gitignore` is easy to write one directory too wide or one character off, and the IDE will not
tell you. Check the exact paths in both directions.

A file you intend to track returns nothing and exits non-zero:

```bash
git check-ignore -v .idea/pharmacy.iml
```

A file you still want ignored is still matched, so a broad negation has not quietly reopened the generated module
files:

```bash
git check-ignore -v .idea/modules/pha-pharma.pha-pharma-app.main.iml
```

Run both after every edit to the ignore rules, and read the rule the second command prints back rather than just
its exit code, because the match may come from a different line than the one you meant.
