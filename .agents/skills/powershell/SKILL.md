---
name: powershell
description: PowerShell 7 scripting standards for strict error handling, advanced functions, parameter validation, module layout, secret handling, PSScriptAnalyzer and Pester 6. Use when the user says "write a PowerShell script for this", "my script ignores when git fails", "turn this into a proper cmdlet" or "add Pester tests for this module". Not for POSIX shell scripting, use `bash`.
---

# PowerShell Standards

How a PowerShell script fails loudly, validates its inputs at the boundary, and stays testable. The defaults are the problem: PowerShell continues after most errors and ignores a native command's exit code unless told otherwise.

Written for PowerShell 7.6 LTS, Pester 6 and PSScriptAnalyzer. Declare the floor with `#Requires -Version 7.6`.

| Task | Open |
|---|---|
| The Pass and Fail example and the reasoning behind any rule below, and a full comment-based help block | [references/rules-and-examples.md](references/rules-and-examples.md) |
| Writing an advanced function or laying out a new module, with the reasoning behind each block | [references/module-layout.md](references/module-layout.md) |
| The readiness banner a PowerShell-run service prints when it comes up | `references/startup-readiness-log.md` in the `observability-and-logging` skill |

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

### Rules

1. Stop on the first error: `$ErrorActionPreference = 'Stop'` and `$PSNativeCommandUseErrorActionPreference = $true` at the top of every script, so a failing `git` or `robocopy` is a terminating error rather than a line of red text. Never silence one with `2>$null`.
2. Wrap every filesystem, network, and external API call in `try` / `catch` / `finally`, and cast explicitly (`[int]`, `[string]`) rather than relying on implicit conversion.
3. Write advanced functions with `[CmdletBinding()]`, which gives `-Verbose`, `-Debug`, `-WhatIf` and `-Confirm` for free, never loose script blocks.
4. Anything that mutates state declares `SupportsShouldProcess` and guards the mutation with `$PSCmdlet.ShouldProcess(...)`, so a dry run actually skips the change.
5. Put each constraint on the parameter, not in a runtime null check: `[ValidateNotNullOrEmpty()]` for required strings, `[ValidateRange(min, max)]` for numeric bounds, `[ValidateSet(...)]` for enumerated values, `[ValidatePattern('^regex$')]` for format-constrained strings.
6. Reusable code is a module: a `.psm1` implementation and a `.psd1` manifest, public functions one per file under `Public/`, helpers under `Private/`, Pester tests under `Tests/`.
7. The manifest exports a named list (`FunctionsToExport = @(...)`), never `'*'`, so an internal rename never breaks a consumer.
8. Use the right stream: `Write-Verbose` for diagnostics, `Write-Warning` for a recoverable issue, `Write-Error` for a non-terminating error, `throw` for a terminating one. `Write-Host` writes to the information stream, not the pipeline, so it never appears in library or module code.
9. Never hold a password or token as a plain `[string]`. Use `[SecureString]` or `[PSCredential]`, read it from an environment variable or a secrets vault at runtime, and hand it to an external tool through the environment, never the command line, where it shows in the process list.
10. Run PSScriptAnalyzer in CI with the PSGallery ruleset, `-EnableExit` and zero findings. Suppress a rule only with `[Diagnostics.CodeAnalysis.SuppressMessageAttribute]` plus a justification, never `-ExcludeRule`.
11. Structure Pester tests with `Describe` / `Context` / `It`, mock with `Mock` and verify with `Should -Invoke`, and put shared setup in `BeforeAll` / `AfterAll` rather than repeating expensive work in `BeforeEach`.
12. Pester 6 allows one of each setup and teardown block per `Describe` or `Context` and throws on a duplicate, and it removed `Assert-MockCalled`. Classic `Should -Be` keeps working, and the newer `Should-*` assertions are optional.
13. Guard Windows-only cmdlets with `$IsWindows` / `$IsLinux` (use `Get-CimInstance`, never `Get-WmiObject`), and build every path with `Join-Path` or `[System.IO.Path]::Combine()`.
14. A PowerShell-run long-running service (scheduled task, service wrapper, polling daemon) prints the readiness banner from `observability-and-logging` with a here-string right before the main loop or `Start-Process`. Probe with `-TimeoutSec 2` inside `try` / `catch` and surface only the marker.
15. The PowerShell 7 console host defaults to UTF-8 and renders the banner's box-drawing characters. Legacy `powershell.exe` needs `[Console]::OutputEncoding = [Text.Encoding]::UTF8` set once before printing.

---

### Comment-Based Help

Comment-based help follows "Doc Comments" in `coding-standards`, so private helpers and script-local functions carry none. The PowerShell delta is one carve-out: help on a function exported from a module is machine consumed, because `Get-Help` renders it, so an exported function always carries `.SYNOPSIS`, one `.PARAMETER` per parameter and one `.EXAMPLE` for the common invocation, even where the names already say it. Keep each `.PARAMETER` to one line, spent on units, a valid range, or who owns the argument afterwards wherever one applies. Add `.OUTPUTS` when the emitted type is non-obvious, and name every terminating error a caller can catch under `.NOTES`, since nothing in the signature declares it.

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
