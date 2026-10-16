# Memory

Installed modules, configured speed against the module rating and the CPU vendor's supported speed, mixed kits, channels, memory errors, and how the owner runs a memory test. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS on 2026-10-13 unless marked otherwise, macOS and Windows commands are UNVERIFIED.

---

### Installed modules

| OS | Command | What it gives | Status |
|---|---|---|---|
| Linux | `free -h`, `swapon --show`, `zramctl` | Total and swap, no per-module detail | verified |
| Linux | `sudo dmidecode -t memory` | Per slot: `Locator`, `Bank Locator`, `Size`, `Type`, `Speed` (the module's rated speed), `Configured Memory Speed`, `Manufacturer`, `Part Number`, `Rank`, `Configured Voltage`. Root only, so it goes to Needs root | verified root only: unprivileged it printed `/sys/firmware/dmi/tables/smbios_entry_point: Permission denied` |
| Linux | `decode-dimms` | SPD contents including the XMP profile. Needs the `ee1004` or `at24` module loaded and root to read, so it goes to Needs root as well | present at `/usr/bin/decode-dimms`, not executed |
| macOS | `system_profiler SPMemoryDataType` | Per slot on Intel Macs. On Apple silicon the memory is in the package and there are no slots to compare | UNVERIFIED |
| Windows | `Get-CimInstance Win32_PhysicalMemory \| Select-Object DeviceLocator,BankLabel,Capacity,Speed,ConfiguredClockSpeed,Manufacturer,PartNumber,Attributes,SMBIOSMemoryType` | Per slot. The bootstrap prompt lists it as unprivileged. If it answers access denied, move it to Needs root as `needs: elevated` | UNVERIFIED |

Read the Windows fields carefully. Microsoft documents `ConfiguredClockSpeed` as "The configured clock speed of the memory device, in megahertz (MHz), or 0, if the speed is unknown", and `Attributes` as "SMBIOS - Type 17 - Attributes. Represents the RANK" (<https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory>, fetched 2026-10-13). The same page documents `Speed` as "Speed of the physical memory, in nanoseconds", which does not match the MT/s figures it usually shows. Treat `Speed` as the module rating only after checking it against the part number.

On Linux the one root command the owner runs is `sudo dmidecode -t memory`. Do not ask for more.

---

### Configured speed against rating against vendor support

Three numbers decide the verdict, and each needs its own source.

1. Configured speed: `Configured Memory Speed` from `dmidecode`, `ConfiguredClockSpeed` on Windows, `Speed` per slot from `system_profiler` on an Intel Mac.
2. Module rating: the part number looked up on the memory vendor's specification page, which gives the XMP or EXPO speed, timings and voltage, plus the JEDEC SPD default. Quote the page and its URL.
3. CPU vendor support for that CPU, that DIMM count and that rank. Look it up on the CPU vendor's page for the exact model, quote the field and the URL, and date the fetch.

What the vendor pages look like, fetched 2026-10-13:

1. AMD Ryzen 7 2700X. The AMD page reads "System Memory Type DDR4 Memory Channels 2 System Memory Specification Up to 2933 MT/s" (<https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-2000-series/amd-ryzen-7-2700x.html>, fetched raw). That figure is for the best case. AMD publishes no per DIMM count table for this generation, and Puget Systems relays the one AMD sent them: "for users that want to use four sticks of RAM, DDR4-1866 or DDR4-2133 is the fastest supported RAM speed depending on whether the RAM is single or dual ranked. If you only need to use two sticks of RAM, the supported speed varies between DDR4-2400 and DDR4-2933" (<https://www.pugetsystems.com/blog/2018/06/06/2nd-Gen-AMD-Ryzen-Supported-RAM-Speeds-1175/>, posted 2018-06-06, a secondary source relaying AMD).
2. Intel Core i9-14900K. Intel's specification page lists "Up to DDR5 5600 MT/s" and "Up to DDR4 3200 MT/s" with "Max # of Memory Channels 2" (<https://www.intel.com/content/www/us/en/products/sku/236773/intel-core-i9-processor-14900k-36m-cache-up-to-6-00-ghz/specifications.html>, read through a summarising fetch because the raw page answered 403, so re-read it before relying on it).

Verdicts:

| Situation | Verdict |
|---|---|
| Configured at or below the CPU vendor's figure for this DIMM count and rank, and at or below the module rating | `ok` |
| Configured above the CPU vendor's figure, for example an XMP profile on four DIMMs | `warn`. It often works, it is the first suspect for random crashes and filesystem checksum errors, and it is the owner's call |
| Configured at the JEDEC default while the modules are rated higher | `warn` for performance, the XMP or EXPO profile is off. Never `fail` |
| Configured above the module rating | `fail`, a manual overclock beyond the parts |
| Slots report different configured speeds | `fail`, the controller runs one speed and the readout is wrong or a module is not detected properly |

---

### Mixed kits and channels

| Check | How | Wrong looks like |
|---|---|---|
| Mixed kits | Compare `Part Number` and `Manufacturer` across slots | More than one part number, or the same size from two vendors. Memory vendors warn against it: G.Skill's `F4-3200C14D-16GTZR` page says "Do not mix memory kits. Memory kits are sold in matched kits that are designed to run together as a set. Mixing memory kits will result in stability issues or system failure" (<https://www.gskill.com/specification/165/166/1536653463/F4-3200C14D-16GTZR-EOL-Specification>, fetched raw 2026-10-13), `warn` |
| Mixed sizes | Compare `Size` across slots | Different sizes run in a partly asymmetric mode, `warn` |
| Channels | `Locator` and `Bank Locator` in `dmidecode`, `DeviceLocator` and `BankLabel` on Windows, which name the channel, for example `P0 CHANNEL A` | Two modules both in channel A with channel B empty means single channel, about half the bandwidth, `warn` |
| Module count | Count slots with a size against the board's slot count in `MACHINE.md` | A module missing since the baseline, `fail` |

The board manual names the slots to use for two modules. Quote it rather than guessing slot order.

---

### Memory errors

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `ls /sys/devices/system/edac/mc/` | With ECC memory and an EDAC driver, one `mcX` directory per controller. No `mcX` directory means no EDAC reporting, which is normal for non-ECC desktop memory, so record `unknown (no EDAC)` rather than `ok` | verified, no `mcX` on the test machine |
| Linux | `grep -H . /sys/devices/system/edac/mc/mc*/ce_count /sys/devices/system/edac/mc/mc*/ue_count` | Any non-zero `ue_count`, or a `ce_count` that grew since the baseline | UNVERIFIED, nothing to read on a non-ECC machine |
| Linux | `ras-mc-ctl --summary` | Any recorded error. Needs `rasdaemon` running, absent is `unknown`, never install it | UNVERIFIED, `rasdaemon` inactive on the test machine |
| Linux | `journalctl -k -b --no-pager -q -g 'mce\|machine check\|edac\|hardware error'` | Any line | verified, printed `-- No entries --` |
| Windows | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-WHEA-Logger'; StartTime = (Get-Date).AddDays(-30) } -MaxEvents 20` | Any event, WHEA is where Windows records hardware errors | UNVERIFIED |
| macOS | none user visible | Use Apple Diagnostics below | not applicable |

The kernel RAS guide defines the two counters: a Correctable Error is when "the error detection mechanism detected and corrected the error", an Uncorrected Error is when "the amount of errors happened above the error correction threshold, and the system was unable to auto-correct" (<https://docs.kernel.org/admin-guide/RAS/main.html>, fetched 2026-10-13).

---

### Running a memory test

A real memory test needs a reboot and takes the machine away from the owner for an hour or more. The agent never schedules it and never reboots. Hand the steps to the owner.

1. Linux and Intel Macs that can boot it: Memtest86+. The project describes it as "a free, open-source, stand-alone memory tester for IA-32, x86-64, and LoongArch64 systems" that runs "directly by a PC BIOS (legacy or UEFI)" or "via an intermediate bootloader", from "a USB Flash Drive (FAT32 formatted)" (<https://www.memtest.org/>, fetched 2026-10-13, current version v8.10 released 2026-05-16). On Arch and CachyOS the `extra` repository carries `memtest86+-efi` 8.10-1 (`pacman -Si memtest86+-efi`, executed 2026-10-13). Installing it and adding a boot entry is a change under `arch-linux` or `cachyos`, not part of this check. Let it run at least one full pass, and treat a single error as `fail`.
2. Windows: Windows Memory Diagnostic. Microsoft's older reliability guide says to run `mdsched.exe` and choose to restart now or at the next restart, after which the test runs automatically (<https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-vista/cc749573(v=ws.10)>, a Vista era page, so confirm the dialog on the current build). Where the result lands in the System log is UNVERIFIED.
3. macOS: Apple Diagnostics. Apple's page "Use Apple Diagnostics to test your Mac" says on Apple silicon "Press and hold the power button on your Mac", release at Options, then "Press and hold Command (⌘)-D", and on Intel "press and hold the D key on your keyboard as your Mac starts up" (<https://support.apple.com/en-us/102550>, fetched 2026-10-13).

While a speed above the CPU vendor's rating is in force, suggest the owner test at the configured speed first, and at the vendor's figure second if errors appear, so the result names the cause.
