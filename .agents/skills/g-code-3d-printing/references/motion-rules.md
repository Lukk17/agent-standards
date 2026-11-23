# Motion Rules

The Pass and Fail G-code behind the motion rules in [SKILL.md](../SKILL.md): coordinate mode, homing, Z-hop, feedrate, and the stops an operator or a script can trigger. They hold on Marlin and on Klipper alike.

---

### Declare the coordinate mode

Never rely on the machine's assumed state. Declare absolute positioning with `G90` and pick the extruder mode explicitly: `M82` for absolute E values, `M83` for relative. The choice must match what the slicer profile computes. Use `G91` only for an immediate micro-move such as a Z-hop, and return to `G90` on the next line.

Pass:

```gcode
G90
M83
```

Fail:

```gcode
G1 X50 Y50 F3000
```

---

### Home before moving, and stay inside the build volume

`G28` before any `G0` or `G1`. A move commanded from an unknown position is a crash. Be given the exact build volume and never generate a coordinate outside it.

Pass:

```gcode
G28
G1 Z5 F600
```

Fail:

```gcode
G1 Z0 F600
```

Z-hop over already-printed areas so the hot nozzle cannot collide with and dislodge the part:

```gcode
G91
G1 Z0.4 F600
G90
G0 X120 Y95
G91
G1 Z-0.4 F600
G90
```

---

### Feedrate and a stopped toolhead

Feedrate `F` is always millimetres per minute, never mm/s, so 600 is 10 mm/s. Insert `M400` before anything that needs the toolhead physically stopped: a camera snapshot, a macro handoff, a pause.

---

### Emergency stop and operator checkpoints

Insert `; VERIFY: <instruction>` comments where the operator must confirm hardware state, bed clear or filament loaded, before the sequence continues. Use `M112` as the abort in any script detecting a fatal condition, and understand that it cuts power to all motors and heaters and needs a firmware restart afterwards.

Pass:

```gcode
; VERIFY: bed clear and previous part removed
```

Fail:

```gcode
M0 Click to continue
```
