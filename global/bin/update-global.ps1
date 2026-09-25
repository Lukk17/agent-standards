#Requires -Version 7.4
<#
.SYNOPSIS
    Updates the global agent-standards install in a home directory from the committed state of the repository.
.DESCRIPTION
    The hook scripts, the plugin and this updater are refreshed in full. Only the skills and subagents already
    installed are refreshed, and none is ever added. A file is removed only when the previously installed commit
    shipped it and the new one no longer does. Exits 1 when no install is found or a git step fails, 2 when a
    required command is missing.
.PARAMETER DryRun
    List what would change and write nothing.
.PARAMETER Source
    A local clone, read at its HEAD commit, or a URL to clone.
.PARAMETER HomeDir
    The home directory that holds the install.
.EXAMPLE
    pwsh -NoProfile -File ~/.agents/bin/update-global.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [ValidateNotNullOrEmpty()][string]$Source = 'https://github.com/Lukk17/agent-standards.git',
    [ValidateNotNullOrEmpty()][string]$HomeDir = $HOME
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$UpstreamPaths = @('.agents/hooks', '.agents/plugin', 'global/bin', '.agents/skills', '.agents/agents', '.claude/agents', '.codex/agents', '.github/agents')
$WiringFiles = @('.claude/settings.json', '.codex/config.toml', '.github/hooks/preflight.json', 'docs/GLOBAL_SETUP.md')
$SubagentTrees = @(
    @('.agents/agents', '.agents/agents'),
    @('.claude/agents', '.claude/agents'),
    @('.codex/agents', '.codex/agents'),
    @('.copilot/agents', '.github/agents')
)

$Counts = @{ update = 0; add = 0; remove = 0; unchanged = 0; keep = 0; skip = 0 }

function Exit-WithError([string]$Message, [int]$Code = 1) {
    [Console]::Error.WriteLine("update-global: $Message")
    exit $Code
}

function Test-GitCommand([string[]]$GitArgument) {
    $PSNativeCommandUseErrorActionPreference = $false
    & git @GitArgument 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Get-GitOutput([string[]]$GitArgument) {
    $PSNativeCommandUseErrorActionPreference = $false
    $lines = @(& git @GitArgument 2>$null)
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return , [string[]]$lines
}

function Get-OrdinalSorted([string[]]$Value) {
    $sorted = [string[]]@($Value)
    [Array]::Sort($sorted, [StringComparer]::Ordinal)
    return , $sorted
}

function Join-Relative([string]$Root, [string]$Relative) {
    return [IO.Path]::Combine($Root, $Relative.Replace('/', [IO.Path]::DirectorySeparatorChar))
}

function Get-RelativeFileList([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return , [string[]]@()
    }
    $files = @(Get-ChildItem -LiteralPath $Root -Recurse -File -Force | ForEach-Object {
            [IO.Path]::GetRelativePath($Root, $_.FullName).Replace([IO.Path]::DirectorySeparatorChar, '/')
        })
    return Get-OrdinalSorted -Value $files
}

function Get-VisibleNameList([string]$Root, [switch]$Directory) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return , [string[]]@()
    }
    $items = if ($Directory) { Get-ChildItem -LiteralPath $Root -Directory -Force } else { Get-ChildItem -LiteralPath $Root -File -Force }
    $names = @($items | Where-Object { -not $_.Name.StartsWith('.') } | ForEach-Object Name)
    return Get-OrdinalSorted -Value $names
}

function Write-Action([string]$Verb, [string]$Relative, [string]$Note = '') {
    $Counts[$Verb]++
    '{0,-7} ~/{1}{2}' -f $Verb, $Relative, $Note
}

function Copy-UpstreamFile([string]$UpstreamFile, [string]$Relative) {
    $target = Join-Relative $HomeDir $Relative

    if (Test-Path -LiteralPath $target -PathType Leaf) {
        if ((Get-FileHash -LiteralPath $UpstreamFile).Hash -eq (Get-FileHash -LiteralPath $target).Hash) {
            $Counts.unchanged++
            return
        }
        Write-Action -Verb 'update' -Relative $Relative
    }
    elseif (Test-Path -LiteralPath $target) {
        Write-Action -Verb 'skip' -Relative $Relative -Note ' (not a regular file, left alone)'
        return
    }
    else {
        Write-Action -Verb 'add' -Relative $Relative
    }

    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($target)) | Out-Null
        Copy-Item -LiteralPath $UpstreamFile -Destination $target -Force
    }
}

function Remove-InstalledFile {
    [CmdletBinding(SupportsShouldProcess)]
    param([string]$Target, [string]$Root)

    if (-not $PSCmdlet.ShouldProcess($Target, 'Remove')) {
        return
    }
    Remove-Item -LiteralPath $Target -Force
    $directory = [IO.Path]::GetDirectoryName($Target)
    while ($directory -ne $Root -and -not (Get-ChildItem -LiteralPath $directory -Force | Select-Object -First 1)) {
        Remove-Item -LiteralPath $directory
        $directory = [IO.Path]::GetDirectoryName($directory)
    }
}

function Sync-Tree([string]$UpstreamPrefix, [string]$HomePrefix) {
    $upstreamRoot = Join-Relative $script:Tree $UpstreamPrefix
    foreach ($relative in (Get-RelativeFileList $upstreamRoot)) {
        Copy-UpstreamFile (Join-Relative $upstreamRoot $relative) "$HomePrefix/$relative"
    }

    if (-not $script:PreviousKnown) {
        return
    }
    $prefix = "$UpstreamPrefix/"
    $homeRoot = Join-Relative $HomeDir $HomePrefix
    foreach ($path in $script:PreviousFiles) {
        if (-not $path.StartsWith($prefix, [StringComparison]::Ordinal)) {
            continue
        }
        $relative = $path.Substring($prefix.Length)
        $target = Join-Relative $homeRoot $relative
        if ((Test-Path -LiteralPath (Join-Relative $upstreamRoot $relative)) -or -not (Test-Path -LiteralPath $target -PathType Leaf)) {
            continue
        }
        Write-Action -Verb 'remove' -Relative "$HomePrefix/$relative"
        if (-not $DryRun) {
            Remove-InstalledFile -Target $target -Root $homeRoot
        }
    }
}

function Test-ShippedBefore([string]$Path) {
    return $script:PreviousKnown -and $script:PreviousSet.Contains($Path)
}

function Test-ShippedBeforeUnder([string]$Prefix) {
    if (-not $script:PreviousKnown) {
        return $false
    }
    foreach ($path in $script:PreviousFiles) {
        if ($path.StartsWith("$Prefix/", [StringComparison]::Ordinal)) {
            return $true
        }
    }
    return $false
}

function Sync-InstalledSkill {
    foreach ($name in (Get-VisibleNameList (Join-Relative $HomeDir '.agents/skills') -Directory)) {
        $relative = ".agents/skills/$name"
        if (Test-Path -LiteralPath (Join-Relative $script:Tree $relative) -PathType Container) {
            Sync-Tree $relative $relative
        }
        elseif (Test-ShippedBeforeUnder $relative) {
            Write-Action -Verb 'keep' -Relative $relative -Note ' (removed upstream, left in place)'
        }
        else {
            Write-Action -Verb 'skip' -Relative $relative -Note ' (not an upstream skill)'
        }
    }
}

function Sync-InstalledSubagent {
    foreach ($pair in $SubagentTrees) {
        $homeTree = $pair[0]
        $upstreamTree = $pair[1]
        foreach ($name in (Get-VisibleNameList (Join-Relative $HomeDir $homeTree))) {
            $upstreamFile = Join-Relative $script:Tree "$upstreamTree/$name"
            if (Test-Path -LiteralPath $upstreamFile -PathType Leaf) {
                Copy-UpstreamFile $upstreamFile "$homeTree/$name"
            }
            elseif (Test-ShippedBefore "$upstreamTree/$name") {
                Write-Action -Verb 'keep' -Relative "$homeTree/$name" -Note ' (removed upstream, left in place)'
            }
            else {
                Write-Action -Verb 'skip' -Relative "$homeTree/$name" -Note ' (not an upstream subagent)'
            }
        }
    }
}

function Write-WiringReport {
    if (-not $script:PreviousKnown) {
        'Hook wiring: the previously installed commit is unknown here, so files removed upstream were not detected'
        'and wiring changes could not be listed. Compare the per-agent blocks in docs/GLOBAL_SETUP.md by hand.'
        return
    }
    $changed = Get-GitOutput -GitArgument (@('-C', $script:Repo, 'diff', '--name-only', $script:PreviousCommit, $script:Commit, '--') + $WiringFiles)
    if ($null -eq $changed) {
        Exit-WithError "git diff failed between $($script:PreviousCommit) and $($script:Commit)"
    }
    if ($changed.Count -eq 0) {
        "Hook wiring: unchanged upstream since $($script:PreviousCommit)."
        return
    }
    "Hook wiring changed upstream since $($script:PreviousCommit). Merge it into your own files by hand, from docs/GLOBAL_SETUP.md:"
    foreach ($file in $changed) {
        "  $file"
    }
    "See the change with: git diff $($script:PreviousCommit) $($script:Commit) -- $($WiringFiles -join ' ')"
}

function Write-CommitRecord {
    if ($DryRun) {
        "Would record $($script:Commit) in ~/.agents/.upstream-commit."
        return
    }
    [IO.File]::WriteAllText((Join-Relative $HomeDir '.agents/.upstream-commit'), "$($script:Commit)`n")
    "Recorded $($script:Commit) in ~/.agents/.upstream-commit."
}

function Write-Summary {
    $leftAlone = " Left alone: $($Counts.keep) removed upstream, $($Counts.skip) not from upstream."
    if ($DryRun) {
        "Dry run, nothing was written. Would update $($Counts.update), add $($Counts.add), remove $($Counts.remove). Unchanged $($Counts.unchanged).$leftAlone"
    }
    else {
        "Updated $($Counts.update), added $($Counts.add), removed $($Counts.remove). Unchanged $($Counts.unchanged).$leftAlone"
    }
}

if (-not (Get-Command git -CommandType Application -ErrorAction SilentlyContinue)) {
    Exit-WithError 'required command not found: git' 2
}

if (-not (Test-Path -LiteralPath (Join-Relative $HomeDir '.agents') -PathType Container)) {
    Exit-WithError "no global install at $(Join-Relative $HomeDir '.agents'); install it first, see docs/GLOBAL_SETUP.md"
}

$workspace = Join-Path ([IO.Path]::GetTempPath()) ('agent-standards-update-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $workspace | Out-Null

try {
    if (Test-Path -LiteralPath $Source -PathType Container) {
        $script:Repo = (Resolve-Path -LiteralPath $Source).ProviderPath
    }
    else {
        $script:Repo = Join-Path $workspace 'clone'
        if (-not (Test-GitCommand -GitArgument @('clone', '--quiet', '--filter=blob:none', $Source, $script:Repo))) {
            Exit-WithError "could not clone $Source"
        }
    }

    $head = Get-GitOutput -GitArgument @('-C', $script:Repo, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}')
    if ($null -eq $head -or $head.Count -ne 1) {
        Exit-WithError "no committed HEAD in $Source"
    }
    $script:Commit = $head[0].Trim()

    $present = @($UpstreamPaths | Where-Object { Test-GitCommand -GitArgument @('-C', $script:Repo, 'cat-file', '-e', "$($script:Commit):$_") })
    if ($present -notcontains '.agents/hooks') {
        Exit-WithError "$Source holds no .agents/hooks at $($script:Commit), so it is not an agent-standards repository"
    }

    $archive = Join-Path $workspace 'upstream.zip'
    $script:Tree = Join-Path $workspace 'tree'
    if (-not (Test-GitCommand -GitArgument (@('-C', $script:Repo, 'archive', '--format=zip', '-o', $archive, $script:Commit, '--') + $present))) {
        Exit-WithError "git archive failed at $($script:Commit)"
    }
    Expand-Archive -LiteralPath $archive -DestinationPath $script:Tree

    $script:PreviousCommit = ''
    $script:PreviousKnown = $false
    $script:PreviousFiles = [string[]]@()
    $record = Join-Relative $HomeDir '.agents/.upstream-commit'
    if (Test-Path -LiteralPath $record -PathType Leaf) {
        $script:PreviousCommit = ([IO.File]::ReadAllText($record)) -replace '\s', ''
    }
    if ($script:PreviousCommit -and (Test-GitCommand -GitArgument @('-C', $script:Repo, 'cat-file', '-e', "$($script:PreviousCommit)^{commit}"))) {
        $listed = Get-GitOutput -GitArgument (@('-C', $script:Repo, '-c', 'core.quotePath=false', 'ls-tree', '-r', '--name-only', $script:PreviousCommit, '--') + $UpstreamPaths)
        if ($null -eq $listed) {
            Exit-WithError "git ls-tree failed at $($script:PreviousCommit)"
        }
        $script:PreviousFiles = $listed
        $script:PreviousKnown = $true
    }
    $script:PreviousSet = [Collections.Generic.HashSet[string]]::new($script:PreviousFiles, [StringComparer]::Ordinal)

    if ($DryRun) { 'agent-standards global update, dry run' } else { 'agent-standards global update' }
    "Source: $Source at $($script:Commit)"
    "Home:   $HomeDir"

    Sync-Tree '.agents/hooks' '.agents/hooks'
    Sync-Tree '.agents/plugin' '.agents/plugin'
    Sync-Tree 'global/bin' '.agents/bin'
    Sync-InstalledSkill
    Sync-InstalledSubagent
    Write-WiringReport
    Write-CommitRecord
    Write-Summary
}
finally {
    Remove-Item -LiteralPath $workspace -Recurse -Force -ErrorAction SilentlyContinue
}
