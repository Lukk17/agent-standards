# G-code and 3D Printing Checklist

Run it before calling generated G-code, a macro or a slicer profile done.

- [ ] No G-code overrides or disables a firmware thermal safety feature.
- [ ] `M109` and `M190` block before the first extrusion, hotend ceiling respected.
- [ ] `G90` and an explicit `M82` or `M83` declared before any move.
- [ ] `G28` precedes every XYZ move, and no coordinate leaves the build volume.
- [ ] Z-hop wraps every travel move over printed material.
- [ ] Complex sequences invoke a Klipper macro rather than inline G-code.
- [ ] Start sequence homes, heats, levels, and purges outside the part, with no hard-coded Z-offset.
- [ ] End sequence retracts, lifts, parks clear, and cuts heaters and fan.
- [ ] Every `F` value is in mm/min.
- [ ] Pressure advance, extrusion multiplier, and retraction recorded per filament.
- [ ] Slicer profile committed, and its name and version stamped in the G-code header.
