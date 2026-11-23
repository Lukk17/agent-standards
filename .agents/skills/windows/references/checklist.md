# Windows Administration Checklist

Walk it before a Windows change is reported as done.

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
