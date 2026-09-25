# Installing notesmd-cli

`notesmd-cli` is the project formerly named `obsidian-cli`, by Yakitrak, written in Go and MIT licensed. Each release
ships prebuilt archives for Windows amd64 and arm64, Linux amd64 and arm64, and one universal macOS archive, plus a
`checksums.txt`.

Sources, fetched 2026-09-25:

- `https://github.com/Yakitrak/notesmd-cli`, README sections Install and Migrating from Obsidian CLI
- `https://github.com/Yakitrak/notesmd-cli/releases/tag/v0.3.7`, the latest release, published 2026-09-01

No winget package exists: `winget search notesmd` and `winget search obsidian-cli` both returned no match on
2026-09-25.

---

### Windows with Scoop

The route the README documents. In PowerShell:

```powershell
scoop bucket add scoop-yakitrak https://github.com/yakitrak/scoop-yakitrak.git
```

```powershell
scoop install notesmd-cli
```

---

### Windows from a release archive

For a machine without Scoop. The archive is a `.tar.gz`, which the `tar` built into Windows 10 and later unpacks.
Download it with the GitHub CLI, into a folder of your choice:

```powershell
gh release download --repo Yakitrak/notesmd-cli --pattern '*windows_amd64.tar.gz' --pattern checksums.txt
```

Compare the hash with the line for the same file in `checksums.txt`:

```powershell
Get-FileHash -Algorithm SHA256 (Get-Item *windows_amd64.tar.gz)
```

Unpack `notesmd-cli.exe` into a folder already on your `PATH`, for example a per-user tools folder:

```powershell
tar -xzf (Get-Item *windows_amd64.tar.gz).Name -C "$env:LOCALAPPDATA\Programs\notesmd-cli" notesmd-cli.exe
```

Create that target folder first if it does not exist, and add it to the user `PATH` if it is new. Pass the archive
by its bare name, as above: the GNU `tar` that Git for Windows puts on the `PATH` reads a full `C:\...` archive path
as a remote host and fails. Use the `windows_arm64` archive on an Arm machine.

---

### macOS and Linux with Homebrew

The route the README documents for both platforms:

```bash
brew tap yakitrak/yakitrak
```

```bash
brew install yakitrak/yakitrak/notesmd-cli
```

---

### Arch Linux

Prebuilt binary from the AUR:

```bash
yay -S notesmd-cli-bin
```

---

### Linux from a release archive

For any distribution without Homebrew. Download with the GitHub CLI:

```bash
gh release download --repo Yakitrak/notesmd-cli --pattern '*linux_amd64.tar.gz' --pattern checksums.txt
```

Check the hash against `checksums.txt`:

```bash
sha256sum --ignore-missing -c checksums.txt
```

Unpack the binary into `~/.local/bin`, which has to be on your `PATH`:

```bash
tar -xzf notesmd-cli_*_linux_amd64.tar.gz -C "$HOME/.local/bin" notesmd-cli
```

Use the `linux_arm64` archive on an Arm machine. On macOS the same steps work with the `darwin_all` archive and
`shasum -a 256 -c` in place of `sha256sum`.

---

### Any platform from source

Needs Go. The README says Go 1.19 or later, but `go.mod` on the main branch declares `go 1.25.8`, so use a current
Go release. The module path is `github.com/Yakitrak/notesmd-cli` with `main.go` at its root:

```bash
go install github.com/Yakitrak/notesmd-cli@latest
```

The README documents `git clone` and `go build` rather than `go install`. The Go module proxy resolves `@latest` to
v0.3.7 and `go.mod` has no `replace` directive, so `go install` should work, but it was not run here.

---

### Check the install

```bash
notesmd-cli --version
```

---

### Migrating from obsidian-cli

Remove the old package first, with the same manager that installed it, for example `scoop uninstall obsidian-cli`
or `brew uninstall obsidian-cli`. The CLI's own preferences, which hold the default vault, moved from an
`obsidian-cli` folder to a `notesmd-cli` folder under the user config directory: `%APPDATA%` on Windows,
`~/.config` on Linux, `~/Library/Application Support` on macOS. Setting the default vault again is the simplest
migration:

```bash
notesmd-cli set-default-vault "<vault-name>"
```
