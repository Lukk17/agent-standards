# MACHINE.md Health Section

Contents:

- [Where it lives](#where-it-lives)
- [Section skeleton](#section-skeleton)
- [Verdicts](#verdicts)
- [Baseline rules](#baseline-rules)
- [Drift rules](#drift-rules)
- [Needs root and the change log](#needs-root-and-the-change-log)
- [What to do with a finding](#what-to-do-with-a-finding)
- [Reply to the owner](#reply-to-the-owner)

Read this before writing anything into `MACHINE.md`. It fixes where the Health section sits, what a baseline row holds, how drift is recorded, and what goes back to the owner. The rules live in [SKILL.md](../SKILL.md).

---

### Where it lives

`MACHINE.md` sits next to the global `AGENTS.md`: `~/.config/agents/MACHINE.md` on Linux and macOS, `%USERPROFILE%\.config\agents\MACHINE.md` on Windows. Its sections come from `global/MACHINE.md.example` in agent-standards, and that template has no Health section, so the first run adds one.

Place `### Health` directly after `### Known quirks and fixes` and before `### Owner preferences`, with a horizontal rule before it like every other section. Do not reorder or rename any existing section. If the file does not exist, stop and tell the owner to run the bootstrap prompt first, because a health baseline without the inventory has nothing to point at.

---

### Section skeleton

```markdown
### Health

Read-only checks from the `machine-health` skill. The baseline is the reference every later run compares against. Drift entries are newest first.

Baseline: `<YYYY-MM-DD HH:MM zone>` by `<agent and version>` on `<OS and version>`.

#### Baseline

| Area | Check | Value | Verdict | Source | Verified |
|---|---|---|---|---|---|
| CPU | Microcode | `0x800820d`, matches `amd-ucode <version>` | ok | `grep -m1 microcode /proc/cpuinfo`, `pacman -Q amd-ucode` | `<YYYY-MM-DD>` |

#### Drift

##### `<YYYY-MM-DD>`

1. `<Area, check>`: baseline `<value>`, now `<value>`. Verdict `<verdict>`. Evidence: `<command and the line that matters>`. Handed to the owner: `<suggested command>`, which `<what it changes>`. Undo: `<how>`.
```

The example row has the shape of a real value read on a CachyOS test machine. Replace it.

---

### Verdicts

Use exactly one per row, so the table sorts and later runs can compare.

| Verdict | Means |
|---|---|
| `ok` | Measured, within the vendor limit or the expected state |
| `warn` | Works, but outside a vendor limit, wasteful, or likely to break later, for example RAM above the CPU's rated speed, a display below its maximum refresh, `.pacnew` files waiting |
| `fail` | Broken or failing now, for example a SMART attribute counting reallocated sectors, a failed unit, a firewall that is off |
| `needs root` | The answer needs elevation. The command is in Needs root and the row stays open |
| `unknown` | The command is absent or answered nothing usable. Write the error text as the value |
| `accepted` | The owner has seen this finding and decided to keep it. Write `accepted (owner, <date>)` and the reason, so later runs do not report it as new |
| `UNVERIFIED` | The command for this OS was not executed in this run. Never a result, only a placeholder for a check still owed |

---

### Baseline rules

1. The first run on a machine writes the Baseline table and no Drift entry.
2. One row per check per device, so two disks are two rows.
3. A value the owner states, such as "the 3000 MT/s RAM setting is deliberate", goes in with Source `owner` and verdict `accepted`. No later run overwrites it.
4. A row that needs root keeps verdict `needs root` until the owner pastes the output. Then fill the value, put `owner, sudo <command>` in Source, and date it the day the owner ran it.
5. Re-baselining is the owner's call. When asked, move the old Baseline table under a `##### Superseded baseline <date>` heading inside Drift rather than deleting it, and write the new one.

---

### Drift rules

1. Every later run compares each check with its baseline row and writes one Drift entry dated from the system clock, newest first, listing only what moved or what is new. Write "No drift" when nothing moved.
2. A value that moved but stays `ok` is still drift. Record it in one line, because a slowly growing counter is how a dying disk looks.
3. Never edit a baseline row to match today. The baseline is the reference. Only the owner re-baselines.
4. A finding that was in the last Drift entry and is still there is listed again with "still present since `<date>`", so age is visible.
5. When an owner row and a measurement disagree, add the disagreement to Drift and, if it matters beyond health, to Known quirks, as the bootstrap prompt requires.

---

### Needs root and the change log

Add every root or elevated command the run could not execute to the existing Needs root section, in its format, without duplicating a line already there:

```text
needs: sudo smartctl -H -A /dev/nvme0n1          (fills: Health, Storage SMART nvme0n1)
```

Add one change log entry under today's `####` date heading, newest first, in the file's existing format:

```text
1. HH:MM Health baseline written by the machine-health skill, 31 checks, 3 warn, 1 fail, 4 needs root. No system change. Why: owner request after setup. Undo: delete the Health section.
```

For a later run, say "Health drift entry added" and name the count of moved checks.

---

### What to do with a finding

1. Do not fix it. That includes a fix that looks harmless, such as removing an orphan, merging a `.pacnew` or switching a display mode.
2. Hand it to the owner in the reply, most severe first: the finding, the evidence line, the suggested command with the shell it runs in, what it changes, and how to undo it.
3. A fix that needs root is written as a command for the owner, never run.
4. A fix that touches a never-touch device is not suggested at all. Say the device is on the list and stop.
5. If the owner then asks the agent to apply a fix, that is a separate task under the OS skill, and its own change log entry records it.

---

### Reply to the owner

Answer in this order: the path written, baseline or drift, the counts per verdict, the `fail` and `warn` findings with their suggested fixes, the Needs root lines added, and the checks that stayed UNVERIFIED with the reason. Quote vendor limits with their URL.
