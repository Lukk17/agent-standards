# Paths, Line Endings, Symlinks and Junctions

Read this when a path is too long, a file has the wrong line endings, a link cannot be created, or a repository's symlinks arrive as text files. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Path length

From Microsoft Learn, "Maximum Path Length Limitation": "the maximum length for a path is MAX_PATH, which is defined as 260 characters." Starting in Windows 10 version 1607 the limit can be lifted, but "two conditions must be met. A registry value must be set, and the application manifest must include the `longPathAware` element." The value is `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem` `LongPathsEnabled`, set to `1`, and "a reboot might be required".

1. Enabling the value helps only programs that declare themselves long path aware. Git has its own switch, `git config core.longpaths true`.
2. The cheap fix is a shorter root: clone into `C:\src\<repo>` rather than deep inside the profile.
3. Read the current value with `Get-ItemPropertyValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled`. Setting it is the owner's elevated step, see [registry.md](registry.md).

---

### Names and case

NTFS is case-insensitive by default, so `Readme.md` and `README.md` are one file and a repository holding both breaks on checkout. Names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1` and `LPT1` are reserved in every directory, with or without an extension, and a trailing dot or space is stripped. A file Linux created with such a name cannot be opened from Windows tools.

---

### Line endings

Windows tools write CRLF, Linux tools expect LF. A shell script with CRLF fails in bash with `$'\r': command not found`.

1. Let the repository decide, through `.gitattributes`, for example `* text=auto eol=lf` and `*.ps1 text eol=crlf` where the project wants that. The `git-workflow` skill owns the policy.
2. `core.autocrlf` is a per-machine guess. Read it with `git config --show-origin --get core.autocrlf` before blaming a file.
3. Check a file's endings from Git Bash or WSL with `file <path>`, which reports "with CRLF line terminators".
4. A PowerShell 5.1 redirect writes UTF-16LE, which looks like a binary file to Linux tools, see [powershell-editions.md](powershell-editions.md).

---

### Symlinks, junctions and Developer Mode

| Link | Needs | Points at | Notes |
|---|---|---|---|
| Symbolic link | administrator rights, or Developer Mode on | a file or a directory, local or remote, relative or absolute | what Git creates when `core.symlinks` is true |
| Junction | nothing beyond write access | a directory on a local volume, absolute path | `mklink /J` in `cmd`, or `New-Item -ItemType Junction` |
| Hard link | nothing beyond write access | a file on the same volume | `mklink /H`, or `New-Item -ItemType HardLink` |

The `CreateSymbolicLinkW` reference describes the flag `SYMBOLIC_LINK_FLAG_ALLOW_UNPRIVILEGED_CREATE`: "Specify this flag to allow creation of symbolic links when the process is not elevated. Developer Mode must first be enabled on the machine before this option will function." Developer Mode is in Settings, System, Advanced, For developers, and the Learn page notes "Enabling Developer mode requires administrator access".

Create a directory symlink in `pwsh`:

```powershell
New-Item -ItemType SymbolicLink -Path '<link>' -Target '<target>'
```

A repository that ships symlinks checks them out as plain text files holding the target path unless Developer Mode is on and `core.symlinks` is true when the clone happens:

```powershell
git config --global core.symlinks true
```

A clone made without it keeps the text files. Fix the setting, then re-checkout the affected paths or clone again.

Before deleting a directory that might be a link, check with `Get-Item <path> | Select-Object LinkType, Target`. Delete a directory link with `cmd /c rmdir <link>`, never with a recursive delete, so the target's contents cannot be followed and removed. UNVERIFIED across PowerShell versions.
