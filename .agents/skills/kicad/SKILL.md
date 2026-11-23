---
name: kicad
description: 'KiCad board design: board setup, DRC rules, trace sizing, ERC, BOM, Gerber export, pcbnew scripts, freerouting. Use when the user says "route this board" or "export gerbers". Not for firmware, use `embedded-c-arduino`.'
metadata:
  version: "1.2.0"
---

# KiCad PCB Design Standards

How a board gets from schematic to fabrication without a respin: rules configured before the first track, checks that are actually enabled, and an export that matches what the fabricator expects. Most board failures trace back to a constraint that existed only in someone's head.

Written for KiCad 10. Custom design rules in `.kicad_dru` and the `kicad-cli` command-line exporter are both standard in that version.

---

### When not to activate

- Writing the firmware that runs on the board, use `embedded-c-arduino`.
- Designing or slicing a 3D-printed enclosure for the board, use `g-code-3d-printing`.
- Setting up the CI that runs the export, use `deployment-patterns`.

---

### Reference files

| Open this | For |
|---|---|
| [layout.md](references/layout.md) | Board setup and `.kicad_dru`, trace sizing and spacing, decoupling, pours, thermal reliefs, footprints, schematic sheets, ERC |
| [fabrication-and-release.md](references/fabrication-and-release.md) | BOM, Gerber export, fabrication limits, the export plugin, the IPC-D-356 netlist, rotation, assembly orders, Git and release tags |
| [signal-integrity.md](references/signal-integrity.md) | A differential pair: skew budget, target impedance, length tuning |
| [verification-discipline.md](references/verification-discipline.md) | Deciding whether a clean DRC or a passing check proves anything |
| [pcbnew.md](references/pcbnew.md) | A `pcbnew` script: its interpreter and its silent traps |
| [kicad-cli.md](references/kicad-cli.md) | Scripting `kicad-cli`: the version pin, the headless pipeline, renders |
| [freerouting.md](references/freerouting.md) | Running freerouting: judging a route, process traps, scripted copper, the dangling-track quirk |
| [scope.md](references/scope.md) | Whether a neighbouring skill owns the job |
| [checklist.md](references/checklist.md) | Before fabrication or an assembly order |

---

### Rules

1. Set track width, clearance, via size and via drill from the fabricator's published capabilities before placing a component. What Board Setup cannot express goes in `.kicad_dru`, never in a note.
2. Run DRC continuously to zero errors before export. Never override or ignore a violation: fix the board, or fix the rule and record why.
3. Size power nets from IPC-2221 at maximum continuous current, never at the default width.
4. No 90-degree corners.
5. Every IC power pin gets a 100 nF ceramic as close as the footprint allows, with a short, wide, direct connection. Lock connectors and mounting holes after placement.
6. Pour continuous `GND` on the bottom, and the top where space allows. Avoid splits, and stitch the pours with vias.
7. Decide pad-to-pour connection per pad: thermal relief for hand- or wave-soldered through-hole joints, solid for reflow pads that carry current or sink heat.
8. Use official verified footprints, a custom one only when the land pattern differs, checked against IPC-7351 and kept in the project. Every footprint maps a 3D model.
9. One schematic sheet per functional block, `PWR_FLAG` on every power net sourced from a connector or regulator, and ERC to zero errors before netlist export or layout.
10. Generate the BOM from the schematic, never by hand, and commit it under `docs/bom/`.
11. Export every layer the board uses plus separate PTH and NPTH drill files, run DRC again, and open the output in an independent viewer.
12. Commit the KiCad text files, disable "Save with full paths", and track binary assets with Git LFS.
13. Tag `fab/vX.Y` when Gerbers are sent, and never rewrite a tag after ordering.
14. Never open the project in a newer major version of KiCad, and run `pcbnew` only on the pinned KiCad's own interpreter.
15. Before a scripted route, an export through the plugin, the IPC-D-356 netlist or an assembly order, open that step's reference file, which holds its rules.
