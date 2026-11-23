# Scope

Companion reference for the [windows](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Administering Windows 10 or 11 from an agent: winget and Chocolatey, PowerShell 7 against 5.1, the registry, services, scheduled tasks, WSL, Defender and UAC, BitLocker, dual boot, event logs, line endings and symlinks.

- Installing, upgrading or removing software on Windows
- Choosing which PowerShell runs a command, or a script that behaves differently in each
- Any change to the registry, a service, a scheduled task, Defender, UAC or BitLocker
- WSL configuration, or files that cross between Windows and a WSL distribution
- A dual boot machine: Fast Startup, hibernation, the shared EFI partition, the hardware clock
- Reading event logs to explain a failure
- Paths, line endings, symlinks or junctions on NTFS
- Also covers winget first, then Chocolatey, then the vendor installer, with Scoop only on request, PowerShell 7 (pwsh) preferred over Windows PowerShell 5.1, the registry, services, scheduled tasks, WSL, Microsoft Defender, UAC and elevation, sudo for Windows, BitLocker, Fast Startup and dual boot with Linux, event logs, file paths and line endings, symlinks, junctions and Developer Mode
- The user says "install this with winget", "set a registry value", "run this as admin", "BitLocker recovery screen", "choco or winget", "why does this script fail in powershell.exe", "restart the service", "run this at logon", "WSL is slow on /mnt/c", "add a Defender exclusion", "Linux cannot mount the Windows partition", "the clock is wrong after booting Linux", "which event log" or "symlink needs admin"

---

### When not to activate

- Writing or reviewing a PowerShell script, module or Pester test, use `powershell`
- Work inside a WSL distribution once you are in Linux, use the Linux distribution's skill
- Windows Server roles such as Active Directory, IIS or Hyper-V clusters, which need their own documentation
- Fleet configuration across many hosts, use `ansible`

---

### Related skills

- `powershell` owns how a PowerShell script or module is written and tested
- `bash` owns scripts run in Git Bash or WSL
- `arch-linux` and `cachyos` own the Linux side of a dual boot machine
- The `security-auditor` agent owns judging whether an exclusion, a policy change or a third party tool is acceptable
- `git-workflow` owns `core.autocrlf`, `.gitattributes` and `core.symlinks`, in its `references/git-config.md`
