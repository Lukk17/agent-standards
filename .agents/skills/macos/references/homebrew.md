# Homebrew

Contents:

- [Install order](#install-order)
- [Prefix and support](#prefix-and-support)
- [Never sudo brew](#never-sudo-brew)
- [Formula or cask](#formula-or-cask)
- [Upgrades](#upgrades)
- [Brewfile](#brewfile)
- [brew services](#brew-services)
- [Diagnose](#diagnose)

Read this before installing, upgrading or removing software, or before writing a Brewfile. The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: the Homebrew documentation in the `Homebrew/brew` repository, `docs/Installation.md`, `docs/FAQ.md`, `docs/Manpage.md` and `docs/Brew-Bundle-and-Brewfile.md`, fetched raw.

---

### Install order

This is rule 2 in [SKILL.md](../SKILL.md), and it decides the route before anything else on this page does.

1. Homebrew for everything it carries: a formula for a command line tool, a cask for a GUI application. Search with `brew search <term>` and confirm the kind with `brew info <name>`, as under "Formula or cask" below.
2. Only when Homebrew has neither a formula nor a cask, the App Store or the vendor's own installer. The App Store route from a terminal is `mas`, which is itself a formula: formulae.brew.sh lists `mas` as "Mac App Store command-line interface", installed with `brew install mas`. Every `mas` subcommand is UNVERIFIED here.
3. A vendor installer, a DMG or a pkg, is downloaded from the vendor's site, and a pkg that asks for an administrator password is the owner's to run.

An application already installed another way stays with that route. An app installed from the vendor's DMG and later as a cask leaves two copies and two update paths.

---

### Prefix and support

`docs/Installation.md`: "The script installs Homebrew to its default prefix (`/opt/homebrew` for Apple Silicon and `/home/linuxbrew/.linuxbrew` for Linux) so that you don't need sudo after Homebrew's initial installation". The same page lists "An Apple Silicon CPU; using a 64-bit Intel CPU is a Tier 3 configuration", and older Intel Macs used `/usr/local` as the prefix.

```bash
brew --prefix
```

```bash
brew config
```

Record the prefix in `MACHINE.md`. A script that hardcodes `/usr/local/bin` or `/opt/homebrew/bin` breaks on the other architecture, so resolve paths with `brew --prefix <formula>`.

---

### Never sudo brew

`docs/FAQ.md`, "Why does Homebrew say sudo is bad?": "Homebrew runs formula builds and installations as the owning account because upstream build scripts should not have unrestricted system access." Some casks and system services still ask for an administrator password through their own installer, which the owner answers.

---

### Formula or cask

| Kind | What it is | Command |
|---|---|---|
| Formula | command line software built or bottled by Homebrew, installed under the prefix | `brew install <formula>` |
| Cask | a vendor's macOS app, pkg or binary, usually placed in `/Applications` | `brew install --cask <cask>` |

1. Search both with `brew search <term>`, and read `brew info <name>` before installing, which names the kind, the version, the dependencies and caveats.
2. A GUI application is a cask. A command line tool that also ships as an app is usually a formula, so check which one the owner wants.
3. One manager per application, as set out under "Install order" above.

---

### Upgrades

```bash
brew update
```

```bash
brew outdated
```

```bash
brew upgrade <name>
```

Casks that update themselves are skipped by default. `docs/Manpage.md`, `brew upgrade`: `--greedy` "Also include outdated casks with `version :latest` and `auto_updates true` casks that would otherwise be skipped." Use it deliberately, because it can replace an app the vendor's own updater already manages.

`brew cleanup` removes old versions and cache. Run `brew cleanup -n` first, which prints what it would remove.

---

### Brewfile

`docs/Brew-Bundle-and-Brewfile.md`: "`brew bundle dump` is Homebrew's installed-state snapshot command: it records supported installed formulae, casks, taps and other package types as a `Brewfile`."

```bash
brew bundle dump --file=<path>/Brewfile
```

```bash
brew bundle check --file=<path>/Brewfile
```

```bash
brew bundle install --file=<path>/Brewfile
```

`brew bundle check` says whether an install would do anything. If the Brewfile lives in a repository, a `dump` over it changes a tracked file, so confirm with the owner.

---

### brew services

`docs/Manpage.md`, `brew services`: "If `sudo` is passed, operate on `/Library/LaunchDaemons` or `/usr/lib/systemd/system` (started at boot). Otherwise, operate on `~/Library/LaunchAgents` or `~/.config/systemd/user` (started at login)."

```bash
brew services list
```

```bash
brew services start <formula>
```

Prefer the per-user form. A boot-time service under `sudo` is the owner's decision. The plist it writes is an ordinary launchd job, see [launchd.md](launchd.md).

---

### Diagnose

`brew doctor` reports common problems with the installation. Read its warnings, and fix only what relates to the problem at hand, because some warnings are informational on a working system.
