---
name: kicad
description: 'KiCad board design standards for board setup and custom DRC rules, IPC-2221 trace sizing, decoupling and placement, ground pours, ERC, BOM fields, Gerber export and Git handling of project files. Use when the user says "route this board", "check my DRC", "export gerbers for JLCPCB" or "generate a BOM with LCSC part numbers". Not for the firmware that runs on the board, use `embedded-c-arduino`.'
---

# KiCad PCB Design Standards

How a board gets from schematic to fabrication without a respin: rules configured before the first track, checks
that are actually enabled, and an export that matches what the fabricator expects. Most board failures trace back to
a constraint that existed only in someone's head.

Written for KiCad 10. Custom design rules in `.kicad_dru` and the `kicad-cli` command-line exporter are both standard in that version.

---

### When to activate

- Setting up board constraints, netclasses, or custom design rules.
- Routing tracks, pouring copper, or placing decoupling.
- Running ERC or DRC, or interpreting a clean report.
- Creating or verifying footprints and 3D models.
- Generating a BOM, Gerbers, or drill files for fabrication.
- Deciding what of a KiCad project goes into Git and how a release is tagged.
- The user says "write a kicad_dru rule for mains clearance".

---

### When not to activate

- Writing the firmware that runs on the board, use `embedded-c-arduino`.
- Designing or slicing a 3D-printed enclosure for the board, use `g-code-3d-printing`.
- Documenting the project for other people to read, use `markdown-writer`.
- Setting up the CI that runs the export, use `deployment-patterns`.
- Writing an export or checking script in shell, use `bash` or `powershell`.

---

### Reference files

| Open this | For |
|---|---|
| [references/layout.md](references/layout.md) | The `.kicad_dru` example, IPC-2221 sizing, decoupling, pours and thermal reliefs, footprints, schematic sheets, with pass and fail cases |
| [references/fabrication-and-release.md](references/fabrication-and-release.md) | The BOM field table and export command, the Gerber layer table and export commands, Git and release tagging |
| [references/signal-integrity.md](references/signal-integrity.md) | Deriving a skew budget for a differential pair, target impedances, and length tuning |
| [references/verification-discipline.md](references/verification-discipline.md) | Deciding whether a clean DRC or a passing check script actually proves anything |

---

### Rules

1. Set minimum track width, clearance, via size and via drill from the target fabricator's published capabilities before placing a component. Anything the Board Setup dialog cannot express (high-voltage isolation, controlled impedance, per-netclass constraints) goes in `.kicad_dru`, never in a note.
2. Run DRC continuously and reach zero errors before export. Never override or ignore a violation: fix the board, or fix the rule and record why.
3. Size power nets (`VCC`, `+5V`, `+3V3`, `GND`, `VIN`) from IPC-2221, `I = k * dT^0.44 * A^0.725`, at maximum continuous current, never at the default width. Signal traces sit around 0.15 to 0.25 mm.
4. No 90-degree corners. Keep at least twice the trace width between adjacent high-speed or sensitive analog signals.
5. Every IC power pin gets a 100 nF X5R or X7R ceramic as close as the footprint allows, with a short, wide, direct connection. Order bypass then bulk toward the source, separate analog from digital, and lock connectors, mounting holes, switches and crystals after placement.
6. Pour continuous `GND` on the bottom, and the top where space allows. Avoid splits, route nothing across an unavoidable one, and stitch the pours with vias.
7. Decide pad-to-pour connection per pad: thermal relief for hand- or wave-soldered through-hole joints, solid for reflow pads that carry current or sink heat.
8. Use official verified footprints. A custom one only when the land pattern differs, checked against IPC-7351, kept in the project rather than edited in a shared system library, and every footprint maps a `.step` or `.wrl` model.
9. One schematic sheet per functional block, connected by unique descriptive net labels, `PWR_FLAG` on every power net sourced from a connector or regulator, annotated per block. ERC to zero errors before netlist export or layout.
10. Generate the BOM from the schematic with Reference, Value, Footprint, Manufacturer, MPN, LCSC, Datasheet and Quantity, single-quoting `${QUANTITY}`. Prefer parts stocked by two distributors, and commit it under `docs/bom/`.
11. Export every layer the board uses plus separate PTH and NPTH Excellon drill files, run DRC again, and open the output in gerbv or KiCad's Gerber Viewer before it goes to the fab.
12. Commit the KiCad text files, disable "Save with full paths", and track `.step`, `.wrl`, renders and fab PDFs with Git LFS.
13. Tag `fab/vX.Y` when Gerbers are sent, never rewrite a tag after ordering, and put the same revision in the PCB title block.

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
