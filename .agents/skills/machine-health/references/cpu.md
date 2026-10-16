# CPU

Model, microcode, frequency governor and power profile, temperatures and throttling. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS on 2026-10-13 on an AMD Ryzen 7 2700X, macOS and Windows commands are UNVERIFIED.

---

### Model and microcode

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `lscpu` | Model differs from `MACHINE.md`, fewer online CPUs than threads | verified |
| Linux | `grep -m1 microcode /proc/cpuinfo` | Revision differs from the baseline with no package update behind it | verified, printed `0x800820d` |
| Linux | `pacman -Q amd-ucode intel-ucode`, or `dpkg -l amd64-microcode intel-microcode`, or `rpm -q microcode_ctl linux-firmware` | No microcode package installed, or the package was updated after the current boot, which means a reboot is owed | Arch form verified |
| macOS | `sysctl -n machdep.cpu.brand_string` | Model differs from `MACHINE.md`. Microcode arrives with macOS updates and is not inspectable | UNVERIFIED |
| Windows | `Get-CimInstance Win32_Processor \| Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed,CurrentClockSpeed` | Model or core count differs from `MACHINE.md` | UNVERIFIED |
| Windows | `Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0' \| Select-Object 'Update Revision'` | Value differs from the baseline with no BIOS or Windows update behind it | UNVERIFIED |

On Linux the early boot lines that name the microcode revision are often missing from the journal, and `dmesg` is root only while `kernel.dmesg_restrict` is 1. Both were measured on the test machine: `journalctl -k -b` started four minutes after boot and `dmesg` answered `Operation not permitted`. Read `/proc/cpuinfo` instead, and list `sudo dmesg` in Needs root only when the boot lines matter.

---

### Governor and power profile

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` | Governor `performance` left on a laptop on battery, `powersave` on `acpi-cpufreq` (which pins the lowest frequency), or a driver that changed since the baseline | verified, printed `acpi-cpufreq` and `schedutil` |
| Linux | `cat /sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference` | Only exists under `amd-pstate` or `intel_pstate` in active mode. Absent under `acpi-cpufreq`, which is not a fault | verified absent |
| Linux | `powerprofilesctl get` | Profile differs from the owner preference in `MACHINE.md` | verified, printed `balanced` |
| Linux | `cat /sys/devices/system/cpu/cpufreq/boost` | `0` when the owner expects boost on | verified, printed `1` |
| macOS | `pmset -g` | Low Power Mode on when not expected | UNVERIFIED |
| Windows | `powercfg /getactivescheme` | Scheme differs from the baseline, or Power saver on a desktop | UNVERIFIED |

---

### Temperatures

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `sensors` | CPU reading near or above the vendor's maximum at idle, or a sensor chip from the baseline missing | verified |
| macOS | `sudo powermetrics --samplers smc -n 1` | Needs root, so it goes to Needs root | UNVERIFIED |
| Windows | `Get-CimInstance -Namespace root\wmi -ClassName MSAcpi_ThermalZoneTemperature` | Needs elevation on most machines and reports an ACPI zone in tenths of kelvin, often not the CPU die. Treat the value as indicative only | UNVERIFIED |

Read the right sensor. On AMD the `k10temp` driver reports `Tctl` and sometimes `Tdie`. The kernel documentation says "On some AMD CPUs, there is a difference between the die temperature (Tdie) and the reported temperature (Tctl)" and "Tdie is the real measured temperature, and Tctl is used for fan control" (<https://docs.kernel.org/hwmon/k10temp.html>, fetched 2026-10-13). On the 2700X test machine `Tctl` read 56.0 and `Tdie` 46.0 at the same moment, so judge against `Tdie` where it exists.

Compare with the vendor's maximum, quoted from the vendor page rather than remembered. For the 2700X, AMD's page lists "Max. Operating Temperature (Tjmax) 85°C" (<https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-2000-series/amd-ryzen-7-2700x.html>, fetched raw 2026-10-13). Idle well below that is `ok`. Idle within 15 degrees of it is `warn`, which usually means a cooler, paste or fan curve problem the owner has to look at.

---

### Throttling

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux, Intel | `grep -H . /sys/devices/system/cpu/cpu*/thermal_throttle/*_throttle_count` | Any non-zero count, or a count that grew since the baseline | UNVERIFIED, the directory does not exist on the AMD test machine |
| Linux | `journalctl -k -b --no-pager -q -g 'thrott\|temperature above\|machine check'` | Any line. `-- No entries --` is the clean answer | verified, clean |
| Linux | `nvidia-smi --query-gpu=name,temperature.gpu,clocks_event_reasons.active,pstate --format=csv` | A reason bitmask other than `0x0` or `0x1` (idle) while under load. Older drivers spell the field `clocks_throttle_reasons.active` | verified, driver 615.78.08 printed `0x0000000000000001` |
| macOS | `pmset -g therm` | A `CPU_Speed_Limit` below 100, or a recorded thermal warning level | UNVERIFIED |
| Windows | `Get-WinEvent -FilterHashtable @{ LogName = 'System'; ProviderName = 'Microsoft-Windows-Kernel-Processor-Power'; StartTime = (Get-Date).AddDays(-7) } -MaxEvents 20` | Events saying the processor speed is limited by firmware. The event id is from memory and not checked against a Microsoft page | UNVERIFIED |
