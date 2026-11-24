---
name: machine-health
description: 'Read-only health check on Linux, macOS or Windows: a MACHINE.md baseline, then drift. Use when the user says "check the health of this machine" or "what drifted since last time". Not for Arch fixes, use `arch-linux`.'
metadata:
  version: "1.1.0"
---

# Machine Health

A read-only health and configuration check for one computer, run after setup and again whenever the owner asks. The first run writes a dated baseline into the Health section of `MACHINE.md`. Every later run compares against that baseline and reports drift. The agent fixes nothing on its own.

| Task | Open |
|---|---|
| The Health section of `MACHINE.md`: where it sits, the baseline and drift format, verdicts, the change log entry, the reply | [machine-md-format.md](references/machine-md-format.md) |
| The machine runs Linux: every check | [linux.md](references/linux.md) |
| The Linux package manager | [pacman.md](references/pacman.md) (Arch, CachyOS), [apt.md](references/apt.md) (Debian, Ubuntu), [dnf.md](references/dnf.md) (Fedora) |
| Linux with systemd and a zsh login shell: where variables and zsh files belong | [linux-zsh-environment.md](references/linux-zsh-environment.md) |
| The machine runs macOS: every check | [macos.md](references/macos.md) |
| The machine runs Windows: every check | [windows.md](references/windows.md) |
| Judging a value on any OS: RAM speed, temperature limits, refresh rate, the dual boot clock, security findings | [judging.md](references/judging.md) |
| Before sending the report | [checklist.md](references/checklist.md) |

---

### When not to activate

- Fixing a finding, which belongs to the owner, guided by `arch-linux`, `cachyos`, `windows` or `macos`
- Writing a script that automates these checks, use `bash` or `powershell`
- Auditing scheduled jobs, hooks and CI rather than the machine, use `automation-inventory`

---

### Hard rules

1. Read `MACHINE.md` first: the never-touch table, the owner rows, Known quirks and the last Health entry. Without it there is no baseline, so the run becomes the baseline.
2. Read-only. No install, no service change, no mount, no repair tool, no `fsck`, `chkdsk /f`, `ntfsfix`, `btrfs check --repair`, no cache cleaning and no package removal, even a dry run that writes state. A missing tool is a finding, not something to install.
3. Never run `sudo`, `doas`, `pkexec`, `runas`, an elevated PowerShell or anything that asks for a password. A check that needs root goes into the Needs root section as `needs: sudo <command>` or `needs: elevated <command>` with the row it fills.
4. A device in the never-touch table gets listing level only (`lsblk`, `Get-Disk`, `diskutil list`). No SMART query, no filesystem tool, no mount, even read-only.
5. Every value carries the command it came from and the date from the system clock. A command not executed on this OS in this run is reported as UNVERIFIED, never as a result.
6. A row whose Source is `owner` is never overwritten. When a measurement disagrees with it, the run records drift and leaves the row as it was.
7. A vendor limit, such as the CPU's supported memory speed or maximum temperature, is quoted from the vendor's page with its URL and fetch date. A remembered number is not a limit.
8. Report, never fix silently. Every finding goes to the owner with the evidence, the suggested command, what it changes and how to undo it. The owner decides.
9. No secret in the report: no key, passphrase, token, serial number or environment variable value. Variable names only.
10. Add a dated change log entry to `MACHINE.md` for every run, saying the run changed nothing on the system.

---

### Run order

1. Read `MACHINE.md` and note the OS, the never-touch devices and the date of the last Health entry.
2. Open only the file for the OS the machine runs, plus on Linux the file for its package manager, and run the checks in the order that file lists them.
3. Give each check a verdict from the `MACHINE.md` format file, by the value rules of the judging file, and compare it with the baseline when one exists.
4. Write the baseline or the drift entry, update Needs root, add the change log entry.
5. Reply to the owner with the findings ordered by severity, each with its suggested fix handed over rather than applied.
