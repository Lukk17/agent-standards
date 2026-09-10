# Windows Traps

Three things that go wrong on a Windows machine when JetBrains project files are edited from a shell, each one found
the hard way. Load this file before scripting any change to `.idea/` or `.run/` on Windows, and when an interpreter
registered by hand has vanished. The rules live in [SKILL.md](../SKILL.md).

---

### The filesystem is case-insensitive

NTFS matches paths without regard to case, so a command that names a file in the wrong case still finds the file.
Deleting a stale `.idea/Pharmacy.iml` after creating `.idea/pharmacy.iml` deletes the file that was just created,
because to the filesystem they are one file. Git, meanwhile, tracks the two spellings as different paths, so the
index and the working tree can disagree about which one exists.

Before deleting or renaming anything under `.idea/`, list the directory and read the case that is actually on disk.

```bash
ls -la .idea
```

Rename a file whose only change is its case through git, so the index follows the working tree.

```bash
git mv .idea/Pharmacy.iml .idea/pharmacy.iml
```

---

### A scripted edit can flip a file to CRLF

A tool that rewrites a `.run.xml` on Windows may write it back with CRLF line endings, while `.gitattributes`
enforces LF for the repository. The result is a diff that touches every line of the file, or a normalisation warning
on the next commit, over a change that was one attribute. Check the line endings after any scripted edit of a run
configuration, and before staging it.

```bash
file .run/*.run.xml
```

A file reported with `CRLF line terminators` needs converting back before it is staged.

```bash
dos2unix ".run/compose [rebuild recreate].run.xml"
```

Prefer the editor tool that preserves the file's existing line endings over a script that rewrites the whole file,
and quote any filename that carries spaces or brackets, which run configuration names usually do.

---

### The interpreter registry is written on exit

The IDE holds its interpreter registry, `jdk.table.xml` under the IDE configuration directory, in memory and writes
the whole file out when it exits. Editing that file while the IDE is running achieves nothing, and the edit
disappears on close. Registering an interpreter through the IDE takes about a minute and is the route that survives.

This is the registry a Python run configuration's `SDK_NAME` refers to, which is why that configuration resolves only
after each machine has registered the interpreter once, as described in
[run-configurations.md](run-configurations.md). The Gradle import cache behaves the same way and is handled by the
cold reopen in [gradle-monorepo.md](gradle-monorepo.md).
