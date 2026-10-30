---
name: machine-health
description: 'Read-only health and configuration check of one Linux, macOS or Windows computer, writing a baseline into MACHINE.md on the first run and reporting drift on later runs: CPU, RAM, disks, errors, PATH, updates and devices. Use when the user says "check the health of this machine", "what drifted since last time" or "is this disk dying". Not for fixing a finding on Arch, use `arch-linux`.'
---

# Machine Health

A read-only health and configuration check for one computer, run after setup and again whenever the owner asks. The first run writes a dated baseline into the Health section of `MACHINE.md`. Every later run compares against that baseline and reports drift. The agent finds and reports. It fixes nothing on its own, it never elevates, and it hands every root command and every fix to the owner.

Linux commands were executed read-only on one CachyOS host with systemd and Plasma 6, and each one that ran says so. macOS and Windows commands were not executed and are marked UNVERIFIED wherever they appear.

| Task | Open |
|---|---|
| Where the Health section sits in `MACHINE.md`, the baseline and drift format, verdicts, the change log entry, the reply to the owner | [machine-md-format.md](references/machine-md-format.md) |
| CPU model, microcode, governor and power profile, temperatures, throttling | [cpu.md](references/cpu.md) |
| RAM modules, speed against rating and vendor support, mixed kits, channels, memory errors, memory tests | [memory.md](references/memory.md) |
| SMART and NVMe health, filesystem errors, free space, mount options, encryption | [storage.md](references/storage.md) |
| Failed units, coredumps, error logs, kernel warnings and taint | [system-errors.md](references/system-errors.md) |
| PATH duplicates, missing entries, shadowed binaries, which file sets what, where variables and zsh files belong, whether graphical applications see the terminal's variables | [paths-and-environment.md](references/paths-and-environment.md) |
| Pending and partial upgrades, `.pacnew` and friends, orphans, caches | [packages.md](references/packages.md) |
| GPU driver, display refresh, audio, network, firewall, time sync and the dual boot clock | [devices-and-network.md](references/devices-and-network.md) |
| Firewall, Secure Boot, disk encryption, pending security updates in one view | [security-baseline.md](references/security-baseline.md) |

---

### When to activate

- The machine was just set up or bootstrapped and the owner wants a health baseline
- The owner asks what changed, broke or drifted since the last check
- A crash, a slow boot, a freeze or a disk warning needs a structured look before anyone changes anything
- A question about whether RAM, a disk, the GPU driver or a display is running the way it should
- `MACHINE.md` exists and its Health section is missing or older than the owner wants
- Also covers CPU microcode, governor, temperatures and throttling, RAM speed against the module rating and the CPU vendor's supported speed, mixed kits, channels and memory errors, SMART and NVMe health, filesystem errors, free space, mount options, encryption, failed units, crashes and error logs, PATH duplicates, shadowed binaries and env file placement, pending updates, GPU driver, display refresh rate, audio, network, firewall, time sync, Secure Boot
- The user says "take a baseline", "is my RAM at the right speed", "why is PATH so long", "is the firewall on" or "how do I run a memory test"

---

### When not to activate

- Writing `MACHINE.md` from nothing, run `global/bootstrap-machine.prompt.md` from agent-standards first, then come back for the baseline
- Fixing a finding, which belongs to the owner, guided by `arch-linux`, `cachyos`, `windows` or `macos`
- Writing a script that automates these checks, use `bash` or `powershell`
- Auditing scheduled jobs, hooks and CI rather than the machine, use `automation-inventory`
- Reviewing application code for vulnerabilities, use `security-review`

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
2. Run the checks in the order of the table above, OS by OS, using only the commands marked for that OS.
3. Give each check a verdict from [machine-md-format.md](references/machine-md-format.md), and compare it with the baseline when one exists.
4. Write the baseline or the drift entry, update Needs root, add the change log entry.
5. Reply to the owner with the findings ordered by severity, each with its suggested fix handed over rather than applied.

---

### Related skills

- `arch-linux`, `cachyos`, `kde-plasma` own fixing what the Linux checks find
- `windows` owns fixing what the Windows checks find, including BitLocker, Fast Startup and the dual boot clock
- `macos` owns fixing what the macOS checks find
- `research` owns looking up and quoting the vendor limits the RAM and CPU checks compare against
- `automation-inventory` owns auditing the automations that run on the machine
- The `security-auditor` agent owns judging whether a security finding is acceptable

---

### Checklist

- [ ] `MACHINE.md` read, never-touch devices noted, owner rows left alone
- [ ] Every check run read-only, nothing installed, nothing repaired, nothing elevated
- [ ] Every root or elevated command written to Needs root with the row it fills
- [ ] Every vendor limit quoted with its URL and fetch date
- [ ] Every command not executed in this run marked UNVERIFIED
- [ ] On Linux with a systemd user session and zsh as the login shell: variables and PATH entries both graphical applications and terminals need live in `~/.config/environment.d/*.conf`, `~/.zshenv` only imports them, sets `ZDOTDIR` and deduplicates PATH, interactive-only setup sits in `.zshrc`, `~/.profile` holds nothing while zsh is the login shell, and the graphical session's environment matches the terminal's
- [ ] On Linux with a systemd user session and zsh as the login shell: zsh files live in `$ZDOTDIR`, `~/.config/zsh`, with `~/.zshenv` the only one left in the home directory
- [ ] Baseline written on the first run, drift against it on every later run
- [ ] Findings handed to the owner with evidence, fix and undo, none applied
- [ ] Change log entry added for the run
