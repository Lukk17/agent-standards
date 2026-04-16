### AI 3D Printing and G-code Development Standards

---

### Core Execution Directives

- Treat all LLM generated G-code, coordinate assignments, and temperature directives as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every machine-level instruction.
- Append a Zero-Trust directive demanding mandatory web searches for current Marlin, Klipper, or RepRap documentation regarding specific G-code parameters.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official firmware documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every coordinate, feedrate, and temperature value provided.
- Mandate direct, working links to the official slicer or firmware documentation used to ground the code.

---

### Thermal Runaway and Heating Safety

- Never attempt to manually override or disable firmware-level thermal runaway protection via G-code. [Confidence: 100%]
- Require the use of blocking temperature commands (`M109` for hotend, `M190` for bed) rather than non-blocking commands (`M104` / `M140`) before any extrusion sequence. This ensures the printer does not attempt cold extrusion, which shreds the filament or breaks the extruder gear. [Confidence: 100%]
  - Link: https://www.klipper3d.org/G-Codes.html
  - Quote: "the"
- Explicitly enforce maximum temperature bounds based on the printer's hardware. Limit PTFE-lined hotends strictly to a maximum of 230°C to prevent off-gassing of toxic neurotoxins. [Confidence: 100%]
- If the AI generates calibration sequences, it must use the PID tuning command (`M303`) to ensure stable thermal profiles before printing. [Confidence: 100%]

---

### Coordinate Systems and Positioning

- Mandate explicit declaration of the positioning mode at the very beginning of the G-code sequence. Never rely on the machine's assumed default state. [Confidence: 100%]
- Set structural and toolhead movements strictly to Absolute Positioning (`G90`). [Confidence: 100%]
  - Link: https://all3dp.com/2/g91-g90-g-code/
  - Quote: "modes:"
- Explicitly declare the Extruder positioning mode. Use `M82` for Absolute Extrusion or `M83` for Relative Extrusion, ensuring it perfectly matches the logic used to calculate the filament E-steps. [Confidence: 100%]
- Always use Relative Positioning (`G91`) for small, immediate toolhead shifts like Z-hop, but immediately return to Absolute Positioning (`G90`) afterward. [Confidence: 100%]

---

### Crash Prevention and Physical Boundaries

- Require a mandatory homing command (`G28`) before any XYZ movement commands (`G0` or `G1`) are issued. The AI must never command a move when the machine's absolute location is unknown. [Confidence: 100%]
- Enforce software limit bounding. The AI must be provided with the exact build volume (e.g., X: 220, Y: 220, Z: 250) and never generate coordinates exceeding these limits to prevent stepper motor crashes and belt skipping. [Confidence: 100%]
- Mandate Z-hop (`G1 Z...` in relative mode) during long travel moves across already printed areas to prevent the hot nozzle from colliding with and dislodging the printed part. [Confidence: 100%]

---

### Firmware Specifics (Marlin vs. Klipper)

- When targeting Klipper firmware, prohibit the AI from generating complex raw G-code logic for processes like tool changes or filament runout. Instead, mandate the invocation of safe, pre-configured Jinja2 macros (e.g., `START_PRINT`, `END_PRINT`). [Confidence: 100%]
- Ensure all feedrate (`F`) values in `G0` and `G1` commands are explicitly declared in millimeters per minute (mm/min), not millimeters per second (mm/s). [Confidence: 100%]
- Add explicit wait commands (`M400`) before executing tasks that rely on the toolhead being physically stopped, such as triggering a camera snapshot or executing a pause. [Confidence: 100%]

---

### Filament Calibration Requirements

- Before generating production G-code for a new filament profile, require the following calibrations to be performed and their values recorded: [Confidence: 100%]
  - **Pressure Advance (Klipper)** / **Linear Advance (Marlin)**: tune the K-factor for the specific filament and hotend combination to eliminate corner bulge and improve dimensional accuracy.
  - **Extrusion Multiplier (EM)**: calibrate via a single-wall cube; target wall thickness must match the configured line width within ±2%.
  - **Retraction**: tune retraction distance and speed for the specific extruder type (direct drive vs. Bowden) to eliminate stringing.
- Store calibrated profile values in a version-controlled slicer profile file alongside the G-code.

---

### First-Layer Calibration

- Every start G-code sequence must include a Z-offset verification step (e.g., `BED_MESH_CALIBRATE` for Klipper, `G29` for Marlin UBL/BLTouch) before the first extrusion move. [Confidence: 100%]
- Never hard-code a Z-offset value in generated G-code; always read it from the printer's saved configuration or prompt the user to verify it before printing.
- The purge line (prime the nozzle) must be generated on an edge of the bed outside the print area; never purge over the build plate where the part will be printed.

---

### Post-Processing G-code Patterns

- Ramp fan speed gradually: set fan to 0% for the first two layers, then to 100% (or profile-defined value) from layer 3 onwards using layer-change G-code hooks. [Confidence: 100%]
- Place seams at the rear of the model (`SEAM_POSITION=REAR` in Klipper slicers) or at a sharp corner to make them less visible.
- Use `G10` / `G11` (Firmware Retract) only when the printer's firmware retract values are tuned; otherwise explicitly specify E-axis retract moves.

---

### Multi-Material Print Standards

- Define a dedicated `TOOL_CHANGE` or `T0`/`T1` macro in Klipper for each extruder; never generate raw tool-change sequences without invoking the printer's macro. [Confidence: 100%]
- Always include a purge/prime tower or purge bucket wipe sequence after every tool change to clear the previous filament colour from the nozzle.
- Set independent temperature targets per tool; ensure both nozzles reach target temperature before beginning a tool-change sequence.

---

### Slicer Profile Version Control

- Store all slicer profiles (PrusaSlicer `.ini`, OrcaSlicer `.json`, Cura `.cfg`) in the project's Git repository under `slicer-profiles/`. [Confidence: 100%]
- Name profile files with the filament type, nozzle size, and layer height: `pla-0.4mm-0.2mm-layer.ini`.
- Tag the slicer profile version in the G-code file header comment so a printed part can always be reproduced:
  ```
  ; Profile: pla-0.4mm-0.2mm-layer.ini v1.3
  ; Slicer: OrcaSlicer 2.1.0
  ```

---

### Emergency Stop and Safety Halts

- The AI must insert `M112` (emergency stop) comments as placeholders in generated G-code sequences that require the operator to verify hardware state (e.g., bed clear, filament loaded) before proceeding. [Confidence: 100%]
- Never generate G-code that moves to Z=0 without a prior `G28 Z` home; a Z-crash with a loaded bed can damage the print surface and the nozzle.