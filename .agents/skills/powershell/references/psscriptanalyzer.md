# PSScriptAnalyzer

The lint gate for every script and module. Open this when wiring PSScriptAnalyzer into CI, clearing its findings, or suppressing one. The rule it serves is in [SKILL.md](../SKILL.md).

---

### Run it in CI with zero findings

Run PSScriptAnalyzer in CI with the PSGallery ruleset and a zero-finding policy. Suppress a rule only with
`[Diagnostics.CodeAnalysis.SuppressMessageAttribute]` plus a justification.

Pass:

```powershell
Invoke-ScriptAnalyzer -Path ./src -Recurse -EnableExit
```

Fail:

```powershell
Invoke-ScriptAnalyzer -Path ./src -ExcludeRule PSAvoidUsingPlainTextForPassword
```

Pass `-EnableExit`, and never drop a rule with `-ExcludeRule`.
