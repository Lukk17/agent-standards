# Fabrication and Release

Contents:

- [Bill of materials](#bill-of-materials)
- [Gerber and drill export](#gerber-and-drill-export)
- [Fabrication limits: aim above the floor](#fabrication-limits-aim-above-the-floor)
- [The export plugin: pin the release, verify by hash](#the-export-plugin-pin-the-release-verify-by-hash)
- [Check the bundle that is actually uploaded](#check-the-bundle-that-is-actually-uploaded)
- [The IPC-D-356 test netlist truncates net names](#the-ipc-d-356-test-netlist-truncates-net-names)
- [Placement rotation](#placement-rotation)
- [Assembly: board size, edge rails and depanelling](#assembly-board-size-edge-rails-and-depanelling)
- [Assembly options that default the wrong way](#assembly-options-that-default-the-wrong-way)
- [Assembly stock is not retail stock](#assembly-stock-is-not-retail-stock)
- [Revision control](#revision-control)

Companion reference for the [kicad](../SKILL.md) skill. Load it for the BOM field table and `kicad-cli` command, the Gerber layer table and export commands, fabrication limits, the export plugin pin, the test netlist, placement rotation, assembly ordering and stock, and the Git and release tagging rules.

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

### Fabrication limits: aim above the floor

A fabricator's published minimum is the point where its process is still capable, not the point where it is reliable. Normal drill wander or etch spread lands a design that sits exactly on the floor on the wrong side of it. Where the fabricator publishes a recommended value as well as a minimum, design to the recommended one. Where it publishes only a minimum, design to a fixed multiple of it, such as one and a half times. Put that number into Board Setup or `.kicad_dru` as the enforced limit, and record the source page beside each one.

Before arguing a limit down for one awkward part, write down what physically breaks below it. "Both neighbours are the same net, so it is not a short" can be true and still miss the failure.

| Limit | What goes wrong below it |
|---|---|
| Annular ring | The drill breaks out through the side of its own pad. A broken-out via often works on the bench and fails later under thermal cycling, so it ships. |
| Hole to hole | The web between two holes tears out and merges them into one slot. |
| Unplated hole to copper | The drill eats into the neighbouring pad. Same net or not, the joint loses copper, a burr can lift the pad, and bare copper sits in the hole wall. On a connector that takes mechanical load, that is a real failure. |
| Plated hole to copper | As above, plus a short when the neighbour is on another net, because the hole wall is copper. |
| Track width and copper to copper | Etching eats sideways. A track near the floor comes out thin, nicked or open, and two tracks too close can stay joined by a sliver. |
| Copper to board edge | The routing bit cuts into the copper and leaves it exposed on the rim. |
| Solder mask dam | The two openings merge and solder bridges the pads, the most common defect on fine-pitch parts. |
| Silkscreen width, height, pad clearance | Thin or small text prints illegibly. Ink on a pad stops solder wetting. Some fabricators, JLCPCB among them, delete silkscreen too close to a pad during review, so cut it back yourself and the files show what will actually print. |

---

### The export plugin: pin the release, verify by hash

When a KiCad plugin, such as a Fabrication Toolkit, writes the bundle the assembler receives (Gerber zip, BOM, placement file, test netlist), the plugin's own release decides that output. Its rotation table, its options file format and its column layout change between releases. Pin it to one exact release, and verify every one of its code and data files by hash before each export, because a folder installed through KiCad's Plugin and Content Manager may carry no version number at all.

A driver script that runs the plugin should refuse in each of these cases, all seen on one project:

- **A different release.** Any file whose hash does not match the pinned release stops the export, naming the file.
- **A rotation table the checks do not read.** A plugin may read its rotation table only from its own folder. Make the project's rotation checks read that same file, or refuse.
- **An unknown option.** An options file written by one release may be read differently by another. Stop on any option the pinned release does not have.
- **Output not rewritten.** A plugin's command-line mode can ignore the options file and exit 0 when it crashes. Check that every output file was rewritten by this run and that the plugin logged no error.

Normalise the CSV line endings before committing, because a plugin may write Windows line endings on every system. Expect the copper refill an export runs to move a zone corner very slightly on some runs, so two exports of one board are not always byte-identical.

Pass, recorded in the project as placeholders resolved from the tagged release:

```text
export plugin: <plugin-name> release <x.y.z>
sha256 <plugin-file-1>: <sha256-of-that-file-at-the-release-tag>
sha256 <rotation-table-file>: <sha256-of-that-file-at-the-release-tag>
```

Resolve each value from a checkout of the release tag, with line endings normalised before hashing:

```bash
git clone --depth 1 --branch <release-tag> <plugin-repository-url>
```

```bash
sha256sum <plugin-file>
```

Fail:

```text
Plugin updated by the plugin manager between two exports. Placement file rotations changed. Nobody noticed until the assembler's preview.
```

Put assembly part numbers where the plugin reads them. A plugin that fills the BOM's assembly part-number column from a footprint property in the board file (a property named `LCSC`, for example) ignores a CSV edited after export. One project shipped a BOM with every part-number cell empty for exactly this reason. Carry the field from the schematic symbol to the footprint, or inject it into the board file by script, and fail the export check on any empty cell.

---

### Check the bundle that is actually uploaded

A project often holds two exports: a `kicad-cli` export kept for reference and the plugin's bundle that is actually uploaded. Name the uploaded folder in the project's ordering document, never order from the other one, and run the cross-checks (BOM against the board, placement file against the board, export freshness against the board file) on the uploaded bundle itself.

---

### The IPC-D-356 test netlist truncates net names

The IPC-D-356A netlist in the bundle is what the fabricator's flying-probe tester reads to know which pads must be joined and which must not. Its net-name field is 14 characters wide. KiCad's exporter, read in the KiCad 9 source, replaces a non-printable character with `?`, upper-cases the name, keeps the last 14 characters of a longer name, and when two nets would then carry the same text, writes the later one as its last 10 characters plus `#1`, `#2` and so on.

Two consequences matter. First, a checker that compares full board net names against the file reports a correct file as wrong. It has to apply the same rule. Second, the checker has to fail when one written name stands for two board nets, which a tester treats as one connection and never tests for a short between, and when one board net appears under two names, which a tester reports as open. A checker also has to read pads on unconnected nets, because the exporter writes them.

Keep net names unique in their last 14 characters, upper-cased, so the test file needs no `#n` suffixes and a person reading it can tell the nets apart.

Pass:

```text
/PSU_A_VOUT_FB and /PSU_B_VOUT_FB are 14 characters each, so both are written whole and stay distinct.
```

Fail:

```text
/PSU_A/VOUT_SENSE_FB and /PSU_B/VOUT_SENSE_FB both truncate to /VOUT_SENSE_FB. The second is written as T_SENSE_FB#1, and nobody can read which supply it belongs to.
```

---

### Placement rotation

Three different things decide which way round a part goes, and only two are standardised. How a part lies in its tape is fixed by EIA-481 and printed in the maker's datasheet, per orderable part number. How a footprint is drawn at zero rotation is fixed by IPC-7351B and by IEC 61188-7, whose preferred conventions differ (KiCad follows IPC's, which IEC calls level A). The number in the placement file's rotation column is standardised by nobody: IEC 61188-7 puts it out of scope, and each assembler reconciles it its own way.

The rotation tables export plugins ship are community-maintained approximations of one assembler's reconciliation, offered by their maintainers on a best-effort basis, and two widely used copies disagree on common packages. A footprint name matching no pattern in the table is exported at zero degrees in silence.

- Treat rotation as belonging to the exact supplier part number ordered, never to the package family. The same package from the same maker can sit differently in the tape.
- Measure each part's rotation against the assembler's own footprint drawing for that part number rather than trusting the table.
- A two-pad part whose pads are identical in size and shape cannot be decided by geometry, because the drawing looks the same after a half turn. Which pad is numbered 1 is a drawing habit, and the habits differ (a CAD library and a supplier can number opposite ends of the same LED as pin 1). Read polarity from the maker's datasheet.
- Print a polarity mark on the silkscreen beside every polarity-sensitive part. Assemblers that correct rotation do it by reading the silkscreen.
- Walk the assembler's rendered placement preview part by part before paying, and turn on the assembler's placement confirmation where offered.

---

### Assembly: board size, edge rails and depanelling

Assembly lines publish a minimum single-board size, because the conveyor and fixtures need something to grip. JLCPCB's Standard assembly, for example, lists 70 by 70 mm on its capability page. Read the current page for the assembler and tier you order. A board under the minimum is not refused. The assembler adds edge rails, strips of scrap board joined to your edges by mouse bites or a V-cut, so the piece the machine handles is bigger than your board, and adds tooling holes if your files carry none.

By default the finished boards ship with the rails still attached. Removing them is a separate option on the order form (JLCPCB calls it "Depanel boards & edge rail"), and it has to be selected explicitly. Select it whenever mounting holes or edge connectors sit close to an edge the rails join: snapping a rail off by hand near a hole risks cracking the board around it, and the assembler's tooling removes it more safely. State the request in the assembly remark as well.

Do not respond to an undersized board by drawing a panel in KiCad. For a small order, panelisation is an order-form option that needs no file change, and editing a gate-clean board to add one means regenerating and revalidating the whole bundle for no benefit.

Fiducials are the board's own job even when the assembler adds rails. Place at least three, a copper dot with a larger solder-mask opening, asymmetrically near the corners of the side that carries the fine-pitch parts. Two cannot resolve rotation, and a symmetric set lets the machine solve the board 180 degrees out and still report success.

---

### Assembly options that default the wrong way

Assembly order forms default to the cheapest case. Check each of these against the board rather than accepting the default:

- **Through-hole assembly.** Some services assemble surface-mount parts only unless through-hole assembly is requested. Without the request every through-hole part arrives unfitted. Say "surface-mount and through-hole assembly required" in the assembly remark and list the through-hole parts. The assembler's part library often tags such parts as hand-soldered, which is expected.
- **Double-sided placement.** The cheapest assembly tier may place one side only. A board with surface-mount parts on both faces needs the tier that places both.
- **Placement and photo confirmation.** Turn on whatever lets you approve the placement before it runs. It is cheap next to a wrong build.

---

### Assembly stock is not retail stock

An assembler's own parts pool, the parts its pick-and-place line draws from, is a different pool from the same distributor's retail shop. Read the assembly stock on the assembler's own part pages or interface. A third-party mirror can disagree with the assembler's figures. A healthy retail listing says nothing about whether the line can build the board.

- **Count against the real minimum.** A part can need a minimum quantity plus an attrition allowance (the parts a machine wastes loading a new reel). A pool holding fewer than that is effectively empty, whatever the number.
- **Set a margin and flag below it.** Flag any part whose assembly stock is under a fixed multiple of the order's need. One project used ten times.
- **Unknown is not zero.** A lookup that returns nothing, text, or a non-integer is "stock unknown" and is reported as such, never read as zero and never as healthy.
- **Low or zero stock is a warning, not a reason to swap.** A validated part has had its footprint, rotation, datasheet limits and circuit checked. Swapping it for stock reasons throws that work away. Report the shortfall with the count and the date it was read, wait for restock, or let the board owner decide on a documented drop-in alternative chosen in advance.
- **Re-read on the day of ordering.** Stock moves daily, and a part can go from hundreds to zero overnight.

The design-time preference for parts stocked by two distributors still holds. It reduces how often the order-time warning fires, without making a swap at order time any safer.

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
