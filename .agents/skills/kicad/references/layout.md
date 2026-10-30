# Layout

Contents:

- [Board setup and custom design rules](#board-setup-and-custom-design-rules)
- [Trace sizing, IPC-2221](#trace-sizing-ipc-2221)
- [Placement and decoupling](#placement-and-decoupling)
- [Ground pours and thermal reliefs](#ground-pours-and-thermal-reliefs)
- [Footprints, libraries, and 3D models](#footprints-libraries-and-3d-models)
- [Hierarchical schematics and ERC](#hierarchical-schematics-and-erc)

Companion reference for the [kicad](../SKILL.md) skill. Load it for the reasoning, the `.kicad_dru` example and the pass and fail cases behind board setup, trace sizing, placement and decoupling, ground pours and thermal reliefs, footprints, and hierarchical schematics.

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
