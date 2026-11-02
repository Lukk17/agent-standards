# Devices and Network

GPU driver, displays and the refresh rate actually applied, audio devices, network and firewall state, time sync and the dual boot clock. The rules live in [SKILL.md](../SKILL.md). Linux commands below were executed read-only on CachyOS with KDE Plasma 6 on Wayland and an NVIDIA RTX 2080, macOS and Windows commands are UNVERIFIED.

---

### GPU driver

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `lspci -nnk \| grep -A3 -E 'VGA\|3D\|Display'` | `Kernel driver in use` missing, or a fallback driver such as `nouveau` or `simpledrm` where the baseline had the vendor driver, `fail` | verified, `nvidia` |
| Linux, NVIDIA | `cat /proc/driver/nvidia/version` and `nvidia-smi --query-gpu=name,driver_version,pstate --format=csv` | The kernel module version differs from the user space version, which happens after an upgrade without a reboot and makes `nvidia-smi` fail, `fail` | verified, both versions matched on the test machine |
| Linux, Arch | `pacman -Q \| grep -E '^(nvidia\|linux.*nvidia)'` | A kernel without its matching prebuilt driver package, or a DKMS package with no module built for the running kernel | verified |
| Linux, AMD or Intel | `glxinfo -B` or `vulkaninfo --summary` where installed | Renderer `llvmpipe`, which is software rendering, `fail` | UNVERIFIED |
| macOS | `system_profiler SPDisplaysDataType` | GPU missing from the list, Metal support missing | UNVERIFIED |
| Windows | `Get-CimInstance Win32_VideoController \| Select-Object Name, DriverVersion, DriverDate, Status` | `Microsoft Basic Display Adapter`, which means no vendor driver, or `Status` other than `OK` | UNVERIFIED |

---

### Displays: applied refresh against the monitor's maximum

The question is whether the mode in use is the best the monitor offers at its resolution. A 144 Hz monitor left at 60 Hz is the common case, and it comes from a cable, a port, a driver default or a desktop setting nobody changed.

On KDE Plasma, compare the current mode with the highest refresh at the same resolution:

```bash
kscreen-doctor -j | python3 -c "import json,sys; d=json.load(sys.stdin); [print(o['name'], cur['size']['width'], cur['size']['height'], round(cur['refreshRate'], 2), 'max', round(max(m['refreshRate'] for m in o['modes'] if m['size'] == cur['size']), 2)) for o in d['outputs'] if o['enabled'] for cur in [next(m for m in o['modes'] if m['id'] == o['currentModeId'])]]"
```

Executed on the test machine, it printed `DP-3 3840 2160 60.0 max 60.0` and `HDMI-A-1 1920 1080 60 max 74.97`. The second line is a `warn`: the monitor offers 74.97 Hz at its native resolution and runs at 60.

Confirm the monitor's own limit from its EDID, which works unprivileged:

```bash
edid-decode /sys/class/drm/card1-HDMI-A-1/edid
```

Read `Display Product Name` and the `Display Range Limits` line. On the test machine it printed `'PL2792H'` and `Monitor ranges (GTF): 55-76 Hz V`. List the connectors with `ls /sys/class/drm/`, the card number differs between machines.

| OS or desktop | Command | Status |
|---|---|---|
| X11 | `xrandr --query`, where `*` marks the current mode and `+` the preferred one | UNVERIFIED |
| GNOME on Wayland | `gdbus call --session --dest org.gnome.Mutter.DisplayConfig --object-path /org/gnome/Mutter/DisplayConfig --method org.gnome.Mutter.DisplayConfig.GetCurrentState` | UNVERIFIED |
| wlroots compositors | `wlr-randr` | UNVERIFIED |
| macOS | `system_profiler SPDisplaysDataType`, which prints the resolution and refresh per display | UNVERIFIED |
| Windows | `Get-CimInstance Win32_VideoController \| Select-Object CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, MaxRefreshRate` | UNVERIFIED |
| Windows | `Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorListedSupportedSourceModes` for the modes each monitor lists | UNVERIFIED |

A lower refresh can be deliberate, for example a capture card or a power choice. When `MACHINE.md` records it as the owner's choice, the verdict is `accepted`.

---

### Audio devices

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux, PipeWire | `wpctl status` | No sinks, a `Dummy Output` sink, which means no card was found, or a default sink (marked `*`) other than the one `MACHINE.md` names, for example a monitor's HDMI output without speakers | verified |
| Linux | `cat /proc/asound/cards` | A card from the baseline missing | verified |
| Linux | `systemctl --user is-active pipewire pipewire-pulse wireplumber` | Any of them not `active` | verified |
| macOS | `system_profiler SPAudioDataType` | The default output device differs from the baseline | UNVERIFIED |
| Windows | `Get-CimInstance Win32_SoundDevice \| Select-Object Name, Status` | `Status` other than `OK`. The default device is not exposed through CIM, so ask the owner rather than installing a module to read it | UNVERIFIED |

---

### Network and firewall

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `ip -br addr` | The primary interface `DOWN` or without an address, an interface from the baseline missing | verified |
| Linux | `nmcli -t -f NAME,TYPE,DEVICE,ACTIVE connection show --active` | No active connection on the interface the baseline uses | verified |
| Linux | `resolvectl status` and `ls -l /etc/resolv.conf` | `resolv.conf` no longer the link the baseline recorded, a DNS server nobody configured. `resolv.conf mode: foreign` means something other than systemd-resolved writes the file | verified |
| Linux | `systemctl is-active ufw firewalld nftables` | None `active`, `fail`, or two firewalls active at once, `warn` | verified, `ufw` active |
| Linux | `sudo ufw status verbose` or `sudo nft list ruleset` | Rules need root, so they go to Needs root | verified root only: `ufw status` printed `ERROR: You need to be root to run this script` |
| macOS | `networksetup -listallhardwareports`, `scutil --dns` | As for Linux | UNVERIFIED |
| macOS | `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` | `disabled`, `warn` on a laptop, the owner decides | UNVERIFIED |
| Windows | `Get-NetAdapter \| Select-Object Name, Status, LinkSpeed`, `Get-NetIPConfiguration` | As for Linux | UNVERIFIED |
| Windows | `Get-NetFirewallProfile \| Select-Object Name, Enabled` | Any profile `False`, `fail` | UNVERIFIED |

---

### Time sync and the dual boot clock

| OS | Command | Wrong looks like | Status |
|---|---|---|---|
| Linux | `timedatectl show -p NTPSynchronized -p LocalRTC -p Timezone` | `NTPSynchronized=no`, `fail`. `LocalRTC=yes` on a machine that does not dual boot with Windows, `warn` | verified, `yes` and `no` |
| Linux | `timedatectl timesync-status` | No server, or a stratum of 16 | verified, with `systemd-timesyncd` |
| Linux | `systemctl is-active systemd-timesyncd chronyd ntpd` | None active | verified |
| macOS | `sudo systemsetup -getusingnetworktime` | Needs root, goes to Needs root | UNVERIFIED |
| Windows | `w32tm /query /status` | `Source: Local CMOS Clock` means no sync. May need elevation | UNVERIFIED |
| Windows | `Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name RealTimeIsUniversal -ErrorAction SilentlyContinue` | See below | UNVERIFIED |

On a machine that dual boots Linux and Windows, both must agree on what the hardware clock holds. Linux keeps it in UTC unless `LocalRTC=yes`, and Windows keeps local time unless `RealTimeIsUniversal` is set to 1. When they disagree, the clock is wrong by the time zone offset after every switch. Report a mismatch between the Linux `LocalRTC` value and the Windows registry value as `warn`, and leave the fix to `windows`, which carries the dual boot clock. That Windows keeps local time by default is from memory, high confidence, not quoted here.
