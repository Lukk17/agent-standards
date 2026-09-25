# Vault discovery

Where Obsidian keeps its vault list on each platform, what the file holds, and how to read it without guessing.

---

### Where obsidian.json lives

Obsidian stores global settings, including the vault list, in a per-user system folder. The file is always
`obsidian.json` inside a folder named `obsidian`.

| Platform | Path | Source |
|---|---|---|
| Windows | `%APPDATA%\obsidian\obsidian.json` | Obsidian help, measured on Windows 11 |
| macOS | `~/Library/Application Support/obsidian/obsidian.json` | Obsidian help |
| Linux, native package or AppImage | `$XDG_CONFIG_HOME/obsidian/obsidian.json`, else `~/.config/obsidian/obsidian.json` | Obsidian help |
| Linux, Flatpak | `~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json` | notesmd-cli source |
| Linux, Snap | `~/snap/obsidian/current/.config/obsidian/obsidian.json` | notesmd-cli source |
| WSL | the Windows path, reached through `/mnt/<drive>/...` | notesmd-cli source |

Obsidian's help writes the Windows folder as `%APPDATA%\Obsidian\`. Windows paths are case insensitive, so either
spelling finds it. Linux paths are case sensitive, and the folder there is lowercase `obsidian`.

`notesmd-cli` searches the same list in the same order on Linux: the XDG path first, then Flatpak, then Snap, then
any numbered Snap revision folder. Under WSL it asks `cmd.exe` for `%APPDATA%` and reads the Windows file.

Sources, fetched 2026-09-25:

- `https://help.obsidian.md/data-storage`, section Global settings
- `https://github.com/Yakitrak/notesmd-cli/blob/main/pkg/config/obsidian_path.go`

---

### What the file holds

A `vaults` object keyed by an opaque id. Each entry carries `path`, the absolute folder path, `ts`, a timestamp, and
`open`, which is `true` on the vault Obsidian currently has open. The vault name the CLI uses is the last folder of
`path`.

---

### List vaults with the CLI

Works the same on every platform once `notesmd-cli` is installed. It prints each vault name and path, and marks the
default.

```bash
notesmd-cli list-vaults
```

For a script, ask for JSON:

```bash
notesmd-cli list-vaults --json
```

Print only the default vault's path:

```bash
notesmd-cli list-vaults --default --path-only
```

The CLI output does not say which vault is open in the app. For that, read `obsidian.json` directly as below.

---

### Read the file directly on Windows

PowerShell, printing each vault's path and whether it is open:

```powershell
(Get-Content -Raw (Join-Path $env:APPDATA 'obsidian\obsidian.json') | ConvertFrom-Json).vaults.PSObject.Properties.Value | Select-Object path, open
```

---

### Read the file directly on macOS

```bash
python3 -c 'import json,os; d=json.load(open(os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json"))); [print(v["path"], v.get("open", False)) for v in d["vaults"].values()]'
```

---

### Read the file directly on Linux

Find which of the known locations exists first:

```bash
ls -1 "${XDG_CONFIG_HOME:-$HOME/.config}/obsidian/obsidian.json" "$HOME/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json" "$HOME"/snap/obsidian/*/.config/obsidian/obsidian.json 2>/dev/null
```

Then read the one it printed, substituting its path:

```bash
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); [print(v["path"], v.get("open", False)) for v in d["vaults"].values()]' "<path-printed-above>"
```

---

### A headless machine with no Obsidian installed

There is no vault list until something writes one. Register the folder with the CLI, which creates the file at the
platform's config location:

```bash
notesmd-cli add-vault "<absolute-path-to-vault>" --set-default
```

Give an absolute path. The CLI does not expand `~`.
