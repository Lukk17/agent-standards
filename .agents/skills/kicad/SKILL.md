---
name: kicad
description: KiCad PCB design standards for schematic, layout, DRC, BOM, Gerber export, and design review processes.
origin: project-standards
---

# KiCad PCB Design Standards

---

### Board Setup and DRC Enforcement

- Configure Board Setup parameters before placing any components. Define minimum trace width, minimum clearance, minimum
  via size, and minimum via drill hole based on the target PCB manufacturer's capabilities (JLCPCB, PCBWay, etc.).
- Run DRC (Design Rules Check) continuously during the layout process. Never override or ignore DRC errors.
- Define custom KiCad design rules (`.kicad_dru`) to enforce high-voltage isolation clearances, controlled impedance
  nets, and any board-specific constraints.
- Target zero DRC errors before submitting Gerbers to fabrication.

---

### Trace Routing and Clearances, IPC-2221

- Calculate trace widths from IPC-2221 standards using the maximum expected continuous current for each net. Never use
  the default trace width for power nets (`VCC`, `+5V`, `+3V3`, `GND`, `VIN`).
- Logic and signal traces: aim for 0.15-0.25 mm to stay within standard manufacturer etching limits.
- Never route tracks at 90-degree angles. Use 45-degree angles or smooth curves to prevent acid traps during
  manufacturing and signal reflections on high-speed traces.
- Maintain a clearance of at least twice the trace width between adjacent high-speed or sensitive analog signals to
  minimise crosstalk.
- Use the KiCad trace width calculator with the IPC-2221 formula (`I = k × ΔT^0.44 × A^0.725`) for all power nets.

---

### Component Placement and Decoupling Capacitors

- Place decoupling capacitors (100 nF / 0.1 µF ceramic, X5R or X7R) physically as close as possible to the power pins of
  every IC. The trace between the capacitor pad and the IC pin must be direct, short, and wide.
- Separate analog components from digital components physically on the board to prevent digital switching noise from
  coupling into sensitive analog circuits.
- Lock critical mechanical components (connectors, mounting holes, switches, crystals) in the KiCad PCB Editor
  immediately after placement to prevent accidental movement during routing.
- Place bypass capacitors before bulk capacitors in the power delivery network, going from smallest to largest value
  toward the power source.

---

### Ground Planes and Thermal Reliefs

- Pour a continuous copper fill on the bottom layer (and top layer where possible) assigned to the `GND` net to provide
  a low-impedance return path for all signals.
- Avoid splitting the ground plane. If a split is required for mixed-signal designs (analog/digital), ensure no traces
  route across the split.
- Decide the pad-to-pour connection per pad, not as one blanket rule for the whole board. A thermal relief connects a
  pad to the copper pour around it through a small number of narrow copper spokes, leaving a gap around the rest of
  the pad. Its purpose is to stop the pour from sinking heat away from a soldering iron, or from a wave-solder bath (a
  machine that solders many through-hole joints at once by passing the underside of the board over a wave of molten
  solder), which is what actually causes a cold solder joint on a pad sitting inside a large sheet of copper. That
  purpose only exists for hand-soldered or wave-soldered through-hole joints. A reflow oven heats the whole board at
  once, so there is no iron or wave losing heat into the plane to protect against, and on a reflow-soldered pad the
  same narrow spokes that protect a hand-soldered joint cut that pad's copper cross-section down to a fraction of a
  solid connection, throttling both the current path and the thermal path through it. Ask, for every pad: will this
  joint be hand- or wave-soldered, and does this pad need to carry meaningful current or sink heat into the pour
  during operation (a power-supply output pin, a high-current connector pad, a component's own thermal pad)? Use a
  thermal relief only where the first is true. Connect solid whenever the second is true, regardless of assembly
  method. KiCad's own zone-connection setting exposes this choice per pad and per zone: solid, thermal relief, thermal
  relief for through-hole pads only, or no connection at all.
- Stitch the top and bottom ground pours together with via stitching around the board perimeter and around
  high-frequency components.

---

### Footprints, Libraries, and 3D Models, IPC-7351

- Use official, verified KiCad library footprints whenever possible. Create custom footprints only when the
  manufacturer's suggested land pattern differs from the library entry.
- Verify that all SMD footprint pad geometries conform to IPC-7351 standards (Most Material Condition, Nominal, or Least
  Material Condition depending on assembly process) to prevent tombstoning during reflow.
- Map 3D models (`.step` or `.wrl`) correctly to all footprints to visually verify spatial clearances and prevent
  physical collisions during assembly.
- Store custom footprints in a project-local library (`<project>.pretty/`) and custom 3D models in `3d_models/` within
  the repository.

---

### Hierarchical Schematic Design

- Organise complex schematics into hierarchical sheets with one sheet per functional block:
  - `power_supply.kicad_sch`
  - `microcontroller.kicad_sch`
  - `communication.kicad_sch`
  - `user_interface.kicad_sch`
- Use net labels for connections between sheets rather than drawing long wires. Net labels must be unique and
  descriptive (e.g., `UART0_TX`, `I2C0_SDA`, `SPI0_CS_n`).
- Add power flags (`PWR_FLAG`) to all power nets sourced from connectors or regulators to suppress ERC errors and ensure
  correct netlisting.
- Annotate all components with sequential reference designators per functional block (e.g., `U1xx` for MCUs, `C2xx` for
  filter capacitors, `R3xx` for pull-up/pull-down resistors).
- Run ERC (Electrical Rules Check) with zero errors before exporting the netlist or generating the PCB layout.

---

### Bill of Materials (BOM)

- Generate the BOM from the schematic using KiCad's built-in BOM exporter or the `kibom` plugin. Never maintain the BOM
  manually.
- Every component entry must include:
  - Reference Designator
  - Value (resistance, capacitance, voltage rating, etc.)
  - Manufacturer
  - Manufacturer Part Number (MPN)
  - Footprint
  - LCSC part number (and/or Digi-Key / Mouser part number)
- Prefer components available from at least two independent distributors to reduce supply-chain risk.
- Store the exported BOM in `docs/bom/` versioned alongside the schematic source files.

---

### Gerber Export Checklist

Before sending to fabrication, export and verify all of the following layers:

| Layer | File |
|---|---|
| Front copper | `F.Cu` |
| Back copper | `B.Cu` |
| Inner copper layers | `In1.Cu`, `In2.Cu`, ... (if applicable) |
| Front silkscreen | `F.Silkscreen` |
| Back silkscreen | `B.Silkscreen` |
| Front solder mask | `F.Mask` |
| Back solder mask | `B.Mask` |
| Front paste mask | `F.Paste` (for SMD reflow) |
| Board outline | `Edge.Cuts` |
| Drill file | Excellon format, separate PTH and NPTH files |

- Run DRC one final time after Gerber export.
- Verify the Gerber preview in an independent Gerber viewer (gerbv or KiCad's built-in Gerber Viewer) before submitting
  to the fab.

---

### High-Speed Signal Integrity, Differential Pairs and Impedance

- A differential pair is two tracks that carry one signal as the voltage difference between them, rather than each
  track carrying its own signal referenced to ground. USB, Ethernet, LVDS, CAN, and RS-485 all use this technique
  because a matched pair rejects common-mode noise (interference picked up equally by both tracks) far better than a
  single track referenced to ground does.
- There is no single length-matching figure that fits every differential pair. The tolerable length mismatch between
  the two tracks of a pair, called skew, is set by the signalling rate of the interface and by how much of that
  interface's own timing budget the board is allowed to spend. A skew that is irrelevant on a slow link (RS-485 at a
  few megabits per second) can break a fast one (a multi-gigabit link) outright, because what matters is skew as a
  fraction of the unit interval, the time one bit occupies at the link's data rate, never skew in millimetres copied
  from a different project.
- Derive the enforced number instead of quoting one from memory:
  1. Read the interface's own specification for its data rate and, where it states one directly, its own maximum
     intra-pair skew. Some interface specifications publish an explicit skew limit in their own electrical chapter.
     Where one doesn't, fall back on the general relationship that timing skew between the two lines of a pair
     converts part of the intended differential signal into unwanted common-mode noise, roughly in proportion to skew
     divided by the signal's rise time.
  2. Convert that time budget into a physical length using the propagation velocity of the actual stackup and layer
     the pair runs on, not a generic PCB propagation-speed figure remembered from elsewhere. Propagation velocity
     depends on the effective dielectric constant the trace actually sees, v = c / √(ε_eff), a single number blending
     how much of the trace's electric field sits inside the board material versus in the air above it for a surface
     trace with a pour underneath (microstrip), or sits entirely inside the board material for a trace buried between
     two reference planes (stripline). IPC-2141A, Design Guide for High-Speed Controlled Impedance Circuit Boards,
     gives the standard delay approximations used for this conversion: roughly 1.017 × √(0.475εr + 0.67) nanoseconds
     per inch for microstrip, and roughly 1.017 × √εr nanoseconds per inch for stripline, where εr is the substrate's
     own dielectric constant (a material property read off the laminate's datasheet).
  3. Apply a derating factor before the number becomes the one a check actually enforces. No IPC or IEEE standard
     publishes one universal derating percentage for this: it is settled engineering convention, not a codified spec,
     and the convention itself varies by how much risk a project is willing to carry. Keeping skew inside roughly 10
     percent of the available timing budget is the commonly used conservative choice. A looser budget of up to
     roughly 25 percent shows up in practice when board area is genuinely constrained and the interface's own timing
     margin can absorb it. Neither figure is mandated anywhere. The underlying physical justification, that skew
     converts to common-mode noise in rough proportion to the skew-to-rise-time ratio, is discussed in Johnson and
     Graham, High-Speed Digital Design: A Handbook of Black Magic (Prentice Hall, 1993). Whichever factor is chosen
     belongs inside the enforced number itself, the netclass rule or the design-rule-check constraint, never only in a
     comment or a paragraph of prose next to the tool. A margin that nothing enforces gets silently consumed the first
     time a router pass or a hand edit nudges a track.
- A pair with a real skew budget is either hand-routed and then locked so nothing can move it afterward, or routed by
  an autorouter and then checked. Neither path is inherently correct. General-purpose autorouters do not implement
  dedicated differential-pair length matching: natural skew after autorouting depends entirely on how symmetric the
  placement is and on whichever path the router happened to find, so an autorouted pair's as-built length has to be
  measured on the real routed copper and checked against the derived tolerance before the board is considered
  finished, never assumed to already match because the router "should" have kept it close. KiCad's interactive router
  includes a dedicated length-tuning mode built for exactly this problem, because a general path-finding algorithm
  does not solve for skew on its own. Use it for the hand-routed path.
- Specify a target impedance for every high-speed pair or single-ended trace in the board stackup, and configure the
  trace-width calculator to hit it:
  - USB 2.0 full-speed/high-speed: 90 Ω differential
  - RF / SMA traces: 50 Ω single-ended
  - LVDS: 100 Ω differential
- Keep high-speed signal return paths short: every signal trace must have an unbroken ground return plane immediately
  below it with no slots or cuts interrupting the return current path.
- Add series termination resistors (33-47 Ω) at the source end of high-speed single-ended traces to damp reflections.

---

### Verification Is a Discipline, Not a Result

- A design-rule check (DRC) reporting zero violations proves only that the rules actually switched on found nothing.
  Before trusting a "0 errors" result, open the rule severity list itself and confirm nothing has been quietly
  downgraded from error to warning, or excluded outright: a downgraded or excluded rule can no longer report a
  violation at all, so the summary line reads exactly as clean as a board with no problems in it.
- A check that silently skips an object it cannot parse produces a result indistinguishable from a genuine pass. Any
  script or plugin that walks footprints, nets, or zones should report what it actually examined, not only what it
  found wrong, meaning a count of footprints checked, nets checked, or zones checked next to the count of violations,
  so a script that quietly processed 40 of 90 footprints because the other 50 had an unexpected property doesn't look
  identical to one that checked all 90 and found them clean.
- A check nobody has ever seen fail is not yet a check. Before trusting an automated check to catch a defect, build or
  find a deliberately broken input carrying exactly that defect and confirm the check actually flags it. A script run
  only against clean boards has never demonstrated it can fail at all, and an inverted condition, a wrong threshold,
  or a pattern that matches nothing will pass every board handed to it while catching none of them, indefinitely.
- A quantity sized by design-time arithmetic on an idealised shape has to be measured again on the routed, filled
  board. A hand or script calculation for trace width, copper area, or clearance models a clean rectangle or a
  straight line between two points. A real board is not that shape once it is routed and its copper pours are filled:
  a keepout (a clearance a hole or a part must keep from copper that isn't its own net) cuts a notch out of a pour, a
  corner pinches near a pad, a current path bends around an obstacle instead of running straight between two points.
  The arithmetic that sized a rail is a starting point, not the final answer. Re-measure the real, as-filled geometry
  once routing and zone fill are done, and check that measurement against the requirement, not the paper number alone.
- A threshold nobody can trace back to a reason is itself a defect. If a check enforces a number and nobody on the
  project can say where it came from, whether that's a component datasheet, a fabricator's published manufacturing
  limit, a named standard, or a calculation someone can redo, the number will eventually either pass a board that
  should fail or reject one that should pass. Once that happens often enough, the check gets ignored rather than
  fixed. Give every enforced number a traceable origin, and record that origin next to the check, not only in
  whoever's memory set it.

---

### Revision Control

- Store all KiCad project files in Git: `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `.kicad_mod`.
- Disable "Save with full paths" in KiCad Preferences → Common to ensure footprint and symbol paths are stored as
  relative paths, making the project portable across developer machines.
- Use Git LFS for binary assets: 3D model files (`.step`, `.wrl`), rendered board images, and fabrication PDFs.
- Tag every release in Git when Gerbers are sent to fabrication using the convention `fab/v1.0`, `fab/v1.1`. Never
  modify a tagged revision after ordering.
- Add a `fab` tag in the KiCad PCB title block on every release build so the revision is embedded in the Gerber file
  headers.
