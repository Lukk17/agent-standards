# pcbnew

Contents:

- [The interpreter that can import pcbnew](#the-interpreter-that-can-import-pcbnew)
- [pcbnew traps that return a wrong answer](#pcbnew-traps-that-return-a-wrong-answer)

Companion reference for the [kicad](../SKILL.md) skill. Load it before writing or running a `pcbnew` Python script. Every trap below was hit on a real project, and every one produced a wrong board or a wrong verdict rather than a visible error. The version pin the interpreter check relies on is in [kicad-cli.md](kicad-cli.md#one-major-version-never-opened-in-a-newer-editor).

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

### pcbnew traps that return a wrong answer

These were found in KiCad 9's SWIG bindings, which KiCad is retiring in favour of its IPC API. Re-test each one on the version in use rather than assuming it is fixed or still present. None of them raises a Python error.

- Units are nanometres. Every coordinate, size and drill `pcbnew` returns is in nanometres. Divide by `1e6` for millimetres, or use `pcbnew.ToMM` and `pcbnew.FromMM`. A value a million times too large, or a distance check that never fires, is almost always this.
- Design settings accept attributes that do not exist. `BOARD_DESIGN_SETTINGS` is a SWIG proxy with no `__slots__`, so `ds.m_AnyMisspelledRule = x` succeeds, sets a Python-side attribute, and never reaches the board. The rule is not enforced and nothing warns. Assert the name exists before assigning, and never wrap the assignment in a bare `try` and `except: pass`, which turns "this build has no such rule" into "this rule is silently off".
- A C++ assertion hangs a headless script. Some calls trip an assertion inside KiCad, for example asking a via for its width with no layer argument once vias carry per-layer padstacks. The assertion opens a modal dialog nobody sees, and the script waits forever. `try` and `except` cannot catch it because it fires below Python. Avoid the call, read the value another way (a fixed worst-case size, or the raw file text), create vias by writing their text into the board file rather than through the via object, keep via creation and zone fill in separate scripts, and give every scripted step a timeout.
- Zone outline edits are non-deterministic. Reading a zone outline and writing a new one have each crashed the process or written a zero-byte board file, on some runs and not others. Resolve every net and pad value before removing any zone, build a fresh polygon set and attach it, never read the outline back, then run the stage several times and confirm the saved file is non-empty and holds the expected zones.
- Enum orderings change between versions. Zone island removal is `0` always, `1` never, `2` below an area threshold. A value remembered from an older version's ordering left isolated copper islands that survived every refill.
- The file token and the display name differ. The board file writes `F.SilkS`, while `pcbnew` and the user interface show `F.Silkscreen`. A text scan of the file for the display name, or an API filter on the file token, matches nothing and reports a clean result. Match each name in its own context.
- Per-pad overrides moved. Per-pad zone connection lives on the `SetLocal...` methods, and some of those setters reject a plain integer because the binding expects an optional value. Where a per-pad setter refuses, set the value on the zone, and read back what was saved.

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
