# Freerouting

Contents:

- [Freerouting: judging a route](#freerouting-judging-a-route)
- [Freerouting: process and environment traps](#freerouting-process-and-environment-traps)
- [Copper the router does not draw](#copper-the-router-does-not-draw)
- [The DRC dangling-track quirk](#the-drc-dangling-track-quirk)

Companion reference for the [kicad](../SKILL.md) skill. Load it before running freerouting, or before scripting copper the router will join. Every trap below was hit on a real project, and every one produced a wrong board or a wrong verdict rather than a visible error.

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

1. Two runs sharing one output path destroy each other's result. A wrapper that deletes an incomplete session file at the end of a failed attempt can delete the file another run just wrote. Both then fail for a reason unrelated to the board, and each failure gets blamed on a fresh cause. Never start a second run while one is in flight.
2. Match the router by its jar, never by the process name `java`. IDEs such as IntelliJ IDEA and PyCharm run on the same JVM, so a kill by name closes them and loses unsaved work while doing nothing about routing.
3. Match the wrapper too. Between two retries the wrapper is alive and holds the board while no Java child exists, so a Java-only check reads "free" while a run is in flight. The wrapper's command line also names the board it holds. A finished agent can leave its wrapper running, and a killed run can leave its Java child running.
4. A headless run can write a stale session file. With no screen, freerouting 2 writes the session file only when the original board object reports an update, while its "restore an earlier board" step swaps in a different object, so later progress never reaches the file. Headless runs also use different preferred layer directions and ignore `-mp`. On Linux, run the router under a virtual screen (`xvfb-run`) so it takes the graphical path, and let the import-and-DRC check decide either way.
5. The graphical path can wait forever on a dialog nobody sees. Once its shared settings file records a handful of finished jobs and no email address, the router opens a profile dialog after a job and stops. Give every attempt a fresh `--user_data_path` folder and delete it afterwards.
6. Time out each attempt inside the wrapper. Kill the attempt's whole process group, so the virtual screen and the Java child die with it. An external timeout shorter than the full retry loop kills the loop and looks like the router hanging.
7. The sponsor window is normal. Freerouting opens an advertisement window on launch. It is not a sign of failure.

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
