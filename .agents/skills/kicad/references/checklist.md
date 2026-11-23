# KiCad Checklist

Run it before a board goes to fabrication or an assembly order is placed.

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
- [ ] `pcbnew` build confirmed, route accepted by DRC on a copy, renders refused while any 3D model was missing.
- [ ] Export plugin hashes match the pin, IPC-D-356 names unique, rotations checked against the assembler's preview.
- [ ] Assembly stock read on the order day, through-hole and depanel options set where the board needs them.
