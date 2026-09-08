# Advanced function and module layout

The full advanced-function template and the module directory shape, with the reasoning behind each block. The rules
that make these mandatory live in [SKILL.md](../SKILL.md).

---

### Advanced function template

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

`[CmdletBinding()]` is what turns a function into something that honours `-Verbose`, `-Debug`, `-ErrorAction`,
`-WhatIf`, and `-Confirm`. Without it those parameters do not exist and a caller has no way to dry-run the function.

`SupportsShouldProcess` plus the `$PSCmdlet.ShouldProcess(...)` guard is the contract for anything that mutates
state. The guard returns false under `-WhatIf`, so the mutation is skipped and PowerShell prints what would have
happened. A function that declares support and then mutates outside the guard is worse than one that never declared
it, because the dry run lies.

`begin` / `process` / `end` matter the moment a parameter carries `ValueFromPipeline`. Work placed directly in the
function body, or in `begin`, runs once. Work in `process` runs per pipeline item. Putting the per-item work in the
wrong block is the usual cause of a function that only ever processes the last object it was piped.

---

### Module directory layout

```text
MyModule/
  MyModule.psd1      # Module manifest
  MyModule.psm1      # Dot-sources private functions, exports public ones
  Public/            # Exported functions (one file per function)
  Private/           # Internal helpers
  Tests/             # Pester test files
```

One file per public function keeps the diff for a change scoped to the function that changed, and it lets the
manifest's `FunctionsToExport` list be read as the module's actual public surface.

`FunctionsToExport` takes an explicit array, never `'*'`. A wildcard exports every helper the module happens to
define, which turns an internal rename into a breaking change for consumers, and it defeats the command
auto-discovery cache PowerShell builds from the manifest.

`Private/` holds everything a consumer must not call. Those functions carry no comment-based help, because nothing
renders it, and they are free to change shape between releases.
