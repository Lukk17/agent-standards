# BitLocker, Fast Startup and Dual Boot

Read this before any firmware, boot order, Secure Boot or bootloader change, before Linux writes to a Windows volume, and when the clock is wrong after switching operating systems. The rules live in [SKILL.md](../SKILL.md). Every Windows command here is UNVERIFIED.

---

### BitLocker: read the state

Elevated, so the owner runs them:

```powershell
Get-BitLockerVolume | Select-Object MountPoint, VolumeStatus, ProtectionStatus, EncryptionPercentage, KeyProtector
```

```powershell
manage-bde.exe -status
```

Record which volumes are encrypted in `MACHINE.md`, and put encrypted data volumes on its never-touch list. The Arch Wiki "Dual boot with Windows" page notes that Windows 11 and recently updated Windows 10 systems "generally have BitLocker enabled by default on the C: drive even if it appears off in Settings". Measure, do not assume.

Never write a recovery key into `MACHINE.md`, a log, or a chat. Ask the owner only to confirm it is saved somewhere off the machine, such as their Microsoft account, a printout or a password manager.

---

### What triggers BitLocker recovery

From Microsoft Learn, "BitLocker recovery overview", among the listed events:

1. "Changes to the boot manager"
2. "Upgrading critical early startup components, such as a BIOS or UEFI firmware upgrade"
3. "Modifying the Platform Configuration Registers (PCRs) used by the TPM validation profile"
4. "Changes to the NTFS partition table on the disk"
5. "Turning off, disabling, deactivating, or clearing the TPM"
6. "On devices with TPM 1.2, changing the BIOS or firmware boot device order"

The Arch Wiki adds that with a TPM bound to PCR 7, changing the Secure Boot database changes PCR 7 and "prevent[s] BitLocker from unlocking the disk", and that disabling Secure Boot shows the recovery screen until it is re-enabled.

---

### Suspend BitLocker for a planned change

Microsoft Learn: "For planned scenarios, such as a known hardware or firmware upgrades, initiating recovery can be avoided by temporarily suspending BitLocker protection. Suspending BitLocker leaves the drive fully encrypted". And from the `Suspend-BitLocker` reference: "If you do not specify the RebootCount parameter, the cmdlet uses a value of one (1), so BitLocker protection resumes after the next restart", with accepted values "integers from 0 to 15", where 0 suspends until `Resume-BitLocker`.

The owner runs, elevated, before a firmware update, a Secure Boot change, or installing a bootloader that becomes the first firmware entry:

```powershell
Suspend-BitLocker -MountPoint 'C:' -RebootCount 1
```

Use a higher count when the change needs several reboots, and confirm afterwards with `Get-BitLockerVolume` that `ProtectionStatus` is back to `On`.

---

### Fast Startup and hibernation

Fast Startup makes "Shut down" a hibernation of the kernel session. The Arch Wiki "Dual boot with Windows" page warns: "Data loss or filesystem corruption can occur when dual-booting between Windows and another operating system, like Linux, if either OS hibernates instead of fully shutting down", and "Windows may enter a hybrid shutdown mode (a form of hibernation) even when "Shut Down" is selected." It also notes that `ntfs-3g` refuses to mount a hibernated NTFS volume read-write, "but the NTFS driver within the Linux kernel has no such safeguard".

1. The safest setting on a dual boot machine is Fast Startup off and hibernation off. The wiki's command, in an elevated shell, is `powercfg /H off`, which removes hibernation and with it Fast Startup.
2. If the owner keeps hibernation, Linux must never write to a volume Windows had mounted while Windows is hibernated.
3. After changing the setting, shut Windows down fully once. The wiki: "rebooting is not sufficient". A restart from Windows is always a full shutdown, and holding Shift while choosing Shut down also bypasses Fast Startup. UNVERIFIED for every build.
4. The wiki notes that "Windows updates may re-enable Fast Startup". Check again after a feature update.
5. A shared EFI system partition can be damaged the same way. Prefer separate EFI partitions per operating system where the disks allow it.

From Linux, a hibernated or dirty NTFS volume usually refuses a read-write mount. Never force it with `ntfsfix` or a `force` mount option. Boot Windows and shut it down fully instead.

---

### The clock is wrong after switching

Windows keeps the hardware clock in local time by default, Linux in UTC. The Arch Wiki "System time" page recommends setting Windows to UTC with a registry value, run by the owner in an elevated terminal:

```powershell
reg.exe add "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\TimeZoneInformation" /v RealTimeIsUniversal /d 1 /t REG_DWORD /f
```

Back up the key first, see [registry.md](registry.md), and record the change in `MACHINE.md`.
