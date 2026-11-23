# Marlin

What changes when the printer runs Marlin, which has no macros. The rules that hold on every firmware are in [SKILL.md](../SKILL.md) and [start-and-end-gcode.md](start-and-end-gcode.md). The linear advance command `M900 K<value>` and the `T0` and `T1` tool-change sequences are in [calibration-and-profiles.md](calibration-and-profiles.md).

---

### The start sequence is the slicer start G-code

On Marlin, which has no macros, the start sequence, home, heat to the real target, level, purge outside the part, then print, is the slicer start G-code itself. The temperatures are written as the slicer placeholders `{bed_temperature}` and `{first_layer_temperature}`. The lines, in order, for a 220 x 220 bed:

1. Declare the modes: `G90`, then `M83`.
2. Start the heat-up early: `M140 S{bed_temperature}`, then `M104 S{first_layer_temperature}`.
3. Home: `G28`.
4. Wait for the real targets: `M190 S{bed_temperature}`, then `M109 S{first_layer_temperature}`.
5. Level with the levelling command of the Marlin build, named below. It runs after the heat, because the bed changes shape as it warms.
6. `G92 E0`, then `G1 Z5 F600`.
7. Purge outside the part: `G1 X1.0 Y20 Z0.3 F5000`, `G1 E10 F300`, `G1 X1.0 Y180 E25 F1500`, `G1 X1.4 Y180 Z0.3 F5000`, then `G1 X1.4 Y20 E40 F1500`.
8. `G92 E0`, then `G1 Z2 F3000`.

The levelling command of step 5 depends on the build:

1. Bilinear levelling with a probe such as a BLTouch: `G29`. The Marlin page https://marlinfw.org/docs/gcode/G029-abl-bilinear.html says "Using an electronic probe Marlin can probe the entire bed with a single G29 command" and "The printer must be homed with G28 before G29".
2. UBL: `G29 L0` then `G29 J`. The Marlin page https://marlinfw.org/docs/features/unified_bed_leveling.html gives them as "Load UBL mesh values from slot 0" and "Probe 3 points and tilt the mesh to the plane", and adds "This can be useful in the starting G-code of your preferred slicer".

The matching end sequence is in [start-and-end-gcode.md](start-and-end-gcode.md#end-g-code).

---

### PID tuning

`M303` is Marlin's PID autotune, which the Marlin page https://marlinfw.org/docs/gcode/M303.html describes as "a process of heating and cooling to determine the proper PID values for the specified hotend or the heated bed". Run it at the print temperature before committing a new filament profile:

```gcode
M303 E0 S<temp> C8
```

The same page says the values are "saved with M500" when `EEPROM_SETTINGS` is enabled.
