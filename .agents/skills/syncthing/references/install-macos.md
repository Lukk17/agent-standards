# Install and Start on macOS

Read this before installing Syncthing on a Mac, making it start at login, or answering the firewall prompt for it. What is the same on every operating system, the command that prints the state directory, the firewall ports and the first check after the start, is in [install-and-start.md](install-and-start.md). The rules live in [SKILL.md](../SKILL.md). Every command here is UNVERIFIED.

Sources: https://formulae.brew.sh/formula/syncthing, https://formulae.brew.sh/cask/syncthing-app and https://docs.syncthing.net/users/firewall.html.

---

### State directory

The configuration and the database are in `~/Library/Application Support/Syncthing`.

---

### Install and start

Install the formula and start it with `brew services`, which writes a LaunchAgent for the user. The formula's service block, read from formulae.brew.sh, runs `syncthing --no-browser --no-restart`, keeps it alive, and logs to `$(brew --prefix)/var/log/syncthing.log`. Homebrew never runs under `sudo`.

```bash
brew install syncthing
```

```bash
brew services start syncthing
```

```bash
brew services info syncthing
```

The cask `syncthing-app` is the menu bar application, which brings its own copy of Syncthing and starts it itself. Install one of the two, never both, or two instances fight over the same configuration and ports.

---

### Firewall

The ports are listed in [install-and-start.md](install-and-start.md#firewall-ports). When the application firewall is on, macOS asks once whether `syncthing` may accept incoming connections. The owner answers that prompt, or allows it in System Settings, Network, Firewall, Options. UNVERIFIED.
