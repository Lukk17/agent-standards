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