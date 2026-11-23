# PowerShell Checklist

Run it before calling a script or a module done. The rules behind each item are in [SKILL.md](../SKILL.md).

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
