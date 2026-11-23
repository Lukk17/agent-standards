# Scope

Companion reference for the [machine-health](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Read-only health and configuration check of one Linux, macOS or Windows computer, writing a baseline into MACHINE.md on the first run and reporting drift on later runs: CPU, RAM, disks, errors, PATH, updates and devices.

- The machine was just set up and the owner wants a health baseline
- The owner asks what changed, broke or drifted since the last check
- A crash, a slow boot, a freeze or a disk warning needs a structured look first
- A question about whether RAM, a disk, the GPU driver or a display is running the way it should
- `MACHINE.md` exists and its Health section is missing or older than the owner wants
- Also covers CPU microcode, governor, temperatures and throttling, RAM speed against the module rating and the CPU vendor's supported speed, mixed kits, channels and memory errors, SMART and NVMe health, filesystem errors, free space, mount options, encryption, failed units, crashes and error logs, PATH duplicates, shadowed binaries and env file placement, pending updates, GPU driver, display refresh rate, audio, network, firewall, time sync, Secure Boot
- The user says "check the health of this machine", "what drifted since last time", "is this disk dying", "take a baseline", "is my RAM at the right speed", "why is PATH so long", "is the firewall on" or "how do I run a memory test"

---

### When not to activate

- Writing `MACHINE.md` from nothing, run `global/bootstrap-machine.prompt.md` from agent-standards first, then come back for the baseline
- Fixing a finding, which belongs to the owner, guided by `arch-linux`, `cachyos`, `windows` or `macos`
- Writing a script that automates these checks, use `bash` or `powershell`
- Auditing scheduled jobs, hooks and CI rather than the machine, use `automation-inventory`
- Reviewing code for vulnerabilities, use `application-security-review`

---

### Related skills

- `arch-linux`, `cachyos`, `kde-plasma` own fixing what the Linux checks find
- `windows` owns fixing what the Windows checks find, including BitLocker, Fast Startup and the dual boot clock
- `macos` owns fixing what the macOS checks find
- `research` owns looking up and quoting the vendor limits the RAM and CPU checks compare against
- `automation-inventory` owns auditing the automations that run on the machine
- The `security-auditor` agent owns judging whether a security finding is acceptable
