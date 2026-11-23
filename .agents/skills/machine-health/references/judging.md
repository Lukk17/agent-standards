# Judging a Measurement on Any OS

Contents:

- [Never-touch devices first](#never-touch-devices-first)
- [CPU temperature against the vendor maximum](#cpu-temperature-against-the-vendor-maximum)
- [RAM: configured speed against rating against vendor support](#ram-configured-speed-against-rating-against-vendor-support)
- [Mixed kits and channels](#mixed-kits-and-channels)
- [Running a memory test](#running-a-memory-test)
- [Encrypted volumes](#encrypted-volumes)
- [PATH and environment](#path-and-environment)
- [Displays: applied refresh against the monitor's maximum](#displays-applied-refresh-against-the-monitors-maximum)
- [The dual boot clock](#the-dual-boot-clock)
- [Security findings: what to hand the owner](#security-findings-what-to-hand-the-owner)

The rules that turn a measured value into a verdict and hold on Linux, macOS and Windows alike. The commands that produce the values are in the file for the operating system the machine runs. The verdict words are defined in [machine-md-format.md](machine-md-format.md), and the rules live in [SKILL.md](../SKILL.md).

---

### Never-touch devices first

Read the never-touch table in `MACHINE.md` before the first storage command. Those devices get listing level only, with the listing command the OS file names. No SMART query, no filesystem tool, no mount, even read-only, and no suggested fix.

---

### CPU temperature against the vendor maximum

Compare with the vendor's maximum, quoted from the vendor page rather than remembered. Look up the page of the exact model the machine has. As a vendor example, not the test machine, AMD's page for the Ryzen 7 7700X lists "Max. Operating Temperature (Tjmax) 95°C" (<https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700x.html>, fetched raw on 2026-11-20). Idle well below that is `ok`. Idle within 15 degrees of it is `warn`, which usually means a cooler, paste or fan curve problem the owner has to look at.

---

### RAM: configured speed against rating against vendor support

Three numbers decide the verdict, and each needs its own source.

1. Configured speed: the configured speed each slot reports, from the field the OS file names.
2. Module rating: the part number looked up on the memory vendor's specification page, which gives the XMP or EXPO speed, timings and voltage, plus the JEDEC SPD default. Quote the page and its URL.
3. CPU vendor support for that CPU, that DIMM count and that rank. Look it up on the CPU vendor's page for the exact model, quote the field and the URL, and date the fetch.

What the vendor pages look like:

1. AMD Ryzen 7 7700X, a vendor example and not the test machine. The AMD page reads "System Memory Type DDR5 Memory Channels 2 Max. Memory 128 GB System Memory Subtype UDIMM Max Memory Speed 2x1R DDR5-5200 2x2R DDR5-5200 4x1R DDR5-3600 4x2R DDR5-3600" (<https://www.amd.com/en/products/processors/desktops/ryzen/7000-series/amd-ryzen-7-7700x.html>, fetched raw on 2026-11-20). The figure depends on the DIMM count and the rank: two modules are supported at DDR5-5200, four at DDR5-3600. A page that gives one figure only gives the best case, so find the vendor's figure for the DIMM count actually installed and say where it came from.
2. Intel Core i9-14900K. Intel's specification page lists "Up to DDR5 5600 MT/s" and "Up to DDR4 3200 MT/s" with "Max # of Memory Channels 2" (<https://www.intel.com/content/www/us/en/products/sku/236773/intel-core-i9-processor-14900k-36m-cache-up-to-6-00-ghz/specifications.html>, read through a summarising fetch because the raw page answered 403, so re-read it before relying on it).

Verdicts:

| Situation | Verdict |
|---|---|
| Configured at or below the CPU vendor's figure for this DIMM count and rank, and at or below the module rating | `ok` |
| Configured above the CPU vendor's figure, for example an XMP profile on four DIMMs | `warn`. It often works, it is the first suspect for random crashes and filesystem checksum errors, and it is the owner's call |
| Configured at the JEDEC default while the modules are rated higher | `warn` for performance, the XMP or EXPO profile is off. Never `fail` |
| Configured above the module rating | `fail`, a manual overclock beyond the parts |
| Slots report different configured speeds | `fail`, the controller runs one speed and the readout is wrong or a module is not detected properly |

If `MACHINE.md` records RAM above its rated speed, mention it next to any checksum or corruption finding.

---

### Mixed kits and channels

| Check | How | Wrong looks like |
|---|---|---|
| Mixed kits | Compare `Part Number` and `Manufacturer` across slots | More than one part number, or the same size from two vendors. Memory vendors warn against it: G.Skill's `F4-3200C14D-16GTZR` page says "Do not mix memory kits. Memory kits are sold in matched kits that are designed to run together as a set. Mixing memory kits will result in stability issues or system failure" (<https://www.gskill.com/specification/165/166/1536653463/F4-3200C14D-16GTZR-EOL-Specification>, fetched raw), `warn` |
| Mixed sizes | Compare `Size` across slots | Different sizes run in a partly asymmetric mode, `warn` |
| Channels | The two slot fields that name the channel, for example `P0 CHANNEL A`. The OS file names them | Two modules both in channel A with channel B empty means single channel, about half the bandwidth, `warn` |
| Module count | Count slots with a size against the board's slot count in `MACHINE.md` | A module missing since the baseline, `fail` |

The board manual names the slots to use for two modules. Quote it rather than guessing slot order.

---

### Running a memory test

A real memory test needs a reboot and takes the machine away from the owner for an hour or more. The agent never schedules it and never reboots. Hand the steps to the owner. The steps for each operating system are in its file.

While a speed above the CPU vendor's rating is in force, suggest the owner test at the configured speed first, and at the vendor's figure second if errors appear, so the result names the cause.

---

### Encrypted volumes

Never unlock, mount or probe an encrypted volume to answer the encryption check. The state from the listing is enough.

---

### PATH and environment

A non-interactive agent shell does not read the same startup files as the owner's terminal, so its PATH is not the owner's PATH. Always measure through the owner's login shell from `MACHINE.md`, interactive and login separately, because they read different files.

The first match on PATH wins, so a version manager's shim or a second install can stand in front of the system binary without anyone deciding it.

Report the file and line for each duplicate, so the owner can remove the second source rather than the symptom. Never edit a startup file during the check. List variable names and paths only, never the value of a variable that might hold a secret.

---

### Displays: applied refresh against the monitor's maximum

The question is whether the mode in use is the best the monitor offers at its resolution. A 144 Hz monitor left at 60 Hz is the common case, and it comes from a cable, a port, a driver default or a desktop setting nobody changed.

A lower refresh can be deliberate, for example a capture card or a power choice. When `MACHINE.md` records it as the owner's choice, the verdict is `accepted`.

---

### The dual boot clock

On a machine that dual boots Linux and Windows, both must agree on what the hardware clock holds. Linux keeps it in UTC unless `LocalRTC=yes`, and Windows keeps local time unless `RealTimeIsUniversal` is set to 1. When they disagree, the clock is wrong by the time zone offset after every switch. Report a mismatch between the Linux `LocalRTC` value and the Windows registry value as `warn`, and leave the fix to `windows`, which carries the dual boot clock. That Windows keeps local time by default is from memory, high confidence, not quoted here.

---

### Security findings: what to hand the owner

Security findings go first in the reply, before performance and tidiness. For each one say what an attacker or a failure gains while it stays, what the fix changes, and whether it needs a reboot or a firmware visit. Turning Secure Boot on, enrolling keys or enabling BitLocker or FileVault can lock the owner out of an operating system or a disk when done in the wrong order, so the suggestion names the OS skill that carries the procedure, `arch-linux`, `cachyos`, `windows` or `macos`, rather than a one-line command.
