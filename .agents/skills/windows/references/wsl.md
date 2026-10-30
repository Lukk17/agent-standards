# WSL

Read this before configuring WSL, when files cross between Windows and a distribution, or when WSL is slow. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Discover

```powershell
wsl.exe --version
```

```powershell
wsl.exe --list --verbose
```

```powershell
wsl.exe --status
```

`--list --verbose` shows each distribution, its state and whether it runs as WSL 1 or 2. If `wsl --version` is not recognised, Microsoft Learn says "you are likely using an older inbox version of WSL that must be updated before systemd is available".

---

### Two configuration files

From Microsoft Learn, "Advanced settings configuration in WSL":

| File | Location | Scope |
|---|---|---|
| `.wslconfig` | `%UserProfile%\.wslconfig`, outside any distribution | the WSL 2 virtual machine: memory, processors, swap, networking mode |
| `wsl.conf` | `/etc/wsl.conf`, inside a distribution | that distribution: automount, interop, user, boot command, systemd |

1. Changes apply only after the subsystem stops. The page calls it "The 8 second rule": wait until the distribution "completely stops running and restarts". Check with `wsl.exe --list --running`, or stop everything with `wsl.exe --shutdown`, which "will shut down all running distributions, so use wisely". `wsl.exe --terminate <distro>` stops one.
2. systemd inside a distribution is `[boot]` with `systemd=true` in `/etc/wsl.conf`, followed by `wsl.exe --shutdown`.
3. `[interop]` `appendWindowsPath=false` stops Windows directories being appended to the Linux `PATH`, which removes Windows tools shadowing Linux ones and speeds up command lookup.
4. `[automount]` controls how Windows drives appear under `/mnt`. Its `options` key takes DrvFs options only.
5. Paths in `.wslconfig` "must be Windows paths with escaped backslashes", for example `C:\\Temp\\kernel`.
6. The page recommends WSL Settings from the Start menu over hand-editing `.wslconfig`.

---

### Where files belong

Microsoft Learn, "Working across file systems": "For the fastest performance speed, store your files in the WSL file system if you are working in a Linux command line", and the Windows file system when working from PowerShell or `cmd`.

1. A repository built with Linux tools lives under `/home/<user>/`, not `/mnt/c/...`.
2. From Windows, a distribution's files are at `\\wsl$\<distro>\` or `\\wsl.localhost\<distro>\`.
3. Windows is case-insensitive and Linux is case-sensitive. A directory created from WSL can carry a per-directory case sensitivity flag that Windows tools then honour, see the `case` automount option.
4. Windows executables run from Linux "have the same permission rights as the WSL process", and Linux binaries run through `wsl.exe` "have the same Windows administrative rights as the calling process and terminal". Running `wsl` from an elevated terminal gives the Linux side Windows administrator rights on `/mnt`.
5. Line endings matter at this boundary, see [files-and-links.md](files-and-links.md).

---

### Calling across the boundary

1. From PowerShell, arguments after `wsl` "are forwarded to the WSL process without modification", so paths must be in Linux form.
2. Pass environment variables with `WSLENV` and its `/p` flag to translate a path between the two forms.
3. A bash script started through `wsl.exe -d <distro> bash -c "..."` runs as the distribution's default user. Quote for PowerShell first, then for bash.
