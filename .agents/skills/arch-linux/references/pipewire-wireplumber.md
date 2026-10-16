# PipeWire, WirePlumber and ALSA

Read this for any audio problem: no sound, the wrong output, a volume that resets after a reboot, a muted jack, a device that does not show up. The rules live in [SKILL.md](../SKILL.md).

---

### The stack

| Layer | Component | What it does |
|---|---|---|
| Hardware | ALSA cards, listed by `cat /proc/asound/cards` or `aplay -l` | Card numbers can change between boots, so address a card by its name: `amixer -c <card name> ...` |
| Kernel mixer state | `alsa-restore.service` from `alsa-utils` | Restores `/var/lib/alsa/asound.state` at boot. Saved with `sudo alsactl store` |
| Server | PipeWire with `pipewire-pulse` and `pipewire-alsa` | PulseAudio clients such as `pactl` talk to PipeWire |
| Session manager | WirePlumber | Chooses devices, ports and defaults, and applies rules |

Discover the versions with `pacman -Q pipewire wireplumber alsa-utils` and the default devices with `wpctl status`. Record a custom audio fix in `MACHINE.md`, because nothing else will tell the next agent it exists.

---

### Inspect

Read-only unless noted.

1. Overview: `wpctl status`. A `*` marks the default sink or source. Ids change per session.
2. One object: `wpctl inspect <id>` for a device, sink or source. The properties show which rules are active, for example `api.alsa.soft-mixer`.
3. Volume: `wpctl get-volume @DEFAULT_AUDIO_SINK@`. These change live state and are fine on request: `wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.6`, `wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle`, `wpctl set-default <id>`.
4. Hardware mixer: `amixer -c <card name> scontrols` and `amixer -c <card name> sget '<control>'`. Look at `Master`, `Headphone`, `Front`, `Line` and `Auto-Mute Mode` where the codec has them.
5. The whole graph: `pw-dump | head`, `pw-cli ls Node`, and `pw-top` for live load, which needs a terminal.
6. The Pulse view: `pactl list short sinks`, `pactl info`.
7. Logs: `journalctl --user -u wireplumber -u pipewire -u pipewire-pulse -b --no-pager`.

---

### Restart without rebooting

WirePlumber configuration changes apply after a restart of the user services, which interrupts audio briefly and can pause a call. Ask first.

```bash
systemctl --user restart wireplumber pipewire pipewire-pulse
```

---

### Where configuration goes

1. User drop-ins: `~/.config/wireplumber/wireplumber.conf.d/*.conf`. All changes go here. Files are read in name order. The format is SPA-JSON, close to JSON, with `=` or `:` and no commas required.
2. System level: `/etc/wireplumber/`, only for a change that must apply to every user.
3. Packaged defaults: `/usr/share/wireplumber/`. Read them as documentation, never edit them, see [config-safety.md](config-safety.md).
4. PipeWire and `pipewire-pulse` follow the same layout under `~/.config/pipewire/`.
5. Look the syntax up before writing it: `man wireplumber`, the files under `/usr/share/wireplumber/`, and `wiki-search wireplumber` where available. WirePlumber 0.4 and 0.5 use different configuration formats, so an older forum snippet written in Lua is wrong for 0.5.

---

### Pattern: mixer state lost at boot, or a jack that mutes another output

On some onboard HDA codecs two symptoms appear together: the levels saved with `alsactl store` are back to defaults after every boot, and plugging or unplugging one jack mutes another output. A drop-in that targets only the affected card fixes both. Find the card's `device.name` with `wpctl status` and `wpctl inspect <id>`, then write, for example, `~/.config/wireplumber/wireplumber.conf.d/51-<card>.conf`:

```text
monitor.alsa.rules = [
  {
    matches = [ { device.name = "<alsa_card.device-name-from-wpctl>" } ]
    actions = {
      update-props = {
        api.alsa.soft-mixer = true
        api.acp.auto-port = false
      }
    }
  }
]
```

1. `api.alsa.soft-mixer = true` keeps volume in software, so WirePlumber does not rewrite the hardware controls when the card appears, which would overwrite what `alsa-restore.service` restored.
2. `api.acp.auto-port = false` stops the ACP card profile code from switching ports on jack detection, which can select a headphone port and mute a line output.

Verified once, on one board, by reading both properties back with `wpctl inspect` after the restart. The mechanism is UNVERIFIED in general. Confirm by ear and by a reboot, and record the file in `MACHINE.md`.

Procedure when mixer controls are wrong:

1. Look with `amixer -c <card name> scontents`, or `alsamixer -c <card name>` in the owner's terminal.
2. Change one control, for example `amixer -c <card name> sset 'Line' unmute`, and test by ear.
3. Persist with `sudo alsactl store`, a root action because it writes `/var/lib/alsa/asound.state`.
4. Reboot once to confirm the state comes back.

---

### Common problems

| Symptom | First checks |
|---|---|
| No sound at all | `wpctl status`: is there a sink, is it the `*` default, is it `[MUTED]`. Then `amixer -c <card name> sget Master`, and whether the application's stream is routed to another sink |
| Sound on the wrong device after boot or monitor wake | `wpctl status`, then `wpctl set-default <id>`. HDMI and DisplayPort sinks appear only while the monitor is on |
| Volume jumps or resets | the soft-mixer pattern above, `alsactl store`, or an application with its own volume |
| Crackling or dropouts | `pw-top` and its ERR counts, `journalctl --user -u pipewire -b`, recent scheduler or power profile changes |
| Missing device after an upgrade | `systemctl --user status wireplumber`, and `pacman -Q pipewire wireplumber libpipewire` must show one version family, see [partial-upgrade-and-404.md](partial-upgrade-and-404.md) |
