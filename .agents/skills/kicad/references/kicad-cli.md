# kicad-cli

Contents:

- [One major version, never opened in a newer editor](#one-major-version-never-opened-in-a-newer-editor)
- [kicad-cli and the headless pipeline](#kicad-cli-and-the-headless-pipeline)
- [Renders refuse when 3D models are missing](#renders-refuse-when-3d-models-are-missing)

Companion reference for the [kicad](../SKILL.md) skill. Load it before scripting `kicad-cli`, or rendering a board inside a pipeline. Every trap below was hit on a real project, and every one produced a wrong board or a wrong verdict rather than a visible error. The `pcbnew` scripts a pipeline runs are covered in [pcbnew.md](pcbnew.md), and its routing step in [freerouting.md](freerouting.md).

---

### One major version, never opened in a newer editor

Pin the project to one KiCad major version and record the pin where every script and agent reads it. Never open its `.kicad_sch` or `.kicad_pcb` in a newer major version's editor. Saving there upgrades the file format with no prompt, and the older version's `kicad-cli` and `pcbnew` can no longer parse the file. Nothing announces the change, so the first sign is a script failing on a file nobody meant to edit. Revert it from version control before running anything against it.

Run `kicad-cli --version` at the start of the pipeline. A version bump is a deliberate decision with its own full validation run, never something discovered mid-task.

Pass:

```text
Pinned major version recorded in AGENTS.md and the launcher. kicad-cli --version checked before the first step.
```

Fail:

```text
Board opened in the newer editor to look at one footprint, saved on close, committed with the next change.
```

---

### kicad-cli and the headless pipeline

Generate the gate's list of checks from one source in code, and have the gate compare the number of checks it executed with the number it declares, refusing to report a result when they differ. A hand-typed copy of the list in a document drifted until it ran a fraction of the real checks while still finishing clean.

Read every check's full output on both streams. A gate that kept only standard output, and only its last line, recorded a script that logged its failure to standard error and exited 0 as a silent pass.

Run the whole pipeline in order after any change, and skip nothing. Several steps exist only to restore what an earlier step in the same run destroys on purpose: a netlist import that rebuilds footprints from the library drops any per-footprint correction injected earlier, a step that deletes every zone also deletes a keepout drawn as a zone, and a step that closes copper fragments has to run after the last refill because every earlier refill reshapes the pour. An omitted step does not fail. It ships a board missing a property nobody checks for.

On a fresh Linux install, KiCad's `sym-lib-table` and `fp-lib-table` may not exist in the user configuration folder until copied from KiCad's template folder. Without them `kicad-cli sch erc` reports a library issue for every symbol library it cannot resolve. Copy them once:

```bash
cp /usr/share/kicad/template/sym-lib-table /usr/share/kicad/template/fp-lib-table ~/.config/kicad/<version>/
```

A plugin that drives `kicad-cli` breaks when a major version removes a flag it passes. `kicad-cli pcb drc --refill-zones` went away in KiCad 9, and an export plugin that still passed it as a pre-flight showed an unknown-argument dialog instead of exporting. Turn off the plugin's own pre-flight DRC when the gate already runs one, or use a plugin that does not call it.

Normalise line endings before hashing a board file. Git checks out text with different line endings on Windows and Linux, so the same commit hashed differently on the two systems until the hash read every line ending one way.

---

### Renders refuse when 3D models are missing

A render made on a machine without KiCad's 3D model library, which is a separate package on most Linux distributions, or with the model-folder variable pointing at nothing, draws every part as bare pads. A render with no bodies cannot answer the questions a render exists for: a body crowding a connector, a tall part overhanging its neighbour, a polarity mark on the body. A warning in a log nobody reads is the same as silence. Body-less renders on one project were committed and walked as if they were complete.

Have the render step check, before it draws anything, that every fitted part's model file resolves. If any is missing, exit non-zero, name each missing file and the model folder in use, say how to install the library, and write nothing. Allow an explicit opt-out flag only for a copper-only plot, and record in the render's manifest which parts had no model.

Pass:

```text
error: N populated part(s) have no 3D model file, so they would show as bare pads with no body. Model folder in use: <path>. Install the KiCad 3D model library or point the model-folder variable at it. Exit 2, nothing written.
```

Fail:

```text
WARNING: N populated part(s) have no resolvable 3D model. Render written, exit 0.
```

Render to a scratch folder when the render step also refreshes a committed snapshot, so a validation run does not rewrite the committed pictures it is meant to compare against.
