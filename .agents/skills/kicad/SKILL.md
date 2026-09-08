---
name: kicad
description: KiCad board design standards for board setup and custom DRC rules, IPC-2221 trace sizing, decoupling and placement, ground pours and thermal reliefs, ERC on hierarchical schematics, BOM fields, Gerber and drill export, and Git handling of project files. Use when you say "route this board", "check my DRC", "export gerbers for JLCPCB", "write a kicad_dru rule for mains clearance", or "generate a BOM with LCSC part numbers". Not for the firmware that runs on the board, use `embedded-c-arduino`.
---

# KiCad PCB Design Standards

How a board gets from schematic to fabrication without a respin: rules configured before the first track, checks
that are actually enabled, and an export that matches what the fabricator expects. Most board failures trace back to
a constraint that existed only in someone's head.

Baseline: KiCad 10, current stable (10.0.6 as of September 2026). Custom design rules in `.kicad_dru` and the
`kicad-cli` command-line exporter are both standard on this baseline.

---

### When to activate

- Setting up board constraints, netclasses, or custom design rules.
- Routing tracks, pouring copper, or placing decoupling.
- Running ERC or DRC, or interpreting a clean report.
- Creating or verifying footprints and 3D models.
- Generating a BOM, Gerbers, or drill files for fabrication.
- Deciding what of a KiCad project goes into Git and how a release is tagged.

---

### When not to activate

- Writing the firmware that runs on the board, use `embedded-c-arduino`.
- Designing or slicing a 3D-printed enclosure for the board, use `g-code-3d-printing`.
- Documenting the project for other people to read, use `markdown-writer`.
- Setting up the CI that runs the export, use `deployment-patterns`.
- Writing an export or checking script in shell, use `bash` or `powershell`.

---

### Board setup and custom design rules

Configure minimum track width, clearance, via size, and via drill from the target fabricator's published
capabilities before placing a single component. Add a `.kicad_dru` file for anything the Board Setup dialog cannot
express: high-voltage isolation, controlled-impedance widths, per-netclass constraints.

Pass, mains isolation and a USB pair width, each enforced by the tool:

```lisp
(version 1)

(rule "Mains isolation"
	(constraint clearance (min 8mm))
	(condition "A.NetClass == 'MAINS' && B.NetClass != 'MAINS'"))

(rule "USB pair width"
	(constraint track_width (min 0.20mm) (opt 0.22mm) (max 0.25mm))
	(condition "A.NetClass == 'USB'"))
```

Fail, the same constraint written where nothing enforces it:

```text
Note in the schematic: keep mains traces 8mm from everything else.
```

Run DRC continuously during layout and target zero errors before export. Never override or ignore a violation, fix
the board or fix the rule and record why.

---

### Trace sizing, IPC-2221

Calculate power-net widths from IPC-2221 using the maximum expected continuous current, with KiCad's own trace-width
calculator and the formula `I = k * dT^0.44 * A^0.725`. The default width is never correct for `VCC`, `+5V`, `+3V3`,
`GND`, or `VIN`.

Pass:

```text
VBUS, 2 A continuous, 10 C rise, outer layer, 1 oz copper -> 0.85 mm, set on the POWER netclass.
```

Fail:

```text
VBUS routed at the 0.25 mm board default because it looked thick enough.
```

Signal and logic traces sit around 0.15 to 0.25 mm to stay inside standard etching limits. Never route at 90
degrees, use 45 degrees or a curve, and keep at least twice the trace width between adjacent high-speed or sensitive
analog signals.

---

### Placement and decoupling

Every IC power pin gets a 100 nF X5R or X7R ceramic as close as the footprint allows, with a short wide direct
connection to the pin. Separate analog from digital physically. Lock connectors, mounting holes, switches, and
crystals immediately after placement so routing cannot nudge them.

Pass:

```text
U3 pin 8 (VDD) -> C14 100nF 0402, 1.1 mm away, 0.4 mm track, then via to the GND pour.
```

Fail:

```text
U3 decoupling placed on the far side of the connector where there was room.
```

Order the power delivery network from smallest to largest toward the source: bypass capacitors first, bulk
capacitors behind them.

---

### Ground pours and thermal reliefs

Pour a continuous `GND` fill on the bottom layer, and on the top where space allows, to give every signal a
low-impedance return. Avoid splitting the plane, and if a mixed-signal split is unavoidable, route nothing across
it. Stitch top and bottom pours with vias around the perimeter and around high-frequency parts.

Decide the pad-to-pour connection per pad, not once for the whole board. A thermal relief connects a pad to the pour
through a few narrow spokes so an iron or a wave-solder bath cannot lose its heat into the copper sheet, which is
what actually causes a cold joint. That purpose only exists for hand-soldered and wave-soldered through-hole joints.
A reflow oven heats the whole board at once, and on a reflow pad those same spokes cut the copper cross-section down
to a fraction, throttling both the current path and the thermal path.

Ask two questions per pad: will this joint be hand- or wave-soldered, and does this pad need to carry meaningful
current or sink heat into the pour during operation.

Pass:

```text
J1 through-hole pads, hand-soldered, no current role -> thermal relief.
U7 exposed thermal pad, reflow, sinks heat -> solid connection.
```

Fail:

```text
Zone connection: thermal relief, applied to every pad on the board.
```

KiCad exposes this per pad and per zone: solid, thermal relief, thermal relief for through-hole pads only, or no
connection.

---

### Footprints, libraries, and 3D models

Use official verified library footprints. Create a custom one only when the manufacturer's land pattern differs from
the library entry, and verify SMD pad geometry against IPC-7351 so parts do not tombstone during reflow. Map a
`.step` or `.wrl` model to every footprint, because spatial collisions are cheap to find in the 3D viewer and
expensive to find on an assembled board.

Pass:

```text
Custom footprint in board.pretty/, model in 3d_models/, both committed, land pattern traced to the datasheet.
```

Fail:

```text
Footprint edited in place inside the shared KiCad system library.
```

---

### Hierarchical schematics and ERC

One sheet per functional block: `power_supply.kicad_sch`, `microcontroller.kicad_sch`, `communication.kicad_sch`,
`user_interface.kicad_sch`. Connect between sheets with unique descriptive net labels rather than long wires, and
add `PWR_FLAG` to every power net sourced from a connector or a regulator. Annotate per block, `U1xx` for MCUs,
`C2xx` for filter capacitors, `R3xx` for pull-ups.

Pass:

```text
Net label UART0_TX crosses from microcontroller.kicad_sch to communication.kicad_sch. ERC: 0 errors, 0 warnings.
```

Fail:

```text
Net label NET1 crosses three sheets. ERC: 0 errors, 6 warnings (unconnected power input).
```

Run ERC to zero errors before exporting the netlist or laying out the board.

---

### Bill of materials

Generate the BOM from the schematic, never by hand. Every line carries the fields below, so the board can be quoted
and assembled without anyone opening KiCad.

| Field | Purpose |
|---|---|
| `Reference` | Which designators this line covers |
| `Value` | Resistance, capacitance, voltage rating, tolerance |
| `Footprint` | Confirms the package the price was quoted against |
| `Manufacturer` | Disambiguates an MPN that several vendors reuse |
| `MPN` | The orderable part |
| `LCSC` | Assembly house part number, plus Digi-Key or Mouser where used |
| `Datasheet` | The traceable origin of every value on the line |
| `Quantity` | Per board, after grouping |

Pass:

```bash
kicad-cli sch export bom --fields 'Reference,Value,Footprint,Manufacturer,MPN,LCSC,Datasheet,${QUANTITY}' --group-by 'Value,Footprint,MPN' --output docs/bom/board-bom.csv board.kicad_sch
```

`${QUANTITY}` is a KiCad BOM variable, not a shell one, so the field list is single-quoted. In double quotes the
shell substitutes it away and the quantity column comes out empty.

Fail:

```text
docs/bom/board-bom.xlsx, last edited by hand three revisions ago.
```

Prefer parts stocked by at least two independent distributors, and commit the exported BOM under `docs/bom/`
alongside the schematic.

---

### Gerber and drill export

Export every layer the board uses, then verify the output in an independent viewer before it goes to the fab.

| Layer | File |
|---|---|
| Front copper | `F.Cu` |
| Back copper | `B.Cu` |
| Inner copper | `In1.Cu`, `In2.Cu`, and so on where the stackup has them |
| Front silkscreen | `F.Silkscreen` |
| Back silkscreen | `B.Silkscreen` |
| Front solder mask | `F.Mask` |
| Back solder mask | `B.Mask` |
| Front paste mask | `F.Paste`, for SMD reflow stencils |
| Back paste mask | `B.Paste`, only when the back is reflowed |
| Board outline | `Edge.Cuts` |
| Drill | Excellon, PTH and NPTH as separate files |

Pass:

```bash
kicad-cli pcb export gerbers --output fab/ --layers "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,F.Paste,Edge.Cuts" board.kicad_pcb
```

Then the drill files, Excellon, plated and non-plated separated:

```bash
kicad-cli pcb export drill --output fab/ --format excellon --separate-files --excellon-separate-th board.kicad_pcb
```

Fail:

```text
Plotted F.Cu, B.Cu and Edge.Cuts only, mask and paste left out of the zip.
```

Run DRC once more after export, and open the result in gerbv or KiCad's own Gerber Viewer. The viewer is reading the
files the fab will read, which the layout canvas is not.

---

### Revision control

Commit `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`, `.kicad_sym`, and `.kicad_mod` as text. Disable "Save with full
paths" in Preferences, Common so library paths stay relative and the project opens on another machine. Track binary
assets with Git LFS: `.step`, `.wrl`, rendered images, fabrication PDFs.

Pass:

```bash
git tag fab/v1.1
```

Fail:

```bash
git tag -f fab/v1.0
```

Tag every release at the moment Gerbers are sent, and never modify a tagged revision after ordering. Put the same
`fab` revision in the PCB title block so it is embedded in the Gerber headers and the physical silkscreen.

---

### Reference files

| Open this | For |
|---|---|
| [references/signal-integrity.md](references/signal-integrity.md) | Deriving a skew budget for a differential pair, target impedances, and length tuning |
| [references/verification-discipline.md](references/verification-discipline.md) | Deciding whether a clean DRC or a passing check script actually proves anything |

---

### Related skills

- `embedded-c-arduino` for the firmware and the hardware abstraction on the other side of the connector.
- `g-code-3d-printing` for the printed enclosure the board mounts into.
- `markdown-writer` for the project README and the hardware documentation.
- `deployment-patterns` for CI that runs ERC, DRC, and the export on every change.
- `bash` and `powershell` for the export and checking scripts themselves.

---

### Checklist

- [ ] Board Setup constraints taken from the chosen fabricator's published limits, before any placement.
- [ ] Every board-specific constraint expressed in `.kicad_dru`, not in a note.
- [ ] Power net widths derived from IPC-2221 with a recorded current and temperature rise.
- [ ] No 90-degree track corners.
- [ ] Every IC power pin decoupled with a short, direct, wide connection.
- [ ] Pad-to-pour connection decided per pad, not one blanket setting.
- [ ] Every footprint verified against the datasheet land pattern, every part carries a 3D model.
- [ ] ERC clean, `PWR_FLAG` on every externally sourced power net.
- [ ] DRC clean with no rule downgraded or excluded, and the severity list checked.
- [ ] BOM generated from the schematic with all required fields, committed under `docs/bom/`.
- [ ] Every needed layer plus separate PTH and NPTH drill files exported and opened in an independent viewer.
- [ ] Release tagged `fab/vX.Y`, title block revision matching, tag never rewritten after ordering.
