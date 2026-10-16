# Bootstrap MACHINE.md

A prompt for any agent: discover this computer read-only and write `MACHINE.md` from the template [MACHINE.md.example](MACHINE.md.example). Paste the whole file into a session started in your home directory, or tell the agent to read it and follow it.

---

### Your task

Write one file describing this computer, dated and sourced, for agents that will later change things on it. Discovery is read-only. The only file you create or change is `MACHINE.md` itself.

Target path:

| OS | Path |
|---|---|
| Linux and macOS | `~/.config/agents/MACHINE.md` |
| Windows | `%USERPROFILE%\.config\agents\MACHINE.md` |

Create the `agents` directory if it is missing. If `MACHINE.md` already exists, this is a refresh: read it first, keep every row whose Source is `owner`, update discovered rows in place with the new date, and add one change log entry naming what moved. Never discard the change log or the never-touch list.

---

### Hard rules

1. Never run `sudo`, `doas`, `pkexec`, `runas`, an elevated PowerShell, or anything that asks for a password. When a fact needs root, write the exact command into the Needs root section as `needs: sudo <command>` with the row it fills, and move on.
2. Read-only means read-only. No package install, no service start or stop, no mount, no unlock, no `fsck`, `ntfsfix`, `chkdsk`, `diskpart`, `parted`, `wipefs`, `mkfs`, no driver change, no setting change. If a discovery tool is not installed, record it as absent. Do not install it.
3. Never probe a disk the owner names as never-touch, not even with a read-only filesystem tool. `lsblk`, `Get-Disk` and `diskutil list` level listing is the limit for those.
4. Never write a secret: no password, recovery key, BitLocker or FileVault key, Wi-Fi passphrase, API token, or the value of any environment variable. List environment variable names only.
5. Every row gets a Source (the command, or `owner`) and a Verified date taken from the system clock, not assumed.
6. Do not edit the global instruction file. At the end, show the owner the one link line from the template and ask whether to add it.

---

### Step 1: ask the owner first

Discovery cannot know these. Ask them as one numbered list, give your suggested default for each, and wait for the answers before writing anything:

1. Default projects folder. Suggest `~/Projects` on Linux and macOS. On Windows ask, because it is often on a second drive, for example `D:\Development`.
2. Disks or partitions that must never be touched, and why: encrypted volumes such as BitLocker, FileVault or LUKS data disks, another OS's system disk, backup drives.
3. Volumes another OS also writes to, and what must be true before Linux writes to them, for example Windows Fast Startup switched off for NTFS.
4. The repository or workspace that provisions or administers this machine, if any.
5. Off-machine backups: tool, target and schedule, or none.
6. Preferences an agent should follow here: which shell to give commands for, packages or sources never to use, whether to snapshot before risky changes, whether sleep or hibernation is known to work.
7. Known quirks already fixed on this machine, with the reason, so the file records the why and not only the state.

---

### Step 2: identify the OS

Run `uname -s` where it exists, otherwise check `$env:OS` in PowerShell. Then use the matching table below. Run each command, read its output, and fill the template row it names. A command that fails or is absent leaves the row as `unknown (<command>: <error>)`, which is still a fact. These lists were written against the tools' documented behaviour and only the Linux one has been run end to end, so a command listed as unprivileged that answers access denied moves to the root list rather than being retried elevated.

---

### Step 3: discover, Linux

| Section | Commands, all read-only and unprivileged |
|---|---|
| Identity | `hostnamectl`, `cat /etc/os-release`, `uname -r`, `echo $XDG_CURRENT_DESKTOP $XDG_SESSION_TYPE`, `plasmashell --version` or `gnome-shell --version`, `systemctl status display-manager`, `id`, `echo $SHELL`, `localectl`, `timedatectl` |
| CPU | `lscpu`, `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor`, `/lib/ld-linux-x86-64.so.2 --help` for the supported ISA levels |
| RAM | `free -h`, `swapon --show`, `zramctl`. Slots, speed and part numbers need `dmidecode -t memory`, which is root only |
| Motherboard and firmware | every readable file under `/sys/class/dmi/id/` (skip `uevent` and `modalias`, the serial files are root only), `bootctl status` for Secure Boot and TPM, `test -d /sys/firmware/efi` |
| GPU | `lspci -nnk`, `nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv`, `cat /proc/driver/nvidia/version`, `glxinfo -B` or `vulkaninfo --summary` if installed |
| Displays | `kscreen-doctor -o` on KDE, `gnome-randr` or `gdbus` on GNOME, `wlr-randr` on wlroots compositors, `xrandr --query` on X11. Monitor model names come from the EDID: read `/sys/class/drm/card*-*/edid` and decode the vendor id at bytes 8 and 9 and the 0xFC name descriptor |
| Storage | `lsblk -o NAME,MODEL,SERIAL,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINTS,ROTA,TRAN`, `findmnt -rno TARGET,SOURCE,FSTYPE,OPTIONS`, `cat /etc/fstab`, `cat /sys/block/*/queue/scheduler`. `/etc/crypttab`, `cryptsetup luksDump`, `smartctl -a` and `blkid -p` on a locked volume are root only |
| Boot | `bootctl status`, `efibootmgr`, `pacman -Q` or `dpkg -l` or `rpm -q` for the bootloader, kernels and initramfs tool, `cat /etc/mkinitcpio.conf` or `/etc/dracut.conf.d/*`. `/boot` contents are often root only |
| Snapshots and backup | `snapper list-configs`, `systemctl is-enabled snapper-timeline.timer snapper-cleanup.timer`, `timeshift --list` is root only, `command -v borg restic btrbk` |
| Network | `ip -br addr`, `nmcli -t -f NAME,TYPE,DEVICE,ACTIVE connection show`, `iw dev`, `resolvectl status`, `ls -l /etc/resolv.conf`, `tailscale status`, `systemctl is-active ufw firewalld nftables`, `bluetoothctl show`. `ufw status verbose` and `nft list ruleset` are root only |
| Audio | `wpctl status`, `pactl info`, `cat /proc/asound/cards`, `ls ~/.config/wireplumber/wireplumber.conf.d ~/.config/pipewire` and read every file found |
| Input and peripherals | `lsusb`, `groups` for `openrazer` or `plugdev`, `command -v openrazer-daemon ckb-next solaar piper` |
| Power | `powerprofilesctl list`, `systemctl is-active power-profiles-daemon tuned tlp ananicy-cpp scx_loader`, `cat /sys/power/state` |
| Package managers | `cat /etc/pacman.conf` section names, `pacman -Qqm` for foreign packages, `ls /etc/*.pacnew /etc/pacman.d/*.pacnew`, or `apt-cache policy` and `ls /etc/apt/sources.list.d`, or `dnf repolist`, plus `flatpak remotes`, `snap list`, `brew --version` |
| Runtimes | `pyenv versions`, `pyenv global`, `python3 --version`, `uv --version`, `node --version`, `ls ~/.nvm/versions/node`, `ls ~/.sdkman/candidates/*`, `java -version`, `go version`, `rustc --version`, `flutter --version`, `ls ~/Android/Sdk` |
| Containers and VMs | `docker info --format '{{.ServerVersion}} {{.Driver}} {{.CgroupDriver}}'`, `docker compose version`, `systemctl is-enabled docker libvirtd`, `virsh -c qemu:///system list --all`, `command -v podman VBoxManage vmware` |
| Agent tooling | `claude --version`, `codex --version`, `opencode --version`, `kilo --version`, `copilot --version`, `gh --version`, `ls -la ~/.claude ~/.codex ~/.config/opencode ~/.config/kilo ~/.copilot ~/.agents`, `cat ~/.agents/.upstream-commit` |

Root-only commands to list for the owner on Linux, with the row each fills: `sudo dmidecode -t memory`, `sudo cat /etc/crypttab`, `sudo ls -R /boot`, `sudo snapper -c root list`, `sudo ufw status verbose`, `sudo nft list ruleset`, `sudo smartctl -a /dev/<disk>` for each disk that is not on the never-touch list, `sudo cryptsetup luksDump /dev/<luks partition>` for the TPM2 token question, `sudo efibootmgr -v` where the plain form hides the paths.

---

### Step 3: discover, macOS

| Section | Commands, all read-only and unprivileged |
|---|---|
| Identity | `sw_vers`, `uname -r`, `scutil --get ComputerName`, `id`, `echo $SHELL`, `systemsetup -gettimezone` is root only, so read `readlink /etc/localtime` |
| CPU | `sysctl -n machdep.cpu.brand_string hw.physicalcpu hw.logicalcpu`, `uname -m` |
| RAM | `sysctl -n hw.memsize`, `system_profiler SPMemoryDataType`, `sysctl vm.swapusage` |
| Motherboard and firmware | `system_profiler SPHardwareDataType` for model identifier and firmware version, `csrutil status` |
| GPU and displays | `system_profiler SPDisplaysDataType` |
| Storage | `diskutil list`, `diskutil apfs list`, `diskutil info /`, `fdesetup status`, `cat /etc/fstab` if present, `mount` |
| Boot | `system_profiler SPSoftwareDataType` for the boot volume and mode, `bputil -d` is root only on Apple silicon |
| Snapshots and backup | `tmutil destinationinfo`, `tmutil listlocalsnapshots /` |
| Network | `networksetup -listallhardwareports`, `ifconfig`, `scutil --dns`, `tailscale status`, `/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate` |
| Audio | `system_profiler SPAudioDataType` |
| Input and peripherals | `system_profiler SPUSBDataType SPBluetoothDataType` |
| Power | `pmset -g`, `pmset -g custom` |
| Package managers | `brew config`, `brew tap`, `brew list --cask`, `mas list` |
| Runtimes, containers, agent tooling | the same commands as the Linux rows, plus `colima status` or `orb status` if Docker runs through them |

Root-only commands to list for the owner on macOS: `sudo bputil -d`, `sudo fdesetup list`, `sudo systemsetup -gettimezone`, `sudo tmutil listbackups` where Full Disk Access is missing.

---

### Step 3: discover, Windows

Run these in a normal, non-elevated PowerShell 7 session.

| Section | Commands, all read-only and unprivileged |
|---|---|
| Identity | `Get-ComputerInfo -Property OsName,OsVersion,OsBuildNumber,CsName,WindowsEditionId`, `whoami /groups`, `Get-TimeZone`, `Get-Culture`, `$PSVersionTable.PSVersion` |
| CPU | `Get-CimInstance Win32_Processor \| Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed` |
| RAM | `Get-CimInstance Win32_PhysicalMemory \| Select-Object BankLabel,Capacity,Speed,ConfiguredClockSpeed,Manufacturer,PartNumber`, `Get-CimInstance Win32_PhysicalMemoryArray \| Select-Object MemoryDevices`, `Get-CimInstance Win32_PageFileUsage` |
| Motherboard and firmware | `Get-CimInstance Win32_BaseBoard`, `Get-CimInstance Win32_BIOS`, `Get-ComputerInfo -Property BiosFirmwareType` for UEFI or legacy. `Confirm-SecureBootUEFI` and `Get-Tpm` are elevated only |
| GPU | `Get-CimInstance Win32_VideoController \| Select-Object Name,DriverVersion,DriverDate,AdapterRAM`, `nvidia-smi` if present |
| Displays | `Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorID` for model names, `Get-CimInstance Win32_VideoController \| Select-Object CurrentHorizontalResolution,CurrentVerticalResolution,CurrentRefreshRate` |
| Storage | `Get-PhysicalDisk`, `Get-Disk`, `Get-Partition`, `Get-Volume`. `Get-BitLockerVolume` and `manage-bde -status` are elevated only |
| Boot | `bcdedit /enum` is elevated only, so record the dual-boot answer from the owner and list the command |
| Snapshots and backup | `Get-ComputerRestorePoint` and `vssadmin list shadows` are elevated only. Ask the owner about File History or third-party backup |
| Network | `Get-NetAdapter`, `Get-NetIPConfiguration`, `netsh wlan show interfaces`, `Get-DnsClientServerAddress`, `tailscale status`, `Get-NetFirewallProfile \| Select-Object Name,Enabled` |
| Audio | `Get-CimInstance Win32_SoundDevice` |
| Input and peripherals | `Get-PnpDevice -PresentOnly -Class USB,Mouse,Keyboard,HIDClass \| Select-Object FriendlyName,InstanceId` |
| Power | `powercfg /getactivescheme`, `powercfg /list`, `powercfg /a`, and the Fast Startup value `Get-ItemPropertyValue 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Power' HiberbootEnabled` |
| Package managers | `winget --version`, `winget source list`, `choco --version`, `scoop --version` |
| Runtimes | `py -0p`, `pyenv versions`, `uv --version`, `node --version`, `nvm list`, `java -version`, `go version`, `rustc --version` |
| Containers and VMs | `wsl -l -v`, `docker info`, `Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V` is elevated only |
| Agent tooling | the same version commands as Linux, and `Get-ChildItem $HOME\.claude,$HOME\.codex,$HOME\.agents -Force` |

Elevated commands to list for the owner on Windows, written as `needs: elevated <command>`: `Get-BitLockerVolume`, `manage-bde -status`, `bcdedit /enum`, `Confirm-SecureBootUEFI`, `Get-Tpm`, `vssadmin list shadows`, `Get-ComputerRestorePoint`.

---

### Step 4: write the file

1. Start from [MACHINE.md.example](MACHINE.md.example). If it is not available locally, reproduce its section list: Identity, CPU, RAM, Motherboard and firmware, GPU, Displays, Storage with the never-touch table, Boot, Snapshots and backup, Network, Audio, Input and peripherals, Power, Package managers and repositories, Language runtimes and version managers, Containers and virtual machines, Agent tooling, Projects, Known quirks and fixes, Owner preferences, Needs root, Change log.
2. Put the date of this run, from the system clock, in the "Last full discovery" line, with your agent name and version and the OS version.
3. Fill every row. Mark the owner's answers from step 1 as `owner`. Where a discovered fact contradicts what the owner said, keep both and add a Known quirks entry naming the disagreement.
4. Put the owner's never-touch disks in the never-touch table with the reason, and repeat the device name in the Storage disk table with "never touch" in the mount column.
5. Fill Needs root with every root-only command from the table for this OS whose answer is still missing, one per line, each naming the row it would fill.
6. Add a change log entry for today: "MACHINE.md created by discovery" plus any change the owner told you happened today.
7. Delete every row and placeholder that does not apply to this machine rather than leaving `<...>` behind.

---

### Step 5: report to the owner

Reply with: the path written, what was discovered against what came from the owner, the Needs root list exactly as written in the file, and the link line from the top of the template, with the question whether to add it to the global instruction file. Do not add it unasked.
