# Automation toolchain

Contents:

- [The interpreter that can import pcbnew](#the-interpreter-that-can-import-pcbnew)
- [One major version, never opened in a newer editor](#one-major-version-never-opened-in-a-newer-editor)
- [pcbnew traps that return a wrong answer](#pcbnew-traps-that-return-a-wrong-answer)
- [kicad-cli and the headless pipeline](#kicad-cli-and-the-headless-pipeline)
- [Freerouting: judging a route](#freerouting-judging-a-route)
- [Freerouting: process and environment traps](#freerouting-process-and-environment-traps)
- [Copper the router does not draw](#copper-the-router-does-not-draw)
- [The DRC dangling-track quirk](#the-drc-dangling-track-quirk)
- [Renders refuse when 3D models are missing](#renders-refuse-when-3d-models-are-missing)

Companion reference for the [kicad](../SKILL.md) skill. Load it before writing or running a `pcbnew` Python script, scripting `kicad-cli`, running freerouting, or rendering a board inside a pipeline. Every trap below was hit on a real project, and every one produced a wrong board or a wrong verdict rather than a visible error.

---

### The interpreter that can import pcbnew

`pcbnew` is KiCad's Python interface to a board. It belongs to the KiCad installation, not to Python, and imports only into an interpreter that matches the build it shipped with: the bundled `python.exe` in KiCad's `bin` folder on Windows, the distribution's system Python that the KiCad package targets on Linux, and the Python inside the unpacked image for an AppImage. A plain virtual environment does not see it. A virtual environment created from that same interpreter with system site packages enabled does, which is the way to add test tools such as `pytest` without touching the system install.

The dangerous case is the quiet one. A `.pth` file in some other environment, a one-line path bridge into a KiCad package folder, makes `import pcbnew` succeed under the wrong interpreter. With two KiCad major versions installed, it can load the other version's module, and the `ModuleNotFoundError` that used to flag a wrong interpreter never fires. Name the interpreter explicitly in every launcher and pipeline step through one variable, such as `KICAD_PYTHON`, and confirm the build and the module path at the start of every run.

Pass:

```bash
"$KICAD_PYTHON" -c "import pcbnew; print(pcbnew.GetBuildVersion(), pcbnew.__file__)"
```

Fail:

```bash
python scripts/check_board.py board.kicad_pcb
```

Stop on a build that is not the pinned major version, or a module path outside the pinned installation.

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

### pcbnew traps that return a wrong answer

These were found in KiCad 9's SWIG bindings, which KiCad is retiring in favour of its IPC API. Re-test each one on the version in use rather than assuming it is fixed or still present. None of them raises a Python error.

- **Units are nanometres.** Every coordinate, size and drill `pcbnew` returns is in nanometres. Divide by `1e6` for millimetres, or use `pcbnew.ToMM` and `pcbnew.FromMM`. A value a million times too large, or a distance check that never fires, is almost always this.
- **Design settings accept attributes that do not exist.** `BOARD_DESIGN_SETTINGS` is a SWIG proxy with no `__slots__`, so `ds.m_AnyMisspelledRule = x` succeeds, sets a Python-side attribute, and never reaches the board. The rule is not enforced and nothing warns. Assert the name exists before assigning, and never wrap the assignment in a bare `try` and `except: pass`, which turns "this build has no such rule" into "this rule is silently off".
- **A C++ assertion hangs a headless script.** Some calls trip an assertion inside KiCad, for example asking a via for its width with no layer argument once vias carry per-layer padstacks. The assertion opens a modal dialog nobody sees, and the script waits forever. `try` and `except` cannot catch it because it fires below Python. Avoid the call, read the value another way (a fixed worst-case size, or the raw file text), create vias by writing their text into the board file rather than through the via object, keep via creation and zone fill in separate scripts, and give every scripted step a timeout.
- **Zone outline edits are non-deterministic.** Reading a zone outline and writing a new one have each crashed the process or written a zero-byte board file, on some runs and not others. Resolve every net and pad value before removing any zone, build a fresh polygon set and attach it, never read the outline back, then run the stage several times and confirm the saved file is non-empty and holds the expected zones.
- **Enum orderings change between versions.** Zone island removal is `0` always, `1` never, `2` below an area threshold. A value remembered from an older version's ordering left isolated copper islands that survived every refill.
- **The file token and the display name differ.** The board file writes `F.SilkS`, while `pcbnew` and the user interface show `F.Silkscreen`. A text scan of the file for the display name, or an API filter on the file token, matches nothing and reports a clean result. Match each name in its own context.
- **Per-pad overrides moved.** Per-pad zone connection lives on the `SetLocal...` methods, and some of those setters reject a plain integer because the binding expects an optional value. Where a per-pad setter refuses, set the value on the zone, and read back what was saved.

Pass:

```python
ds = board.GetDesignSettings()
assert "m_MinThroughDrill" in dir(ds)
ds.m_MinThroughDrill = pcbnew.FromMM(0.3)
```

Fail:

```python
try:
    ds.m_ViasMinDrill = pcbnew.FromMM(0.3)
except Exception:
    pass
```

That attribute does not exist, so the assignment succeeds, the `except` never runs, and the via drill floor is never enforced.

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

### Freerouting: judging a route

Never judge a route by the router's exit code. The router exits 0 whether or not it finished. Never judge it by the router's summary line either. The "unrouted" count is a bare integer with no net names, it includes power-plane nets deliberately left to a zone fill, and a headless run can write a session file older than its own summary (next section). Run the router through a committed wrapper and let the wrapper decide.

The only reliable verdict comes from the board itself. Import the session file into a throwaway copy of the board, refill zones, run DRC, and read the unconnected items. Exempt only a net carried by a filled inner-layer zone, or one named explicitly, never "any one net". Also reject any `track_dangling` or `via_dangling` finding, and run the gate's own post-route checks (differential-pair skew, decoupling distance) against the same copy. "Nothing unconnected" alone accepted routes that then failed later steps: a track parked where a scripted connection had to land, a pair over its skew limit, a dangling stub on a net still joined some other way.

Pass:

```text
Attempt 3 imported into a scratch copy, zones refilled. DRC: 0 unconnected outside the two plane nets, 0 dangling. Skew and decoupling audits pass on the copy. Accepted.
```

Fail:

```text
Router exited 0 and printed "1 unrouted". That must be the plane net. Imported into the real board.
```

Freerouting is not deterministic. The same design file can route completely on one attempt and leave a connection open on the next, so the wrapper retries a fixed number of attempts. Each attempt is the same unmodified router on the same unmodified design file, so a retry is not a hand finish. A board that regularly needs many attempts has a placement problem: move parts, do not keep retrying.

The router reads the Specctra design file KiCad exports, which carries netclass widths and clearances. A clearance granted only by a custom rule or a rule area does not reach it. Put any clearance the router must honour into a netclass, so the router and DRC work to the same number.

Choose one freerouting major version and stay on it. Versions 1 and 2 take different command-line flags, and their session files are not interchangeable.

Read the flags against the router's own source before relying on them. In version 2, the pass limit `-mp` is read only on the graphical path, and the thread-count flags reach only the route optimiser, which never runs on a KiCad export because KiCad does not write the design-file settings block that switches it on. The log confirms it: optimisation "completed" in a hundredth of a second with the score unchanged. The CPU and memory figures in the same log are not real usage. Editing the router's settings file on disk does not stick, because the loader merges its built-in defaults back over it. Changing any of these in the middle of a diagnosis only adds an unproven variable.

---

### Freerouting: process and environment traps

1. **Two runs sharing one output path destroy each other's result.** A wrapper that deletes an incomplete session file at the end of a failed attempt can delete the file another run just wrote. Both then fail for a reason unrelated to the board, and each failure gets blamed on a fresh cause. Never start a second run while one is in flight.
2. **Match the router by its jar, never by the process name `java`.** IDEs such as IntelliJ IDEA and PyCharm run on the same JVM, so a kill by name closes them and loses unsaved work while doing nothing about routing.
3. **Match the wrapper too.** Between two retries the wrapper is alive and holds the board while no Java child exists, so a Java-only check reads "free" while a run is in flight. The wrapper's command line also names the board it holds. A finished agent can leave its wrapper running, and a killed run can leave its Java child running.
4. **A headless run can write a stale session file.** With no screen, freerouting 2 writes the session file only when the original board object reports an update, while its "restore an earlier board" step swaps in a different object, so later progress never reaches the file. Headless runs also use different preferred layer directions and ignore `-mp`. On Linux, run the router under a virtual screen (`xvfb-run`) so it takes the graphical path, and let the import-and-DRC check decide either way.
5. **The graphical path can wait forever on a dialog nobody sees.** Once its shared settings file records a handful of finished jobs and no email address, the router opens a profile dialog after a job and stops. Give every attempt a fresh `--user_data_path` folder and delete it afterwards.
6. **Time out each attempt inside the wrapper.** Kill the attempt's whole process group, so the virtual screen and the Java child die with it. An external timeout shorter than the full retry loop kills the loop and looks like the router hanging.
7. **The sponsor window is normal.** Freerouting opens an advertisement window on launch. It is not a sign of failure.

Before drawing any conclusion from a failed route, list both kinds of process. On Windows, the router:

```powershell
Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Where-Object { $_.CommandLine -like '*freerouting*' } | Select-Object ProcessId, CreationDate
```

Then the wrapper, keeping the filter on the process name so the shell asking the question does not match its own command line:

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*<wrapper-script-name>*' } | Select-Object ProcessId, CreationDate, CommandLine
```

On Linux, select by process name first for the same reason:

```bash
ps -C java -o pid=,args= | grep -F freerouting
```

No rows from both listings means no run is in flight. Rows from either mean one is. Never pipe either listing into a kill unfiltered. Then read the wrapper output and the router log in full, check whether a session file was written and what the wrapper said about it, and only then suspect the placement.

---

### Copper the router does not draw

No copper is drawn by hand in the editor, as a fallback or for any other reason. A hand-drawn track is wiped by the next rebuild that clears tracks, and nothing can reproduce it, so the board stops being rebuildable from its source. If the router cannot find a path, change the placement.

One exception holds: a committed, deterministic script that runs as a pipeline step before the router may lay locked copper for a net the router handles badly, such as a differential pair it cannot length-match. The script re-applies its copper on every rebuild, and every net it draws passes the same gate checks as a routed one. This is the third option beside the two in [signal-integrity.md](signal-integrity.md#routed-by-hand-and-locked-or-autorouted-and-measured), and the only one that survives a rebuild.

Locked tracks and vias present before the design-file export become obstacles the router routes around. Freerouting does not echo that fixed wiring back into its session file, though, and an import step that clears every track before importing the session loses it. Re-run the script after the import, and dry-run it against the throwaway copy while judging the route, so a route that blocks it is rejected before it reaches the real board.

---

### The DRC dangling-track quirk

KiCad connects a track end that lies on the middle of another track of the same net. Its dangling test, though, credits the neighbouring track to whichever end of the short track lies nearer one of the neighbour's own end points. When both ends of a short track fall within the width of a long track, for example a router wire that ends on the middle of a locked bridge, the credit lands on one end and DRC reports the other as `track_dangling`, while the copper is electrically fine. This was read in KiCad 9's connectivity code and confirmed by predicting DRC's result on several boards. Re-test it on the version in use.

The fix is geometry, not an exclusion. Split the long track with a vertex at every point where another track ends on it, so each join lands on an end point. A script that lays locked copper which routed wires will join should, after the import, find every unlocked track end and via of the same net lying on its line, lay the copper as a chain of pieces through exactly those points, and remove all of its earlier pieces on a re-run.

Pass:

```text
Bridge laid as three locked pieces with vertices at both router join points. DRC: 0 track_dangling.
```

Fail:

```text
Bridge laid as one straight piece. Two short router wires end on its middle. DRC: 2 track_dangling, added to the exclusion list.
```

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
