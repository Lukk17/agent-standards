# Package Managers: winget, then Chocolatey, then the Vendor Installer

Read this before installing, upgrading, exporting or removing software. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED unless marked.

---

### Install order

This is rule 3 in [SKILL.md](../SKILL.md), and it decides the manager before anything else on this page does.

1. winget. Search it first, by exact id, as shown under winget below.
2. Chocolatey, only when winget has no package for the application.
3. The vendor's own installer, only when neither winget nor Chocolatey has it. Download it from the vendor's site and hand the install to the owner.
4. Scoop only when the owner asks for it by name. It is never a fallback the agent picks.

An application that is already installed stays with the manager it came from, and so does one `MACHINE.md` assigns to a manager. Check with `winget list` and `choco list` before installing. An app installed by Chocolatey and later upgraded by winget ends up with two records and two upgrade paths.

---

### The managers

| Manager | Scope and rights | Place in the order | Source |
|---|---|---|---|
| winget | per package, user or machine, elevation only when the installer asks | first, shipped in App Installer on Windows 10 1809 and later and on Windows 11 | `https://learn.microsoft.com/en-us/windows/package-manager/winget/` |
| Chocolatey | machine wide under `%ProgramData%\chocolatey`, needs an administrative shell | second, for packages winget lacks | `https://docs.chocolatey.org/en-us/choco/setup/` |
| Scoop | per user under `C:\Users\<user>\scoop`, no admin | only on the owner's request | `https://github.com/ScoopInstaller/Scoop` |

Check which are present with `Get-Command winget, choco, scoop -ErrorAction SilentlyContinue` in `pwsh`.

---

### winget

Microsoft Learn, "Use WinGet to install and manage applications": "When running WinGet without administrator privileges, some applications may require elevation to install. When the installer runs, Windows will prompt you to elevate." and "When running WinGet in an Administrator Command Prompt, you will not see elevation prompts if the application requires it."

Search, then install by exact id from one source. The `install` page says "The best way to limit the selection to one file is to use the id of the application combined with the exact query option":

```powershell
winget search <name>
```

```powershell
winget install --id Git.Git -e --source winget
```

1. `--scope user` or `--scope machine` chooses the install target where the installer supports both. Leave it unset when unsure.
2. `--silent` with `--accept-package-agreements` and `--accept-source-agreements` gives a non-interactive install. The page notes the package agreement flag covers "the package's own license terms only".
3. `--override` passes a string straight to the installer and replaces winget's own arguments. Use `--custom` to add arguments instead.
4. Never pass `--ignore-security-hash`, which the page calls "Not recommended".
5. Upgrades: `winget upgrade` lists, `winget upgrade --id <id> -e` upgrades one. Prefer one at a time over `--all`, so a failure names its package.
6. Hold a version with `winget pin add --id <id>`. Back up and restore a set with `winget export -o <file>` and `winget import -i <file>`.
7. Logs live under `%LOCALAPPDATA%\Packages\Microsoft.DesktopAppInstaller_8wekyb3d8bbwe\LocalState\DiagOutputDir`. That directory was confirmed to exist on a mounted Windows 11 disk, read-only.
8. On a fresh account winget can be missing until the Store registers App Installer. The page gives `Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe` to request registration.

---

### Chocolatey

From "Setup / Install" on docs.chocolatey.org: "First, ensure that you are using an administrative shell", and "most things you do on Windows require administrative rights". Every Chocolatey install therefore goes to the owner's elevated terminal.

```powershell
choco install <package> -y
```

```powershell
choco upgrade <package> -y
```

1. Chocolatey CLI 2.0 changed `choco list`. From "Upgrading to Chocolatey v2": the list command "cannot be used to query remote sources. You must instead use the `choco search` command", and `--local-only` was removed with the error "Invalid argument --local-only". `choco list` shows installed packages only.
2. A package is a script that downloads and runs a vendor installer. Read the package page and its install script before trusting it, as with any third party code.
3. Chocolatey's download cache and its HTTP metadata cache are different things. Ask `choco <command> --help` what a cache subcommand actually clears before relying on its name.

---

### Scoop

From the Scoop README: "Run the following commands from a regular (non-admin) PowerShell terminal to install Scoop", followed by `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` and `Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression`. It installs to `C:\Users\<YOUR USERNAME>\scoop`. "The `main` bucket is installed by default", and `extras` holds apps that do not meet the main bucket's criteria.

```powershell
scoop bucket add extras
```

```powershell
scoop install <app>
```

Scoop never needs elevation for its own installs, so an agent can run it once the owner has asked for Scoop. The install line pipes a remote script into `Invoke-Expression`, so the owner decides whether to run it.

---

### Store apps and per-user installs

Some applications install per user from the Store or from a per-user installer. They do not appear in a machine wide inventory and are not upgraded by an elevated session running as another account. Check both scopes with `winget list` from the owner's own unelevated terminal.
