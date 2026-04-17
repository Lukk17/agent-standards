---
name: kicad
description: KiCad PCB design standards for schematic, layout, DRC, BOM, Gerber export, and design review processes.
origin: project-standards
---

# KiCad PCB Design Standards

## Board Setup and DRC Enforcement

- Configure Board Setup parameters **before placing any components**. Define minimum trace width, minimum clearance, minimum via size, and minimum via drill hole based on the target PCB manufacturer's capabilities (JLCPCB, PCBWay, etc.).
- Run **DRC (Design Rules Check)** continuously during the layout process. Never override or ignore DRC errors.
- Define custom KiCad design rules (`.kicad_dru`) to enforce high-voltage isolation clearances, controlled impedance nets, and any board-specific constraints.
- Target zero DRC errors before submitting Gerbers to fabrication.

## Trace Routing and Clearances — IPC-2221

- Calculate trace widths from **IPC-2221** standards using the maximum expected continuous current for each net. Never use the default trace width for power nets (`VCC`, `+5V`, `+3V3`, `GND`, `VIN`).
- Logic and signal traces: aim for **0.15–0.25 mm** to stay within standard manufacturer etching limits.
- **Never route tracks at 90-degree angles.** Use 45-degree angles or smooth curves to prevent acid traps during manufacturing and signal reflections on high-speed traces.
- Maintain a clearance of at least **twice the trace width** between adjacent high-speed or sensitive analog signals to minimise crosstalk.
- Use the KiCad trace width calculator with the IPC-2221 formula (`I = k × ΔT^0.44 × A^0.725`) for all power nets.

## Component Placement and Decoupling Capacitors

- Place decoupling capacitors (**100 nF / 0.1 µF** ceramic, X5R or X7R) physically as close as possible to the power pins of every IC. The trace between the capacitor pad and the IC pin must be direct, short, and wide.
- Separate **analog components from digital components** physically on the board to prevent digital switching noise from coupling into sensitive analog circuits.
- Lock critical mechanical components (connectors, mounting holes, switches, crystals) in the KiCad PCB Editor immediately after placement to prevent accidental movement during routing.
- Place bypass capacitors before bulk capacitors in the power delivery network, going from smallest to largest value toward the power source.

## Ground Planes and Thermal Reliefs

- Pour a **continuous copper fill** on the bottom layer (and top layer where possible) assigned to the `GND` net to provide a low-impedance return path for all signals.
- Avoid splitting the ground plane. If a split is required for mixed-signal designs (analog/digital), ensure **no traces route across the split**.
- Use **thermal reliefs** for all pads connecting to copper pours (`GND` or `VCC` planes) to prevent heat sinking during soldering, which causes cold solder joints. Use spoke-style reliefs for through-hole; optionally solid fills for high-current SMD pads.
- Stitch the top and bottom ground pours together with via stitching around the board perimeter and around high-frequency components.

## Footprints, Libraries, and 3D Models — IPC-7351

- Use official, verified KiCad library footprints whenever possible. Create custom footprints only when the manufacturer's suggested land pattern differs from the library entry.
- Verify that all SMD footprint pad geometries conform to **IPC-7351** standards (Most Material Condition, Nominal, or Least Material Condition depending on assembly process) to prevent tombstoning during reflow.
- Map **3D models** (`.step` or `.wrl`) correctly to all footprints to visually verify spatial clearances and prevent physical collisions during assembly.
- Store custom footprints in a project-local library (`<project>.pretty/`) and custom 3D models in `3d_models/` within the repository.

## Hierarchical Schematic Design

- Organise complex schematics into **hierarchical sheets** with one sheet per functional block:
  - `power_supply.kicad_sch`
  - `microcontroller.kicad_sch`
  - `communication.kicad_sch`
  - `user_interface.kicad_sch`
- Use **net labels** for connections between sheets rather than drawing long wires. Net labels must be unique and descriptive (e.g., `UART0_TX`, `I2C0_SDA`, `SPI0_CS_n`).
- Add **power flags** (`PWR_FLAG`) to all power nets sourced from connectors or regulators to suppress ERC errors and ensure correct netlisting.
- Annotate all components with sequential reference designators per functional block (e.g., `U1xx` for MCUs, `C2xx` for filter capacitors, `R3xx` for pull-up/pull-down resistors).
- Run **ERC (Electrical Rules Check)** with **zero errors** before exporting the netlist or generating the PCB layout.

## Bill of Materials (BOM)

- Generate the BOM from the schematic using KiCad's built-in BOM exporter or the `kibom` plugin. Never maintain the BOM manually.
- Every component entry must include:
  - Reference Designator
  - Value (resistance, capacitance, voltage rating, etc.)
  - Manufacturer
  - Manufacturer Part Number (MPN)
  - Footprint
  - LCSC part number (and/or Digi-Key / Mouser part number)
- Prefer components available from at least two independent distributors to reduce supply-chain risk.
- Store the exported BOM in `docs/bom/` versioned alongside the schematic source files.

## Gerber Export Checklist

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
- Verify the Gerber preview in an independent Gerber viewer (gerbv or KiCad's built-in Gerber Viewer) before submitting to the fab.

## High-Speed Signal Integrity — Differential Pairs and Impedance

- Route **differential pairs** (USB, Ethernet, LVDS, CAN) using KiCad's differential pair router (`X` then `Shift+X`). Enforce length matching within **±0.1 mm**.
- Specify target **impedance** for high-speed traces in the board stackup and configure the trace width calculator accordingly:
  - USB 2.0 full-speed/high-speed: 90 Ω differential
  - RF / SMA traces: 50 Ω single-ended
  - LVDS: 100 Ω differential
- Keep high-speed signal return paths short: every signal trace must have an unbroken ground return plane immediately below it with no slots or cuts interrupting the return current path.
- Add series termination resistors (33–47 Ω) at the source end of high-speed single-ended traces to damp reflections.

## Revision Control

- Store all KiCad project files in Git: `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, `.kicad_mod`.
- Disable **"Save with full paths"** in KiCad Preferences → Common to ensure footprint and symbol paths are stored as relative paths, making the project portable across developer machines.
- Use **Git LFS** for binary assets: 3D model files (`.step`, `.wrl`), rendered board images, and fabrication PDFs.
- **Tag every release** in Git when Gerbers are sent to fabrication using the convention `fab/v1.0`, `fab/v1.1`. Never modify a tagged revision after ordering.
- Add a `fab` tag in the KiCad PCB title block on every release build so the revision is embedded in the Gerber file headers.
