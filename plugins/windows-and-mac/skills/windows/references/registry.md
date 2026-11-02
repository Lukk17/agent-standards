# The Registry

Read this before reading or changing a registry value. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

---

### Where things live

| Hive | Holds | Who can write |
|---|---|---|
| `HKCU` (`HKEY_CURRENT_USER`) | the signed-in user's settings | the user |
| `HKLM` (`HKEY_LOCAL_MACHINE`) | machine wide settings, services, drivers, policies | administrators |
| `HKLM\SOFTWARE\WOW6432Node` | the 32-bit view of `HKLM\SOFTWARE` on 64-bit Windows | administrators |

An elevated session running as a different administrator account has a different `HKCU`. A per-user value set from that session lands in the wrong profile, so hand per-user changes to the owner's own unelevated shell.

---

### Read

In PowerShell the hives are drives:

```powershell
Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
```

```powershell
Get-ItemPropertyValue -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled
```

From `cmd` or any shell, `reg.exe` does the same:

```powershell
reg.exe query "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled
```

---

### Back up, then change

1. Export the key first. `reg.exe export` writes a `.reg` file that restores it with `reg.exe import`:

```powershell
reg.exe export "HKCU\Software\<Vendor>\<App>" "$HOME\reg-backup-<app>-<date>.reg"
```

2. Change one value, with an explicit type:

```powershell
New-ItemProperty -Path 'HKCU:\Software\<Vendor>\<App>' -Name '<Name>' -PropertyType DWord -Value 1 -Force
```

3. Read it back with `Get-ItemPropertyValue`.
4. Some values are read once at process start or at boot. Microsoft Learn says of `LongPathsEnabled`: "The registry value will not be reloaded during the lifetime of the process", so a restart of the program, a sign-out or a reboot can be needed. Say which one.
5. Record the key, the old value, the new value and the backup file in the `MACHINE.md` change log.

`HKLM` changes go to the owner's elevated terminal. Never delete a whole key to "reset" an application without an export and the owner's approval.

---

### Policies

Values under `HKLM\SOFTWARE\Policies` and `HKCU\SOFTWARE\Policies` are Group Policy. On a managed machine they are rewritten by the next policy refresh, so a local change does not stick and can conflict with the organisation's settings. Read them, and report rather than override.
