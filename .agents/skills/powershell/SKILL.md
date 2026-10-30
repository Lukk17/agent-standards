---
name: powershell
description: PowerShell 7 scripting standards for strict error handling, advanced functions, parameter validation, module layout, secret handling, PSScriptAnalyzer and Pester 6. Use when the user says "write a PowerShell script for this", "my script ignores when git fails", "turn this into a proper cmdlet" or "add Pester tests for this module". Not for POSIX shell scripting, use `bash`.
---

# PowerShell Standards

How a PowerShell script fails loudly, validates its inputs at the boundary, and stays testable. The defaults are the
problem: PowerShell continues after most errors and ignores a native command's exit code unless told otherwise.

Written for PowerShell 7.6 LTS, Pester 6 and PSScriptAnalyzer. Declare the floor with `#Requires -Version 7.6`.

---

### When to activate

- Writing or reviewing a `.ps1`, `.psm1`, or `.psd1` file.
- Turning a loose script into an advanced function or a module.
- Fixing a script that keeps running after a cmdlet or a native command failed.
- Adding parameter validation, `-WhatIf` support, or comment-based help.
- Writing Pester tests or clearing PSScriptAnalyzer findings.
- Making a Windows-only script run on Linux or macOS.

---

### When not to activate

- Writing POSIX shell scripts, use `bash`.
- Writing the CI workflow YAML that invokes the script, use `deployment-patterns`.
- Writing the container image the script runs in, use `docker-patterns`.
- Configuring Windows hosts at fleet scale, use `ansible`.
- Choosing exception types and error-handling architecture, use `coding-standards`.

---

### Stop on the first error

Set the preference at the top of every script, and turn on native command error propagation so a failing `git` or
`robocopy` is a failure rather than a line of red text.

Pass:

```powershell
$ErrorActionPreference = 'Stop'
```

Also set this, so a non-zero exit code from a native executable becomes a terminating error:

```powershell
$PSNativeCommandUseErrorActionPreference = $true
```

Fail:

```powershell
git push 2>$null
```

- Ref: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables
- Wrap every filesystem, network, and external API call in `try` / `catch` / `finally`.
- Cast explicitly (`[int]`, `[string]`) rather than relying on implicit conversion.

---

### Write advanced functions, not loose script blocks

`[CmdletBinding()]` gives you `-Verbose`, `-Debug`, `-WhatIf`, and `-Confirm` for free. Anything that mutates state
declares `SupportsShouldProcess` and guards the mutation with `$PSCmdlet.ShouldProcess(...)`, so a dry run actually
skips the change instead of reporting one it made anyway. The full template and the `begin` / `process` / `end`
reasoning live in [references/module-layout.md](references/module-layout.md).

Pass:

```powershell
[CmdletBinding(SupportsShouldProcess)] param([Parameter(Mandatory)][string]$Path)
```

Fail, a destructive function with no binding and no guard:

```powershell
function Remove-Backups { param($Path) Remove-Item -Recurse -Force $Path }
```

---

### Validate parameters with attributes

Put the constraint on the parameter, not in a runtime null check further down.

Pass:

```powershell
[Parameter(Mandatory)][ValidateSet('dev', 'staging', 'prod')][string]$Environment
```

Fail:

```powershell
if (-not $Environment) { throw "Environment is required" }
```

Use `[ValidateNotNullOrEmpty()]` for required strings, `[ValidateRange(min, max)]` for numeric bounds,
`[ValidateSet(...)]` for enumerated values, and `[ValidatePattern('^regex$')]` for format-constrained strings.

---

### Module structure

Organise reusable code as a module with a `.psm1` implementation and a `.psd1` manifest, public functions under
`Public/` one file each, internal helpers under `Private/`, and Pester tests under `Tests/`. Export a named list, so
an internal rename never becomes a breaking change for a consumer. The layout is set out in
[references/module-layout.md](references/module-layout.md).

Pass:

```powershell
FunctionsToExport = @('Get-BackupSet', 'New-BackupSet')
```

Fail:

```powershell
FunctionsToExport = '*'
```

---

### Comment-Based Help

Comment-based help follows "Doc Comments" in `coding-standards`, so private helpers and script-local functions carry
none. The PowerShell delta is one carve-out: help on a function exported from a module is machine consumed, because
`Get-Help` renders it, so an exported function always carries `.SYNOPSIS`, one `.PARAMETER` per parameter and one
`.EXAMPLE` for the common invocation, even where the names already say it. Keep each `.PARAMETER` to one line, and spend it on units, a valid range, or
who owns the argument afterwards wherever one of those applies. Add `.OUTPUTS` when the emitted type is
non-obvious, and name every terminating error a caller can catch under `.NOTES`, since nothing in the signature
declares it.

```powershell
function Get-BackupSet {
    <#
    .SYNOPSIS
        Returns the backup sets kept for a vault, newest first.
    .PARAMETER VaultName
        Vault to read, which must already exist, since the function never creates one.
    .PARAMETER RetentionDays
        Age cut-off in days, values above 3650 are rejected.
    .EXAMPLE
        Get-BackupSet -VaultName prod -RetentionDays 30
    #>
}
```

---

### Logging through the right stream

`Write-Verbose` for diagnostics, `Write-Warning` for a recoverable issue, `Write-Error` for a non-terminating error,
`throw` for a terminating one. `Write-Host` writes to the information stream for display, not to the output pipeline,
so a caller cannot consume what it prints as data. It never appears in library or module code.

Pass:

```powershell
Write-Verbose "Rotated $($removed.Count) backup sets"
```

Fail:

```powershell
Write-Host "Rotated $($removed.Count) backup sets"
```

---

### Secret handling

Never hold a password or token as a plain `[string]`. Use `[SecureString]` or `[PSCredential]`, read the value from
an environment variable or a secrets vault at runtime, and pass it to an external tool through the environment rather
than the command line, where it shows up in the process list.

Pass:

```powershell
$credential = Get-Secret -Name 'deploy-account' -Vault 'CorpVault'
```

Fail:

```powershell
& terraform apply -var "token=$PlainTextToken"
```

---

### PSScriptAnalyzer and Pester 6

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

Structure tests with `Describe` / `Context` / `It`, mock dependencies with `Mock` and verify with `Should -Invoke`,
and use `BeforeAll` / `AfterAll` for shared setup rather than repeating expensive work in `BeforeEach`. Pester 6
allows one of each setup and teardown block per `Describe` or `Context` and throws on a duplicate, and it removed
`Assert-MockCalled`, so `Should -Invoke` is the call-count check. Classic `Should -Be` keeps working, and the newer
`Should-*` assertions are optional.

---

### Cross-platform rules

Guard Windows-only cmdlets and build every path with `Join-Path` or `[System.IO.Path]::Combine()` so the separator is
never hardcoded.

Pass:

```powershell
if ($IsWindows) { Get-CimInstance Win32_OperatingSystem } elseif ($IsLinux) { Get-Content /etc/os-release }
```

Fail:

```powershell
Get-WmiObject Win32_OperatingSystem
```

---

### Startup readiness log

For a PowerShell-orchestrated long-running service (a scheduled task, a service wrapper, a polling daemon), print the
readiness banner with a here-string right before the main loop or `Start-Process`. The universal convention, the ANSI
Shadow banner, the section order, and the probe rules live in
the `observability-and-logging` skill, in its `references/startup-readiness-log.md`.

The PowerShell 7 console host defaults to UTF-8 and renders the box-drawing characters natively. Legacy
`powershell.exe` needs `[Console]::OutputEncoding = [Text.Encoding]::UTF8` set once before printing.

Pass, a bounded probe that swallows the exception and surfaces only a marker:

```powershell
try { $r = Invoke-WebRequest $Url -TimeoutSec 2 -ErrorAction Stop; "$Url [Connected]" } catch { "$Url [FAILED]" }
```

Fail:

```powershell
Invoke-WebRequest $Url
```

---

### Reference files

| Open this | For |
|---|---|
| [references/module-layout.md](references/module-layout.md) | Writing an advanced function or laying out a new module, with the reasoning behind each block |
| `references/startup-readiness-log.md` in the `observability-and-logging` skill | Writing the readiness banner a PowerShell-run service prints when it comes up |

---

### Related skills

- `bash` for the same standards on POSIX shells.
- `observability-and-logging` for the readiness banner and the logging conventions it follows.
- `deployment-patterns` for the CI workflow that runs PSScriptAnalyzer and Pester.
- `docker-patterns` when the script runs inside a container.
- `ansible` when the work is fleet configuration rather than a one-host script.

---

### Checklist

- [ ] `$ErrorActionPreference = 'Stop'` and `$PSNativeCommandUseErrorActionPreference = $true` at the top.
- [ ] `#Requires -Version` declares the minimum PowerShell version.
- [ ] Every reusable block is an advanced function with `[CmdletBinding()]`.
- [ ] State-changing functions declare `SupportsShouldProcess` and guard with `ShouldProcess`.
- [ ] Constraints live in parameter attributes, not runtime null checks.
- [ ] Module manifest exports a named list, never `*`.
- [ ] No `Write-Host` in module or library code.
- [ ] Secrets are `[SecureString]` or `[PSCredential]`, never a command-line argument.
- [ ] PSScriptAnalyzer passes with zero findings, every suppression justified.
- [ ] Pester 6 tests exist and mocks are verified with `Should -Invoke`.
- [ ] Paths built with `Join-Path`, Windows-only cmdlets guarded by `$IsWindows`.
