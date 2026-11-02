# systemd and Journal Triage

Read this when a service failed, boot is slow or hangs, something misbehaves and you need evidence from the logs, or before changing a systemd unit. The rules live in [SKILL.md](../SKILL.md).

The first two sections are read-only. Reading the system journal as a normal user needs membership of `wheel`, `adm` or `systemd-journal`. Check with `id`.

---

### Triage order

1. What is failing now: `systemctl --failed --no-pager` and `systemctl --user --failed --no-pager`.
2. Why: `systemctl status <unit> --no-pager -l`. Note `Active:`, `Main PID` and the exit status.
3. The unit's own log for this boot: `journalctl -u <unit> -b --no-pager`, with `-p err` for errors only. For a user unit: `journalctl --user -u <unit> -b`.
4. The previous boot, when the problem ended in a crash or reboot: `journalctl -b -1 --no-pager -e`. `journalctl --list-boots` shows what is kept.
5. Errors across the whole boot: `journalctl -b -p err --no-pager`. Read around the symptom with `--since '<YYYY-MM-DD HH:MM>' --until '<YYYY-MM-DD HH:MM>'`.
6. Kernel messages: `journalctl -k -b --no-pager`. Plain `dmesg` fails for a normal user when `kernel.dmesg_restrict = 1`, so use the journal.
7. What the unit actually runs: `systemctl cat <unit>` shows the packaged file and every drop-in in order, which is also how to find the override file to edit.
8. Dependencies and ordering: `systemctl list-dependencies <unit>` and `systemctl show -p After,Requires,WantedBy <unit>`.

Always bound a query with `-b`, `--since`, `-n 200` or `-p err`. An unbounded `journalctl` pours the whole history into the context window.

---

### Reading logs honestly

1. The first error in a cascade is usually the cause and later ones are consequences. Sort by time and start from the earliest.
2. A repeated line is one event with a count: `journalctl ... | sort | uniq -c | sort -rn | head`.
3. Firewall drop lines such as `[UFW BLOCK]` are the firewall working, not a fault. Filter them out with `grep -v` when reading the kernel log.
4. Do not call a warning a fault. Correlate it with a symptom or a time, such as a package update, a boot, or a resume, before blaming it.
5. Quote the exact line you rely on, with its timestamp and unit.

---

### Slow boot

`systemd-analyze` splits the time into firmware, loader, kernel, initrd and userspace. Use `systemd-analyze blame` and `systemd-analyze critical-chain` for the userspace part. On an encrypted root the initrd figure includes the time the owner spent typing the passphrase, so do not treat a large initrd number as a fault before checking when the prompt appeared: `journalctl -b` around the `systemd-cryptsetup` lines shows the timestamps.

---

### Changing a unit

1. Never edit the file under `/usr/lib/systemd/system/`, a package owns it.
2. Use a drop-in. `sudo systemctl edit <unit>` creates `/etc/systemd/system/<unit>.d/override.conf` and opens an editor, so the owner runs it. For a scripted change, the owner writes the drop-in file, then runs `sudo systemctl daemon-reload`.
3. In a drop-in, a list setting such as `ExecStart=` must first be cleared with an empty `ExecStart=` line before the new one, otherwise systemd refuses a second start command for most service types.
4. Check with `systemctl cat <unit>` and `systemd-analyze verify <unit>` before restarting. Restart with `sudo systemctl restart <unit>`, then read `systemctl status` and the journal.
5. Enabling and disabling change boot behaviour. Snapshot first for anything related to boot, login, networking or the display manager.
6. User services live in `~/.config/systemd/user/` and `systemctl --user` needs no root. Packaged ones are under `/usr/lib/systemd/user/`.
7. Packaged systemd settings under `/usr/lib/systemd/*.conf.d/`, such as journald size, timeouts, limits, the zram generator and oomd, are overridden in `/etc/systemd/*.conf.d/`, see [config-safety.md](config-safety.md).

---

### Discover the units that matter

Instead of a fixed list, ask the machine and record the answer in `MACHINE.md`:

```bash
systemctl list-unit-files --state=enabled --no-pager
```

```bash
systemctl list-timers --all --no-pager
```

```bash
systemctl --user list-unit-files --state=enabled --no-pager
```
