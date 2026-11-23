# Scope

Companion reference for the [g-code-3d-printing](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Writing or reviewing start, end, layer-change, or tool-change G-code.
- Building or editing a Klipper macro.
- Diagnosing a crash, a cold extrusion, a nozzle dragging through a print, or a Z-offset problem.
- Calibrating pressure advance, extrusion multiplier, or retraction for a filament.
- Version-controlling slicer profiles or embedding a profile reference in output.
- Generating or post-processing G-code from a script.
- The user says "write start G-code for my printer", "my nozzle drags through the print", "set up a START_PRINT macro", "calibrate pressure advance" or "version my slicer profiles".

---

### When not to activate

- Designing the PCB the printed enclosure houses, use `kicad`.
- Writing firmware for the printer's own microcontroller, use `embedded-c-arduino`.
- Writing the shell script that uploads or post-processes the file, use `bash` or `powershell`.
- Automating the printer from Home Assistant, use `home-assistant`.
- Documenting the printer setup for other people, use `markdown-writer`.

---

### Related skills

- `kicad` for the board that goes inside the printed enclosure.
- `embedded-c-arduino` for firmware on the printer's own controller.
- `home-assistant` for automating the printer, its power, and its notifications.
- `bash` and `powershell` for upload and post-processing scripts.
- `markdown-writer` for the printer and profile documentation.
