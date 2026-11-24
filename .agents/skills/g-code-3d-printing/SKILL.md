---
name: g-code-3d-printing
description: 'G-code safety for Marlin and Klipper printers: heating, homing, start and end sequences, macros, calibration. Use when the user says "write start G-code" or "calibrate pressure advance". Not for the PCB, use `kicad`.'
metadata:
  version: "1.1.0"
---

# G-code and 3D Printing Standards

How generated G-code stays safe on real hardware: the machine is never asked to move from an unknown position, never asked to extrude cold, and never asked to override a firmware safety feature. Every rule here maps to a specific way printers catch fire, crash, or ruin a plate.

Written for Marlin 2 and Klipper. Both accept the standard G-code below, the difference is that Klipper expects complex sequences to live in Jinja2 macros rather than in the slicer.

---

### When not to activate

- Designing the PCB the printed enclosure houses, use `kicad`.
- Writing firmware for the printer's own microcontroller, use `embedded-c-arduino`.
- Writing the shell script that uploads or post-processes the file, use `bash` or `powershell`.

---

### Rules

1. Thermal safety: never override or disable firmware thermal runaway protection from G-code. Wait for the heaters with the blocking `M109` and `M190` before any extrusion, and stay under the hotend's hardware ceiling.
2. Never rely on the machine's assumed state. Declare `G90` and an explicit `M82` or `M83` that matches the slicer profile, and use `G91` only for an immediate micro-move, with `G90` on the next line.
3. `G28` before any `G0` or `G1`, no coordinate outside the exact build volume you were given, and a Z-hop over already-printed areas.
4. Feedrate `F` is always millimetres per minute, never mm/s. Insert `M400` before anything that needs the toolhead physically stopped.
5. The start sequence is fixed: home, heat to the real target, level, purge outside the part, then print. Never hard-code a Z-offset, and never purge over the area the part will occupy.
6. The end sequence retracts, lifts, parks clear of the part, and cuts the heaters and motors. It is kept with the start sequence in the slicer profile and in version control.
7. Where the firmware has macros, tool changes, filament runout, mesh levelling and the start sequence live in a version-controlled macro the slicer calls, never in inline G-code every export regenerates.
8. Insert `; VERIFY: <instruction>` comments where the operator must confirm hardware state, and use `M112` as the abort in any script detecting a fatal condition.
9. Record pressure advance, extrusion multiplier and retraction per filament before generating production G-code, and commit the slicer profile with its name and version stamped in the G-code header.

---

### Reference files

| Open this | When |
|---|---|
| [start-and-end-gcode.md](references/start-and-end-gcode.md) | Heat-up, start or end G-code: blocking heat commands, the hotend ceiling, PID tuning, the start order, the end sequence, with Pass and Fail |
| [motion-rules.md](references/motion-rules.md) | Coordinate mode, homing, Z-hop, feedrate, `M400`, `M112` and operator checkpoints, with Pass and Fail G-code |
| [klipper-macros.md](references/klipper-macros.md) | The printer runs Klipper: macros over raw sequences, the full `START_PRINT` macro body, PID tuning |
| [marlin.md](references/marlin.md) | The printer runs Marlin: the start sequence as slicer start G-code, PID tuning |
| [calibration-and-profiles.md](references/calibration-and-profiles.md) | Calibrating a new filament, fan and seam post-processing, multi-material tool changes, slicer profile version control |
| [checklist.md](references/checklist.md) | Before calling G-code or a slicer profile done |
