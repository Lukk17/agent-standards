---
name: windows
description: 'Administering Windows 10 or 11 from an agent: winget and Chocolatey, PowerShell 7 against 5.1, the registry, services, scheduled tasks, WSL, Defender and UAC, BitLocker, dual boot, event logs, line endings and symlinks. Use when the user says "install this with winget", "set a registry value", "run this as admin" or "BitLocker recovery screen". Not for PowerShell modules, use `powershell`.'
---

# Windows Administration

How to change a Windows machine without surprising its owner: run PowerShell 7, install through winget before anything else, hand every elevated step to the owner, and never trip BitLocker recovery or corrupt a disk Linux shares. Windows behaves differently by edition, build and policy, so measure the machine before applying a recipe.

Written for Windows 10 and 11 with PowerShell 7, from Microsoft Learn pages. No command in this skill was executed. Facts checked read-only against a mounted Windows 11 disk say so, and every command is otherwise UNVERIFIED.

| Task | Open |
|---|---|
| Install, upgrade, export or remove software with winget, Chocolatey or Scoop | [package-managers.md](references/package-managers.md) |
| Choose between `pwsh` and `powershell.exe`, fix encoding or a missing cmdlet | [powershell-editions.md](references/powershell-editions.md) |
| Read or change a registry value, back one up | [registry.md](references/registry.md) |
| Inspect or change a service or a scheduled task | [services-and-tasks.md](references/services-and-tasks.md) |
| Configure WSL, move files between Windows and Linux, fix WSL performance | [wsl.md](references/wsl.md) |
| Elevate a command, UAC, sudo for Windows, Defender status and exclusions | [elevation-and-defender.md](references/elevation-and-defender.md) |
| BitLocker, Fast Startup, hibernation, dual boot with Linux, the clock offset | [bitlocker-and-dual-boot.md](references/bitlocker-and-dual-boot.md) |
| Read the System, Application or a service's event log | [event-logs.md](references/event-logs.md) |
| Long paths, line endings, case, symlinks, junctions, Developer Mode | [files-and-links.md](references/files-and-links.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`: the Windows edition and build, which package managers are installed, the BitLocker state of each volume, whether another operating system shares the disk, the projects folder, and the change log. Read it before acting. This skill holds no facts about any single machine. Discover with the read-only commands in the topic files and compare with `MACHINE.md`.

---

### When to activate

- Installing, upgrading or removing software on Windows
- Choosing which PowerShell runs a command, or a script that behaves differently in each
- Any change to the registry, a service, a scheduled task, Defender, UAC or BitLocker
- WSL configuration, or files that cross between Windows and a WSL distribution
- A dual boot machine: Fast Startup, hibernation, the shared EFI partition, the hardware clock
- Reading event logs to explain a failure
- Paths, line endings, symlinks or junctions on NTFS
- Also covers winget first, then Chocolatey, then the vendor installer, with Scoop only on request, PowerShell 7 (pwsh) preferred over Windows PowerShell 5.1, the registry, services, scheduled tasks, WSL, Microsoft Defender, UAC and elevation, sudo for Windows, BitLocker, Fast Startup and dual boot with Linux, event logs, file paths and line endings, symlinks, junctions and Developer Mode
- The user says "choco or winget", "why does this script fail in powershell.exe", "restart the service", "run this at logon", "WSL is slow on /mnt/c", "add a Defender exclusion", "Linux cannot mount the Windows partition", "the clock is wrong after booting Linux", "which event log" or "symlink needs admin"

---

### When not to activate

- Writing or reviewing a PowerShell script, module or Pester test, use `powershell`
- Work inside a WSL distribution once you are in Linux, use the Linux distribution's skill
- Windows Server roles such as Active Directory, IIS or Hyper-V clusters, which need their own documentation
- Fleet configuration across many hosts, use `ansible`

---

### Hard rules

1. Run PowerShell in PowerShell 7 (`pwsh`) when it is installed. When it is not, recommend that the owner install it with `winget install --id Microsoft.PowerShell -e --source winget` before anything else, and fall back to Windows PowerShell 5.1 (`powershell.exe`) only when the owner declines. Detection and the differences are in [powershell-editions.md](references/powershell-editions.md).
2. Name the shell for every command: `pwsh` for PowerShell 7, `powershell.exe` for Windows PowerShell 5.1, or `cmd`. A command that works in one can fail in the other.
3. Install software with winget first. Use Chocolatey only when winget has no package for it, and the vendor's own installer only when neither has it. Use Scoop only when the owner asks for it. An application already installed, or one `MACHINE.md` assigns to a manager, stays with that manager, and no application is installed through two. The order is set out in [package-managers.md](references/package-managers.md).
4. The agent does not elevate. A command that needs administrator rights goes to the owner, with what it changes, to run in an elevated terminal or through `sudo` where sudo for Windows is enabled. Never trigger a UAC prompt from the agent's own process.
5. Back up before a change: export the registry key, record the service start type, note the task definition, or create a restore point when the owner wants one.
6. Before any firmware, boot order, Secure Boot or bootloader change on a BitLocker machine, confirm the recovery key is saved somewhere other than the machine, and suspend BitLocker for the change.
7. Never weaken Defender, UAC or SmartScreen for convenience. An exclusion is scoped to one path the owner names, and recorded.
8. On a machine that dual boots, never write to an NTFS volume from Linux while Windows is hibernated or shut down with Fast Startup on.
9. Record every system change in the change log of `MACHINE.md`, with how to undo it.

---

### Related skills

- `powershell` owns how a PowerShell script or module is written and tested
- `bash` owns scripts run in Git Bash or WSL
- `arch-linux` and `cachyos` own the Linux side of a dual boot machine
- The `security-auditor` agent owns judging whether an exclusion, a policy change or a third party tool is acceptable
- `git-workflow` owns `core.autocrlf`, `.gitattributes` and `core.symlinks`, in its `references/git-config.md`

---

### Checklist

- [ ] `MACHINE.md` read, edition, build and installed package managers confirmed
- [ ] `pwsh` used, or its install recommended before any fallback to `powershell.exe`
- [ ] The shell named for every command handed over
- [ ] Software installed through winget, then Chocolatey, then the vendor installer, Scoop only on request
- [ ] Every elevated step handed to the owner, none run by the agent
- [ ] A backup or export taken before a registry, service or task change
- [ ] BitLocker recovery key confirmed saved before any boot level change
- [ ] Fast Startup state checked before Linux writes to a shared NTFS volume
- [ ] No security control weakened beyond one named, recorded exclusion
- [ ] The change and its undo recorded in the `MACHINE.md` change log
