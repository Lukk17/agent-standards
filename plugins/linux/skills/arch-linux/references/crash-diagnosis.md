# Diagnosing a Crash

Read this when a program segfaulted, aborted, disappeared, or a "process crashed" notification appeared. The rules live in [SKILL.md](../SKILL.md).

The goal is an honest account of what happened, not a plausible story. Diagnosis reads and does not fix. The only thing to clean up afterwards is your own temporary core file.

---

### 1. Establish the facts

1. `coredumpctl list --no-pager` shows whether this is a one-off or a pattern. Repeated crashes of one program, or several programs dying together, point somewhere different from a single failure.
2. `coredumpctl info <pid>` for the entry. Note the signal (SIGSEGV, SIGABRT, SIGBUS), the executable, the package version, the command line and the time. The command line often shows what the process was working on, and is frequently the whole answer.
3. Find the owning package with `pacman -Qo <exe>`, and when it last changed with `grep -a '<pkg>' /var/log/pacman.log | tail`. A crash that begins right after an update points at the update.

---

### 2. Rule out the boring causes first

1. Memory pressure: `free -h`, and the journal for the OOM killer, `journalctl -b -k | grep -i -E 'out of memory|oom'`. If `systemd-oomd` runs, also `journalctl -b -u systemd-oomd`. A process killed for memory is not a bug in that process.
2. A full disk or a read-only filesystem: `df -h`, `findmnt -o TARGET,OPTIONS /`.
3. The GPU, for a graphical program: driver errors in `journalctl -k -b | grep -i -E 'nvidia|nvrm|xid|amdgpu|i915|drm'`.
4. A `PATH` or pyenv mix-up for a Python program, see [aur-and-makepkg.md](aur-and-makepkg.md), or a missing library after a partial upgrade, see [partial-upgrade-and-404.md](partial-upgrade-and-404.md).

---

### 3. Correlate against the timeline

The crash timestamp is the most underused evidence. Compare it with:

1. Modification times. A file whose mtime falls in the same second as the crash suggests the trigger: `find ~ -xdev -newermt '<time-1s>' ! -newermt '<time+1s>' 2>/dev/null | head`.
2. The journal around that moment: `journalctl --since '<time-30s>' --until '<time+30s>' --no-pager`.
3. Recent package updates, above, and recent changes in the `MACHINE.md` change log.
4. Your own commands. A program that aborts while writing into a pipe that closed early, for example output cut by `head`, can leave a core that looks like a bug. Check whether the crash time matches something you ran.

---

### 4. Read the whole core, not only frame 0

Other threads show what work was in flight: loaders, IPC readers, GPU queues. Note third party code in the address space, such as plugins, extensions or out of tree drivers, but do not blame it without evidence that it is implicated.

---

### 5. Symbolize when possible

Check for debuginfod with `echo "$DEBUGINFOD_URLS"` and the files in `/etc/debuginfod/`. Arch publishes `https://debuginfod.archlinux.org`, and some derivatives add their own server. Check that `gdb` is installed with `pacman -Q gdb`.

```bash
core=$(mktemp -t crash-XXXXXX.core); trap 'rm -f "$core"' EXIT; coredumpctl dump <pid> --output="$core"; gdb -q <executable> "$core" -batch -ex 'set debuginfod enabled on' -ex 'bt'
```

`coredumpctl gdb <pid>` is the interactive form and needs a real terminal, so the owner runs it.

A core file is a copy of the process memory and can hold passwords, tokens and private documents. Write it to a fresh `mktemp` path, never a predictable shared one, delete it when done, and never paste or attach it anywhere.

Many packages publish no debug symbols, and AUR packages have no debuginfod coverage. When frames stay unresolved, say so and do not invent function names. An unsymbolized stack still has shape: which library each frame belongs to, and whether the crash came from a signal handler, the main loop or a worker thread.

---

### 6. Report

1. What crashed and what it was doing.
2. The most likely mechanism, separating what the evidence proves from what is inferred.
3. Whether user data was lost, and where it can be recovered, checking Trash and application autosave first.
4. Whether it will recur, and what would avoid or fix it.

If the cause is ambiguous, say so. Report a bug upstream only with the owner's agreement, after searching the tracker for duplicates including closed issues. A closed-as-fixed match that still reproduces is a regression and worth reporting. Never post a comment that only says it happens to you too.

---

### Offering a mute

After the diagnosis, and never in place of a fix, you may offer to silence crash notifications for one program. On KDE that is a `kde-plasma` topic, because the crash handler and notifications are Plasma configuration.
