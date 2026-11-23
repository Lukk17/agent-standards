---
name: windows
description: 'Administering Windows: winget, PowerShell 7, the registry, WSL, Defender, BitLocker, dual boot. Use when the user says "install this with winget" or "run this as admin". Not for PowerShell modules, use `powershell`.'
metadata:
  version: "1.1.0"
---

# Windows Administration

How to change a Windows machine without surprising its owner. Windows behaves differently by edition, build and policy, so measure the machine before applying a recipe.

Written for Windows 10 and 11 with PowerShell 7, from Microsoft Learn pages. No command in this skill was executed. Facts checked read-only against a mounted Windows 11 disk say so, and every command is otherwise UNVERIFIED.

| Task | Open |
|---|---|
| Install, upgrade, export or remove software with winget, Chocolatey or Scoop | [package-managers.md](references/package-managers.md) |
| Choose between `pwsh` and `powershell.exe`, detect or install PowerShell 7, fix encoding or a missing cmdlet | [powershell-editions.md](references/powershell-editions.md) |
| Read or change a registry value, back one up | [registry.md](references/registry.md) |
| Inspect or change a service or a scheduled task | [services-and-tasks.md](references/services-and-tasks.md) |
| Configure WSL, move files between Windows and Linux, fix WSL performance | [wsl.md](references/wsl.md) |
| Elevate a command, UAC, sudo for Windows, Defender status and exclusions | [elevation-and-defender.md](references/elevation-and-defender.md) |
| BitLocker, Fast Startup, hibernation, dual boot with Linux, the clock offset | [bitlocker-and-dual-boot.md](references/bitlocker-and-dual-boot.md) |
| Read an event log | [event-logs.md](references/event-logs.md) |
| Long paths, line endings, case, symlinks, junctions, Developer Mode | [files-and-links.md](references/files-and-links.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Report a Windows change as done | [checklist.md](references/checklist.md) |

---

### Machine facts

Machine-specific facts live in `MACHINE.md` next to the global `AGENTS.md`. Read it before acting. This skill holds no facts about any single machine.

For this skill they are the Windows edition and build, the installed package managers, the BitLocker state of each volume, a second operating system on the disk, the projects folder, and the change log. Discover with the read-only commands in the topic files and compare with `MACHINE.md`.

---

### When not to activate

- Writing or reviewing a PowerShell script, module or Pester test, use `powershell`
- Fleet configuration across many hosts, use `ansible`
- The Linux side of a dual boot machine, use `arch-linux` or `cachyos`

---

### Hard rules

1. Run PowerShell in PowerShell 7 (`pwsh`) when it is installed. When it is not, recommend that the owner install it before anything else, and fall back to Windows PowerShell 5.1 (`powershell.exe`) only when the owner declines.
2. Name the shell for every command: `pwsh` for PowerShell 7, `powershell.exe` for Windows PowerShell 5.1, or `cmd`. A command that works in one can fail in the other.
3. Install software with winget first, then Chocolatey, then the vendor's own installer, and with Scoop only when the owner asks for it. An application already installed, or one `MACHINE.md` assigns to a manager, stays with that manager, and no application is installed through two.
4. The agent does not elevate and never triggers a UAC prompt from its own process. A command that needs administrator rights goes to the owner with what it changes.
5. Back up before a change: export the registry key, record the service start type, note the task definition, or create a restore point when the owner wants one.
6. Before any firmware, boot order, Secure Boot or bootloader change on a BitLocker machine, confirm the recovery key is saved somewhere other than the machine, and suspend BitLocker for the change.
7. Never weaken Defender, UAC or SmartScreen for convenience. An exclusion is scoped to one path the owner names, and recorded.
8. On a machine that dual boots, never write to an NTFS volume from Linux while Windows is hibernated or shut down with Fast Startup on.
9. Record every system change in the change log of `MACHINE.md`, with how to undo it.
