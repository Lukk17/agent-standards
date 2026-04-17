---
name: g-code-3d-printing
description: G-code and 3D printing standards covering thermal safety, motion safety, Klipper macros, calibration, start/end G-code, and slicer profile version control.
origin: project-standards
---

# G-code and 3D Printing Development Standards

## Thermal Runaway and Heating Safety

- Never attempt to manually override or disable firmware-level **thermal runaway protection** via G-code. This protection is a critical safety feature that prevents fires.
- Use **blocking temperature commands** before any extrusion sequence:
  - `M109 S<temp>` — wait for hotend to reach target temperature.
  - `M190 S<temp>` — wait for heated bed to reach target temperature.
  - Do not use the non-blocking variants (`M104` / `M140`) as the sole heat command before extrusion; cold extrusion shreds filament or breaks the extruder gear.
- Enforce maximum temperature bounds based on the printer's hardware:
  - **PTFE-lined hotends**: strictly limit to a maximum of **230°C** to prevent off-gassing of toxic fumes (PTFE decomposition begins above 240°C).
  - All-metal hotends: respect the manufacturer's stated maximum.
- Use `M303 E0 S<target_temp> C8` PID auto-tuning to establish stable thermal profiles before committing a new filament profile to production G-code.

## Coordinate Systems and Positioning

- Declare the positioning mode **explicitly at the beginning of every G-code sequence**. Never rely on the machine's assumed default state.
- Set all structural and toolhead movements to **Absolute Positioning**: `G90`.
- Explicitly declare the extruder positioning mode:
  - `M82` — Absolute Extrusion (E-values are cumulative totals).
  - `M83` — Relative Extrusion (E-values are per-move deltas).
  - The chosen mode must exactly match the logic used to calculate filament E-steps in the slicer profile.
- Use **Relative Positioning** (`G91`) only for immediate toolhead micro-moves such as Z-hop, then immediately return to `G90` (Absolute).

## Crash Prevention and Physical Boundaries

- Require a mandatory **homing command** (`G28` or `G28 XYZ`) before any XYZ movement commands (`G0` or `G1`). Never command a move when the machine's absolute position is unknown.
- Enforce **software limit bounding**: be provided the exact build volume (e.g., X: 220, Y: 220, Z: 250) and never generate coordinates that exceed these limits to prevent stepper motor crashes and belt skipping.
- Mandate **Z-hop** during long travel moves over already printed areas:
  ```gcode
  G91           ; relative
  G1 Z0.4 F600  ; lift
  G90           ; absolute
  G0 X... Y...  ; travel
  G91
  G1 Z-0.4 F600 ; lower
  G90
  ```
  This prevents the hot nozzle from colliding with and dislodging the printed part.

## Firmware Specifics — Marlin vs. Klipper

- When targeting **Klipper**, prohibit raw G-code logic for complex processes (tool changes, filament runout, mesh levelling). Invoke safe, pre-configured **Jinja2 macros** instead:
  - `START_PRINT BED_TEMP=60 EXTRUDER_TEMP=215`
  - `END_PRINT`
  - `PAUSE`, `RESUME`, `CANCEL_PRINT`
- All feedrate `F` values in `G0` and `G1` commands must be in **millimeters per minute (mm/min)**, not mm/s. (600 mm/min = 10 mm/s.)
- Add explicit `M400` (wait for moves to finish) before tasks that require the toolhead to be physically stopped (camera snapshot, macro execution, pause).

## Filament Calibration Requirements

Before generating production G-code for a new filament profile, perform and record the following calibrations:

- **Pressure Advance (Klipper)** / **Linear Advance K-factor (Marlin)**: tune for the specific filament and hotend combination to eliminate corner bulge and improve dimensional accuracy.
  - Klipper: `SET_PRESSURE_ADVANCE ADVANCE=<value>`
  - Marlin: `M900 K<value>`
- **Extrusion Multiplier (EM)**: calibrate via a single-wall cube; target wall thickness must match the configured line width within **±2%**.
- **Retraction**: tune retraction distance and speed for the specific extruder type:
  - Direct drive: typically 0.5–2.0 mm.
  - Bowden: typically 4–7 mm.
  - Objective: eliminate stringing between features.
- Store all calibrated profile values in a **version-controlled slicer profile file** alongside the G-code output.

## Start G-code — Bed Mesh and Purge Line

Every start G-code sequence must follow this pattern:

1. Home all axes: `G28`.
2. Load bed mesh / run auto-levelling:
   - Klipper: `BED_MESH_CALIBRATE` or `BED_MESH_PROFILE LOAD=default`.
   - Marlin UBL/BLTouch: `G29`.
3. Never hard-code a Z-offset value in generated G-code; always read it from the printer's saved configuration.
4. Generate a **purge line on an edge of the bed, outside the print area** to prime the nozzle before the first print move. Never purge over the area where the part will be printed.

Example purge line (left edge, outside print area):
```gcode
G1 X1 Y20 Z0.3 F5000   ; move to purge start
G1 E10 F300             ; prime
G1 Y180 E25 F1500       ; draw purge line
G1 Z2 F3000             ; lift
```

## Post-Processing G-code Patterns

- **Fan ramp**: set fan to 0% for the first two layers, then ramp to 100% (or profile-defined value) from layer 3 onward using layer-change hooks.
  ```gcode
  ; Layer 1-2: M107 (fan off)
  ; Layer 3+:  M106 S255 (full fan)
  ```
- **Seam placement**: position seams at the rear of the model or at a sharp corner to minimise visibility.
- Use `G10` / `G11` (Firmware Retract) only when the printer's firmware retract values are fully tuned; otherwise use explicit E-axis retract moves for reproducibility.

## Multi-Material Print Standards

- Define a dedicated `TOOL_CHANGE` macro in Klipper (or `T0`/`T1` sequences in Marlin) for each extruder. Never generate raw inline tool-change sequences without invoking the printer's macro.
- Always include a purge/prime tower or purge bucket wipe sequence after every tool change to clear residual filament colour from the nozzle.
- Set independent temperature targets per tool (`T0` and `T1`); ensure both nozzles reach target temperature before beginning the tool-change sequence.

## Slicer Profile Version Control

- Store all slicer profiles in the project's Git repository under `slicer-profiles/`:
  - PrusaSlicer: `.ini`
  - OrcaSlicer: `.json`
  - Cura: `.cfg` / `.curaprofile`
- Name profile files with the filament type, nozzle size, and layer height:
  ```
  pla-0.4mm-0.2mm-layer.ini
  petg-0.6mm-0.3mm-layer.json
  ```
- Tag the slicer profile version in the G-code file header comment so any printed part can be exactly reproduced:
  ```gcode
  ; Profile: pla-0.4mm-0.2mm-layer.ini v1.3
  ; Slicer: OrcaSlicer 2.1.0
  ; Printer: Voron 2.4 350mm
  ; Date: 2025-03-01
  ```

## Emergency Stop and Safety Halts

- Insert `; VERIFY: <instruction>` comments as operator checkpoints in generated G-code sequences that require hardware state verification (bed clear, filament loaded) before proceeding.
- Use `M112` (emergency stop) as the abort command in scripts that detect a fatal error condition. Understand that `M112` immediately cuts power to all motors and heaters and requires a firmware restart.
- Never generate G-code that commands `G1 Z0` or moves toward Z=0 without a prior `G28 Z` home; a Z-crash with a loaded bed damages the print surface and the nozzle.
