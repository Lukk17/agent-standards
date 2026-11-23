# Scope

Companion reference for the [kicad](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Setting up board constraints, netclasses, or custom design rules.
- Routing tracks, pouring copper, or placing decoupling.
- Running ERC or DRC, or interpreting a clean report.
- Creating or verifying footprints and 3D models.
- Generating a BOM, Gerbers, or drill files for fabrication.
- Writing a `pcbnew` script, running freerouting, or placing an assembly order.
- Deciding what of a KiCad project goes into Git and how a release is tagged.
- The user says "route this board", "check my DRC", "export gerbers for JLCPCB", "generate a BOM with LCSC part numbers" or "write a kicad_dru rule for mains clearance".

The skill covers board setup and custom DRC rules, IPC-2221 trace sizing, decoupling, ground pours, ERC, BOM, Gerber export, Git, pcbnew scripting, freerouting and assembly orders.

---

### When not to activate

- Writing the firmware that runs on the board, use `embedded-c-arduino`.
- Designing or slicing a 3D-printed enclosure for the board, use `g-code-3d-printing`.
- Documenting the project for other people to read, use `markdown-writer`.
- Setting up the CI that runs the export, use `deployment-patterns`.
- Writing an export or checking script in shell, use `bash` or `powershell`.

---

### Related skills

- `embedded-c-arduino` for the firmware and the hardware abstraction on the other side of the connector.
- `g-code-3d-printing` for the printed enclosure the board mounts into.
- `markdown-writer` for the project README and the hardware documentation.
- `deployment-patterns` for CI that runs ERC, DRC, and the export on every change.
- `bash` and `powershell` for the export and checking scripts themselves.
