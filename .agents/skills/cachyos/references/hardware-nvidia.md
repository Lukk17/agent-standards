# Hardware Profiles and the NVIDIA Driver

Read this before touching the NVIDIA driver or its packages, running `chwd`, changing the GPU, or when the display breaks after a kernel or driver upgrade. The rules live in [SKILL.md](../SKILL.md).

---

### Discover the GPU and how its driver is packaged

```bash
lspci -nnk | grep -A3 -E 'VGA|3D|Display'
```

```bash
pacman -Q | grep -E 'nvidia|dkms'
```

```bash
lsmod | grep -E '^nvidia'
```

1. The `lspci` line gives the model, the PCI id and the kernel driver in use. The NVIDIA open kernel modules support Turing and newer GPUs, and older generations need the proprietary or a legacy branch. Check the generation before suggesting `-open`.
2. On CachyOS the module usually comes prebuilt per kernel, as `linux-cachyos-<flavor>-nvidia-open` or `-nvidia`, alongside `nvidia-utils` and `lib32-nvidia-utils`. If no `*-dkms` package is installed, DKMS is not in use.
3. `chwd --list-installed` shows the installed hardware profile. The profile name can say `dkms` while the modules actually come from the prebuilt package, so read the package list rather than the name.
4. `chwd` writes generated initramfs snippets such as `/etc/mkinitcpio.conf.d/10-chwd*.conf`. They say not to edit them, and they are why a driver change needs an initramfs rebuild.
5. `nvidia-smi` as a normal user shows the running driver version.
6. `cachyos-settings` can ship NVIDIA module options under `/usr/lib/modprobe.d/` and udev rules under `/usr/lib/udev/rules.d/`. Read them with `pacman -Ql cachyos-settings | grep -i nvidia`. An option the owner wants different goes in `/etc/modprobe.d/`, followed by an initramfs rebuild.

Record the GPU, driver version and packaging in `MACHINE.md`.

---

### chwd cheat sheet

| Command | What it does |
|---|---|
| `chwd --list-installed` | installed profiles |
| `chwd --list` | profiles available for the devices found |
| `chwd --list-all` | every profile |
| `chwd -c <profile>` | check a profile |
| `sudo chwd -i <profile>`, `-r <profile>`, `-f -i <profile>` | install, remove, force reinstall. These change packages and the initramfs |
| `sudo chwd -a` | autoconfigure for the current hardware |

1. Do not pipe `chwd` output into `head` or another program that exits early. It was observed to abort with SIGABRT when its output pipe closed, leaving a coredump. Redirect to a file or let it finish.
2. Do not run `chwd -r`, `-i` or `-a` without need. They remove or install driver packages. Take a snapshot, have a way to a console (the fallback kernel, a TTY with Ctrl+Alt+F3, a live ISO), and expect an initramfs rebuild.

---

### When the display breaks after an upgrade

1. Do not install packages from a black screen. Switch to a TTY or SSH and read: `journalctl -b -p err --no-pager`, `journalctl -k -b | grep -i -E 'nvidia|nvrm|drm'`, `uname -r`, and the kernel, module and `nvidia-utils` package versions.
2. A mismatch between the booted kernel and its module package is the first suspect. Booting the fallback kernel tests this quickly.
3. A partial upgrade is the second: `nvidia-utils` and the module package must carry the same driver version. Finish the upgrade with `sudo pacman -Syu`.
4. If the module is present and the initramfs is stale, the owner runs `sudo mkinitcpio -P`. With Limine, its hook then rebuilds the entries, see [boot-limine.md](boot-limine.md).
5. Roll back to a snapshot if none of that resolves it.

---

### Do not

1. Add `nvidia-dkms`, `nvidia-open-dkms` or another driver set on top of a prebuilt module. Two providers of the module fight, and `chwd` and the kernel packages manage the set. A driver branch change goes through `chwd`.
2. Edit the generated mkinitcpio snippets or anything under `/usr/lib/modprobe.d/`. Use `/etc/modprobe.d/`.
3. Remove `linux-firmware-nvidia`, `nvidia-utils` or `libva-nvidia-driver` as orphans.
4. Apply Arch Wiki NVIDIA instructions written for plain Arch without checking what `chwd` and `cachyos-settings` already did.
