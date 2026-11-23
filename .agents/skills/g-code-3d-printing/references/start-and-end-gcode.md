# Start and End G-code

The heat-up, start and end rules that hold on every firmware, with their Pass and Fail G-code. The form the start sequence takes on each firmware is in [klipper-macros.md](klipper-macros.md) and [marlin.md](marlin.md). The motion rules live in [motion-rules.md](motion-rules.md).

---

### Thermal safety

Never override or disable firmware thermal runaway protection from G-code. It is the feature that stops a detached thermistor from turning into a fire. Use the blocking heat commands before any extrusion: `M109` waits for the hotend, `M190` waits for the bed. The non-blocking `M104` and `M140` are for starting a heat-up early, never as the only heat command before extruding, because cold extrusion shreds filament and strips the extruder gear.

Pass:

```gcode
M140 S60
M104 S215
M190 S60
M109 S215
```

Fail:

```gcode
M104 S215
G1 E10 F300
```

Respect the hardware ceiling: a PTFE-lined hotend stays at or below 230 C, because PTFE decomposition starts above 240 C and off-gasses. An all-metal hotend follows the manufacturer's stated maximum. Tune the hotend PID before committing a new filament profile, with the firmware's own command: `M303` on Marlin, in [marlin.md](marlin.md#pid-tuning), and `PID_CALIBRATE` on Klipper, which has no `M303`, in [klipper-macros.md](klipper-macros.md#pid-tuning).

---

### Start G-code, bed mesh and purge line

The sequence is fixed: home, heat to the real target, level, purge outside the part, then print. Never hard-code a Z-offset, read it from the printer's saved configuration. Never purge over the area the part will occupy.

The mesh loads after the heat, because the bed changes shape as it warms.

On Klipper this sequence is the body of the `START_PRINT` macro in `printer.cfg`, written out in [klipper-macros.md](klipper-macros.md). On Marlin, which has no macros, the same sequence is the slicer start G-code itself, written out in [marlin.md](marlin.md).

---

### End G-code

The matching end sequence retracts, lifts, parks clear of the part, and cuts the heaters and motors.

Pass:

```gcode
M400
G91
G1 E-4 F2100
G1 Z10 F600
G90
G1 X5 Y200 F6000
M104 S0
M140 S0
M106 S0
M84 X Y E
M117 Print complete
```

Fail, an end sequence that leaves the nozzle sitting on the part with the heaters live:

```gcode
M104 S0
M84
```

The pair belongs together in the slicer profile and in version control. The end sequence retracts before it lifts, so no ooze is dragged across the top surface, and it leaves the Z motor energised so the gantry cannot drop.
