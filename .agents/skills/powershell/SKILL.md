---
name: powershell
description: 'PowerShell 7 script standards: strict errors, advanced functions, validation, modules, Pester. Use when the user says "write a PowerShell script" or "add Pester tests for this module". Not for POSIX shell, use `bash`.'
metadata:
  version: "1.1.0"
---

# PowerShell Standards

How a PowerShell script fails loudly, validates its inputs at the boundary, and stays testable. The defaults are the problem: PowerShell continues after most errors and ignores a native command's exit code unless told otherwise.

Written for PowerShell 7.6 LTS, Pester 6 and PSScriptAnalyzer. Declare the floor with `#Requires -Version 7.6`.

---

### When not to activate

- Writing POSIX shell scripts, use `bash`.
- Configuring Windows hosts at fleet scale, use `ansible`.
- Choosing exception types and error-handling architecture, use `coding-standards`.

---

### Rules

1. Stop on the first error: `$ErrorActionPreference = 'Stop'` and `$PSNativeCommandUseErrorActionPreference = $true` at the top of every script, so a failing native command is a terminating error. Never silence one with `2>$null`.
2. Wrap every filesystem, network, and external API call in `try` / `catch` / `finally`, and cast explicitly rather than relying on implicit conversion.
3. Write advanced functions with `[CmdletBinding()]`, never loose script blocks.
4. Anything that mutates state declares `SupportsShouldProcess` and guards the mutation with `$PSCmdlet.ShouldProcess(...)`, so a dry run actually skips the change.
5. Put each constraint on the parameter as a validation attribute, not in a runtime null check.
6. Reusable code is a module: a `.psm1` implementation and a `.psd1` manifest, public functions one per file under `Public/`, helpers under `Private/`, tests under `Tests/`. The manifest exports a named list, never `'*'`.
7. Use the right stream: `Write-Verbose` for diagnostics, `Write-Warning` for a recoverable issue, `Write-Error` for a non-terminating error, `throw` for a terminating one. `Write-Host` never appears in library or module code.
8. Never hold a password or token as a plain `[string]`. Use `[SecureString]` or `[PSCredential]`, read it at runtime, and hand it to an external tool through the environment, never the command line.
9. Lint in CI with zero findings, and suppress a rule only with a stated justification, never by excluding it.
10. Test every module, mock what it calls, verify the calls, and keep expensive shared setup out of the per-test block.
11. Guard Windows-only cmdlets with `$IsWindows` / `$IsLinux`, and build every path with `Join-Path` or `[System.IO.Path]::Combine()`.
12. A long-running service started from PowerShell prints its readiness banner right before the main loop or `Start-Process`, with each probe bounded and only the marker shown.
13. Comment-based help follows "Doc Comments" in `coding-standards`, with one carve-out: a function exported from a module always carries `.SYNOPSIS`, one `.PARAMETER` per parameter and one `.EXAMPLE`, because `Get-Help` renders it.

---

### Reference files

| Open this | When |
| --- | --- |
| [rules-and-examples.md](references/rules-and-examples.md) | A rule above needs its Pass and Fail example, its reasoning or the full comment-based help block. |
| [module-layout.md](references/module-layout.md) | Writing an advanced function or laying out a new module. |
| [psscriptanalyzer.md](references/psscriptanalyzer.md) | Wiring PSScriptAnalyzer into CI, clearing its findings, or suppressing one. |
| [pester.md](references/pester.md) | Writing Pester tests, or moving a suite to Pester 6. |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job. |
| [checklist.md](references/checklist.md) | Before calling a script or a module done. |
