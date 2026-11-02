# konsave: Backup and Restore

konsave saves the Plasma configuration files it is told about as a named profile, exports a profile to a `.knsv` archive, and applies one back. The rules live in [SKILL.md](../SKILL.md).

---

### Discover how it is installed

```bash
command -v konsave
```

```bash
pacman -Qo "$(command -v konsave)"
```

konsave can come from a distribution package or from pipx. Keep to one source, because a second install shadows the first on `PATH`. The owner's saved profile name and the path of its exported archive belong in `MACHINE.md`.

---

### Flags

Verified from `konsave --help` on one host:

| Task | Command |
|---|---|
| List profiles | `konsave -l` |
| Save the current configuration as a profile | `konsave -s <name>`, with `-f` to overwrite |
| Apply a profile | `konsave -a <name>` |
| Remove a profile | `konsave -r <name>` |
| Export to a `.knsv` archive | `konsave -e <name> [-d <dir>] [-n <archive-name>] [-f]` |
| Import a `.knsv` archive | `konsave -i <path>` |
| Version | `konsave -v` |
| Wipe all profiles | `konsave -w`, never |

Only `-l`, `-v` and `--help` were run. On the first run even `konsave -l` creates `~/.config/konsave/conf.yaml` and an empty `~/.config/konsave/profiles/`, so a listing is not entirely free of side effects.

---

### Restore a profile from an archive

UNVERIFIED. Snapshot the current state first, so the apply can be undone:

```bash
konsave -s backup-"$(date +%Y%m%d)" -f
```

```bash
konsave -i <path to profile>.knsv
```

```bash
konsave -a <profile name>
```

Then log out and in. `konsave -a` replaces the files listed in `~/.config/konsave/conf.yaml`, so anything changed since the profile was saved is lost, which is why the backup comes first.

---

### Save and export

UNVERIFIED:

```bash
konsave -s <profile name> -f
```

```bash
konsave -e <profile name> -f -d <directory>
```

If the export target is a file tracked by git, for example in a provisioning repository, exporting over it changes a committed file. Confirm with the owner first.

---

### Limits

konsave copies configuration files, not packages. A widget or theme the profile references must be installed before the profile is applied, or its panel slot comes up empty, see [widget-plugin-ids.md](widget-plugin-ids.md).
