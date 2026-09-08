# Verification is a discipline, not a result

Why a clean DRC report is not the same as a clean board, and what to do about it. The layout and export rules live
in [SKILL.md](../SKILL.md).

---

### A zero-violation DRC proves only that the enabled rules found nothing

Before trusting a "0 errors" result, open the rule severity list and confirm nothing has been quietly downgraded
from error to warning, or excluded outright. A downgraded or excluded rule can no longer report a violation at all,
so the summary line reads exactly as clean as a board with no problems in it.

Pass:

```text
Violations: 0. Severity overrides: none. Exclusions: 0.
```

Fail:

```text
Violations: 0. (silk_over_copper downgraded to Ignore, 14 exclusions saved in project)
```

---

### A check that skips what it cannot parse looks identical to a pass

Any script or plugin that walks footprints, nets, or zones reports what it examined, not only what it found wrong. A
count of footprints checked next to the count of violations is what separates a script that quietly processed 40 of
90 footprints, because the other 50 had an unexpected property, from one that checked all 90 and found them clean.

Pass:

```text
Checked 90 footprints, 214 nets, 4 zones. Violations: 0.
```

Fail:

```text
Violations: 0.
```

---

### A check nobody has seen fail is not yet a check

Before trusting an automated check to catch a defect, build or find a deliberately broken input carrying exactly
that defect and confirm the check flags it. A script run only against clean boards has never demonstrated it can
fail at all. An inverted condition, a wrong threshold, or a pattern that matches nothing will pass every board
handed to it while catching none of them, indefinitely.

---

### Design-time arithmetic has to be re-measured on the filled board

A hand or script calculation for trace width, copper area, or clearance models a clean rectangle or a straight line
between two points. A real board is not that shape once it is routed and its pours are filled: a keepout, a
clearance a hole or a part must keep from copper that is not its own net, cuts a notch out of a pour, a corner
pinches near a pad, a current path bends around an obstacle instead of running straight.

The arithmetic that sized a rail is a starting point, not the final answer. Re-measure the real as-filled geometry
once routing and zone fill are done, and check that measurement against the requirement rather than the paper
number.

---

### A threshold nobody can trace back to a reason is itself a defect

If a check enforces a number and nobody on the project can say where it came from, whether a component datasheet, a
fabricator's published manufacturing limit, a named standard, or a calculation someone can redo, the number will
eventually either pass a board that should fail or reject one that should pass. Once that happens often enough the
check gets ignored rather than fixed.

Give every enforced number a traceable origin and record that origin next to the check itself, in the rule comment
or the netclass description, not only in whoever's memory set it.
