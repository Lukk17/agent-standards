# Companion OpenSpec schema

The methodology in [SKILL.md](../SKILL.md) works on its own. A project that already uses
[OpenSpec](https://github.com/Fission-AI/OpenSpec) can install the matching schema on top of it to get the slash-command
lifecycle, with an artifact chain that mirrors the methodology: proposal, then test spec, then tasks template, then run.

The schema also scaffolds the `e2e/` tree and its four README files on first use, which is the manual step described in
the Directory layout section of the skill.

---

### Install from the consumer project root

Clone the schema repository into a temporary directory.

```bash
git clone --depth 1 https://github.com/Lukk17/openspec-schemas /tmp/lukk17-schemas
```

Copy the schema into the project's OpenSpec directory.

```bash
cp -r /tmp/lukk17-schemas/e2e-runbooks openspec/schemas/
```

Remove the clone.

```bash
rm -rf /tmp/lukk17-schemas
```

Windows equivalents, in PowerShell.

```powershell
git clone --depth 1 https://github.com/Lukk17/openspec-schemas $env:TEMP\lukk17-schemas
```

```powershell
Copy-Item -Recurse $env:TEMP\lukk17-schemas\e2e-runbooks openspec\schemas\
```

```powershell
Remove-Item -Recurse -Force $env:TEMP\lukk17-schemas
```

---

### Select the schema

Either pass it per change, or make it the default. Per change:

```text
/opsx:new --schema e2e-runbooks
```

As the project default, set this key in `openspec/config.yaml`:

```yaml
default_schema: e2e-runbooks
```

---

### What the schema adds

| Without the schema | With the schema |
| --- | --- |
| Scaffold the `e2e/` tree and its four READMEs by hand | Created on first use, with canonical README text |
| Create the spec, template and run file by hand from the section list | Generated from the artifact chain, sections pre-filled |
| Track sweeps by convention | Tracked as OpenSpec changes with the usual lifecycle commands |

Nothing in the skill depends on the schema. It is a lifecycle wrapper over the same three-file triple, for projects
already invested in OpenSpec.
