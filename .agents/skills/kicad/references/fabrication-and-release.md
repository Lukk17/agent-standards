# Fabrication and Release

Contents:

- [Bill of materials](#bill-of-materials)
- [Gerber and drill export](#gerber-and-drill-export)
- [Revision control](#revision-control)

Companion reference for the [kicad](../SKILL.md) skill. Load it for the BOM field table and `kicad-cli` command, the Gerber layer table and export commands, and the Git and release tagging rules.

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
