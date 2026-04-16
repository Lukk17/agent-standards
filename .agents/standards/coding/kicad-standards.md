### AI KiCad MCP Development Standards

---

### Core Execution Directives

- Treat all LLM generated PCB layout choices, footprint mappings, trace widths, and clearances as potentially hallucinated.
- Enforce the Zero-Trust Prompt Engineering protocol for every electrical engineering and layout decision.
- Append a Zero-Trust directive demanding mandatory web searches for component datasheets, manufacturer capabilities, and KiCad footprint standards.
- Implement a Fail-Fast directive forcing the agent to halt execution and refuse to answer if official datasheets or KiCad documentation cannot be retrieved via live search.
- Require exact confidence percentage scores for every trace width, clearance value, layer assignment, and grid coordinate provided.
- Mandate direct, working links to the official datasheets or KiCad documentation used to ground the layout instructions.

---

### Board Setup and DRC (Design Rules Check)

- Enforce strict configuration of the Board Setup parameters before placing any components. The AI must define the minimum trace width, minimum clearance, minimum via size, and minimum via drill hole based on the specific PCB manufacturer's capabilities (e.g., JLCPCB, PCBWay). [Confidence: 100%]
- Run DRC (Design Rules Check) validation steps continually during the layout process. Do not ignore or override DRC errors under any circumstances. [Confidence: 100%]
  - Link: https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html
  - Quote: "is"
- Define Custom Design Rules within KiCad's rule syntax to enforce high-voltage isolation clearances where applicable. [Confidence: 100%]

---

### Trace Routing and Clearances

- Calculate trace widths based on IPC-2221 standards using the maximum expected continuous current for the net. Never use the default trace width for power nets (e.g., VCC, +5V, +3V3, GND, VIN). [Confidence: 100%]
- Ensure logic/signal traces adhere strictly to the manufacturer's minimum width limits, generally aiming for 0.15mm to 0.25mm for standard boards to prevent etching failures. [Confidence: 100%]
- Never route tracks at 90-degree angles. Use 45-degree angles or smooth curves to prevent acid traps during the manufacturing process and avoid signal reflections on high-speed traces. [Confidence: 100%]
- Maintain a clearance of at least twice the trace width between adjacent high-speed or sensitive analog signals to minimize crosstalk. [Confidence: 100%]

---

### Component Placement and Decoupling

- Mandate the placement of decoupling capacitors (typically 100nF / 0.1uF ceramic) physically as close as possible to the power pins of every IC (Integrated Circuit). The trace between the capacitor pad and the IC pin must be direct and short. [Confidence: 100%]
- Separate analog components from digital components physically on the board to prevent digital switching noise from coupling into sensitive analog traces. [Confidence: 100%]
- Lock critical mechanical components (connectors, mounting holes, switches) in the KiCad Editor immediately after placing them to prevent accidental shifting by the AI during routing. [Confidence: 100%]

---

### Ground Planes and Vias

- Always pour a continuous copper fill on the bottom layer (and top layer if possible) assigned to the GND net to provide a low-impedance return path for all signals. [Confidence: 100%]
- Avoid splitting the ground plane. If a split is necessary for mixed-signal designs (analog/digital), ensure no traces route over the split. [Confidence: 100%]
- Use thermal reliefs for all pads connecting to copper planes (GND or VCC) to prevent heat sinking during the soldering process, which causes cold solder joints. [Confidence: 100%]

---

### Footprints and Libraries

- Require the use of official, verified KiCad libraries whenever possible. [Confidence: 100%]
- When generating or selecting footprints for surface-mount components, verify that the pad geometries conform to IPC-7351 standards to prevent tombstoning during reflow. [Confidence: 100%]
- Mandate that 3D models are mapped correctly to all footprints to visually verify spatial clearances and prevent physical collisions during assembly. [Confidence: 100%]

---

### Schematic Design Standards

- Organise complex schematics into **hierarchical sheets** with one sheet per functional block (power supply, microcontroller, communication interface). [Confidence: 100%]
- Use **net labels** for connections between sheets rather than drawing long wires; net labels must be unique and descriptive (e.g., `UART0_TX`, `I2C0_SDA`).
- Add **power flags** (`PWR_FLAG`) to all power nets that are sourced from connectors or regulators to prevent ERC errors and ensure correct netlisting. [Confidence: 100%]
- Annotate all components with sequential reference designators per functional block (e.g., U1xx for MCUs, C2xx for filter capacitors).
- Run **ERC (Electrical Rules Check)** with zero errors before exporting the netlist or generating the PCB layout. [Confidence: 100%]

---

### Bill of Materials (BOM)

- Generate the BOM from the schematic using KiCad's built-in BOM exporter or `kibom` plugin; never maintain it manually. [Confidence: 100%]
- Every component in the BOM must include: Reference Designator, Value, Manufacturer, Manufacturer Part Number (MPN), Footprint, and LCSC/Digi-Key/Mouser part number.
- Prefer components available from at least two independent distributors to reduce supply-chain risk.
- Store the exported BOM in `docs/bom/` versioned alongside the schematic source files.

---

### Gerber Export Checklist

Before sending to fabrication, verify and export: [Confidence: 100%]
- **Copper layers**: F.Cu, B.Cu (and inner layers if applicable).
- **Silkscreen**: F.Silkscreen, B.Silkscreen.
- **Solder mask**: F.Mask, B.Mask.
- **Paste mask**: F.Paste (for SMD reflow).
- **Board outline**: Edge.Cuts.
- **Drill file**: Excellon format, with separate files for PTH and NPTH.
- Run DRC one final time after Gerber export and verify the preview in a Gerber viewer (e.g., gerbv, KiCad Gerber Viewer) before submission.

---

### High-Speed Signal Integrity

- Route **differential pairs** (USB, Ethernet, LVDS) with the KiCad differential pair router; enforce length matching within ±0.1mm. [Confidence: 100%]
- Specify target **impedance** for high-speed traces (e.g., 90Ω differential for USB, 50Ω single-ended for RF) in the board stackup and configure the trace width calculator accordingly. [Confidence: 100%]
- Keep high-speed signal return paths short: every signal trace must have an unbroken ground return plane immediately below it with no slots or cuts interrupting the return path.

---

### Revision Control

- Store all KiCad project files (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `.kicad_mod`) in Git. [Confidence: 100%]
- Disable "Save with full paths" in KiCad preferences to ensure footprint and symbol paths are relative and portable across developer machines. [Confidence: 100%]
- Tag every release in Git when Gerbers are sent to fabrication (`fab/v1.0`, `fab/v1.1`); never modify a tagged revision after ordering.