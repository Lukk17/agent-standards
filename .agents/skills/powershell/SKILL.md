---
name: powershell
description: PowerShell 7+ scripting standards for error handling, advanced functions, module structure, secrets handling, and Pester v5 testing.
origin: project-standards
---

# PowerShell Standards

## Core Execution Directives

- Treat all LLM generated scripts, cmdlets, and object pipelines as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every script generation task.
- Append a Zero-Trust directive demanding mandatory web searches for current PowerShell module documentation.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every cmdlet parameter and error handling structure provided.
- Mandate direct, working links to the official documentation used to ground the code.

---

## Strict Mode and Error Handling

- Alter the default error behavior to stop execution on the first error rather than silently continuing.
- Require the agent to set the global error action preference at the beginning of every script:

```powershell
$ErrorActionPreference = 'Stop'
```

- Enforce termination for native command failures (e.g., `git`, `robocopy`) in PowerShell 7.3 and newer:
  - Ref: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables

```powershell
$PSNativeCommandUseErrorActionPreference = $true
```

---

## Defensive Scripting Practices

- Mandate the use of `try`, `catch`, and `finally` blocks for all operations that interact with the filesystem, network, or external APIs to gracefully handle terminating errors.
- Avoid implicit data type conversions. Explicitly cast variables (e.g., `[int]`, `[string]`) to prevent runtime type mismatch errors.
- Validate all required parameters at script entry using `#Requires` statements and parameter validation attributes; print a usage message and exit on invalid input.

---

## Advanced Function Template

Every reusable script block must be written as an advanced function:

```powershell
function Invoke-MyOperation {
    [CmdletBinding(SupportsShouldProcess)]
    param (
        [Parameter(Mandatory, ValueFromPipeline)]
        [ValidateNotNullOrEmpty()]
        [string]$InputPath,

        [Parameter()]
        [ValidateRange(1, 100)]
        [int]$MaxRetries = 3
    )

    begin {
        Write-Verbose "Starting Invoke-MyOperation"
    }

    process {
        if ($PSCmdlet.ShouldProcess($InputPath, 'Process')) {
            # operation logic
        }
    }

    end {
        Write-Verbose "Completed Invoke-MyOperation"
    }
}
```

- Always use `[CmdletBinding()]` on functions to enable `-Verbose`, `-Debug`, `-WhatIf`, and `-Confirm` support.
- Use `SupportsShouldProcess` for any function that modifies state; guard mutations with `$PSCmdlet.ShouldProcess(...)`.

---

## Parameter Validation

Use validation attributes on every parameter that has constraints:

- `[ValidateNotNullOrEmpty()]` for required strings.
- `[ValidateRange(min, max)]` for numeric bounds.
- `[ValidateSet('Value1', 'Value2')]` for enumerated values.
- `[ValidatePattern('^regex$')]` for format-constrained strings.

Mark mandatory parameters with `[Parameter(Mandatory)]`; do not rely on runtime null checks for required inputs.

---

## Module Structure

Organise reusable code as PowerShell modules with a `.psm1` implementation file and a `.psd1` manifest. Export only public functions in the module manifest (`FunctionsToExport`); keep internal helpers unexported.

Use the following module directory layout:

```
MyModule/
  MyModule.psd1      # Module manifest
  MyModule.psm1      # Dot-sources private functions, exports public ones
  Public/            # Exported functions (one file per function)
  Private/           # Internal helpers
  Tests/             # Pester test files
```

---

## Logging Pattern

- Use `Write-Verbose` for diagnostic messages (visible with `-Verbose`).
- Use `Write-Warning` for recoverable issues that do not stop execution.
- Use `Write-Error` for non-terminating errors; use `throw` for terminating errors.
- Never use `Write-Host` in library/module code; it bypasses the pipeline and cannot be captured. Use `Write-Output` for data and `Write-Verbose`/`Write-Information` for status messages.

---

## Secret Handling

- Never store passwords or tokens as plain `[string]`; use `[SecureString]` or `[PSCredential]`.
- Pass secrets to external tools via environment variables or credential objects, not as command-line arguments (they appear in process lists).
- Read secrets from environment variables or a secrets vault (Azure Key Vault, HashiCorp Vault via the respective PowerShell module) at runtime.

---

## PSScriptAnalyzer and Testing

- Run **PSScriptAnalyzer** on all scripts and modules in CI with the `PSGallery` ruleset; zero warnings/errors policy.
  - Suppress individual rules only with `[Diagnostics.CodeAnalysis.SuppressMessageAttribute]` accompanied by a justification comment.
- Write tests using **Pester v5**:
  - Structure tests with `Describe` / `Context` / `It` blocks.
  - Mock dependencies with `Mock` and verify calls with `Should -Invoke`.
  - Use `BeforeAll` / `AfterAll` for setup and teardown; do not use `BeforeEach` for expensive setup that can be shared.

---

## Cross-Platform Compatibility (PowerShell 7+)

- Target **PowerShell 7.x** (LTS) for all new scripts; document the minimum required version in the script header with `#Requires -Version 7.2`.
- Avoid Windows-only cmdlets (`Get-WmiObject`, `Get-EventLog`) without an OS guard:

```powershell
if ($IsWindows) { ... } elseif ($IsLinux) { ... } elseif ($IsMacOS) { ... }
```

- Use `[System.IO.Path]::Combine()` or `Join-Path` for all path construction to ensure cross-platform path separators.
