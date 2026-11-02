# AUR, paru and makepkg

Read this before installing or updating anything from the AUR, before running `makepkg`, and when a build fails with "No module named build". The rules live in [SKILL.md](../SKILL.md).

---

### What the AUR is

The AUR holds PKGBUILD recipes written by anyone. A PKGBUILD is a shell script that runs as your user during the build, and a `.install` file runs as root at install time. Nothing is vetted. The Arch News item "Active AUR malicious packages incident" told users to review every PKGBUILD and install script change, and that advice stands. List the foreign packages on the machine with `pacman -Qm`.

---

### Rules for the agent

1. Use one AUR helper. Check which are installed with `command -v paru yay`, and keep to the one `MACHINE.md` names.
2. Search with `paru -Ss <term>`. Fetch a recipe without building it with `paru -G <pkg>`, which clones the PKGBUILD directory into the current directory. Do that in a scratch directory, never inside a project.
3. Read the PKGBUILD and every `*.install` file. Check where `source=` points (the upstream project's own release URL, not a personal server), whether checksums are `SKIP` for anything but a VCS source, whether `prepare()`, `build()` or `package()` download or execute things, and whether the `.install` file does more than refresh caches.
4. Look at votes, popularity, maintainer and last update on the AUR page. A new package with no votes, or one whose maintainer changed recently, deserves a harder look.
5. Build and install with the review step forced: `paru -S --review <pkg>`, run by the owner. The flag overrides a `SkipReview` setting. Check `/etc/paru.conf` and `~/.config/paru/paru.conf` for `SkipReview` before trusting the default.
6. Never run `makepkg` as root. Never build a PKGBUILD from a gist or a chat message.
7. AUR updates are part of the full upgrade. Do [upgrade-preflight.md](upgrade-preflight.md), then `paru -Syu`, which upgrades the repositories and the AUR together and shows PKGBUILD diffs. `paru -Sua` upgrades only the AUR part and is fine right after a complete `pacman -Syu`.
8. After a large library upgrade (Qt, KDE Frameworks, Python, ICU, Boost) some AUR packages must be rebuilt because they link against old sonames. Symptom: `cannot open shared object file` at start. Fix: `paru -S <pkg>` again after the system upgrade finished, see [partial-upgrade-and-404.md](partial-upgrade-and-404.md).

---

### The pyenv pitfall, "No module named build"

Python AUR packages build with `python -m build` and install with `installer`, using the `python-build`, `python-installer` and `python-setuptools-scm` pacman packages. Those exist only for the system Python.

1. pyenv puts its shims first in `PATH`, so `python` resolves to a shim. Check with `command -v python` and `echo "$PATH"`.
2. If `pyenv global` or a `.python-version` file names a pyenv version, the shim runs that interpreter, which has none of the pacman-installed modules.
3. The build dies with `No module named build`.

Demonstrate it without changing anything: `PYENV_VERSION=<a pyenv version> python -m build --version` fails with `No module named build`, while `PYENV_VERSION=system python -m build --version` prints the version. Verified on one host.

What to do:

1. Prefer `pyenv global system`, and select a pyenv version per project with `pyenv local <version>`, which writes `.python-version` in that directory only.
2. For one shell or one command, use `pyenv shell <version>` or `PYENV_VERSION=<version> <command>`.
3. When a build fails this way, check `pyenv version` and any `.python-version` in the build directory or a parent of it. Build with `PYENV_VERSION=system paru -S <pkg>`.
4. Do not pip-install `build` and friends into a pyenv version to make the error go away. It hides the problem and the next build uses different tools.

---

### Makedepends and orphans

`paru` and `makepkg -s` install build dependencies and leave them behind, so they show up in `pacman -Qtdq` as orphans. They are not garbage, because the next AUR build reinstalls them. Either keep them, or have paru remove them after each build with `--removemake` or `RemoveMake` in `paru.conf`. Never remove them in bulk with `--noconfirm`, see [orphans-and-cleanup.md](orphans-and-cleanup.md).

---

### Build failures

1. Read the first error, not the last. `makepkg` names the failing function: `prepare`, `build`, `check` or `package`.
2. A 404 or checksum failure while downloading sources usually means upstream moved a file. Read the AUR page comments. Never push it through with `--skipchecksums` or `--skippgpcheck`.
3. A missing dependency or `.so` is probably a partial upgrade, see [partial-upgrade-and-404.md](partial-upgrade-and-404.md).
4. Stale build state lives in the helper's clone directory, `~/.cache/paru/clone/<pkg>` for paru. Removing that one package directory forces a clean clone, with the owner's approval.
5. Check the AUR comments and the Arch forum before editing a PKGBUILD. A local edit is lost at the next update and may go unnoticed. If one is needed, tell the owner and record it in `MACHINE.md`.

---

### Reinstall survival

AUR packages do not come back from the repositories after a reinstall. If one should survive, tell the owner to add it to whatever provisions the machine, which `MACHINE.md` names.
