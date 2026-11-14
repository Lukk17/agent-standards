# Verification is a discipline, not a result

Contents:

- [A zero-violation DRC proves only that the enabled rules found nothing](#a-zero-violation-drc-proves-only-that-the-enabled-rules-found-nothing)
- [A check that skips what it cannot parse looks identical to a pass](#a-check-that-skips-what-it-cannot-parse-looks-identical-to-a-pass)
- [A check nobody has seen fail is not yet a check](#a-check-nobody-has-seen-fail-is-not-yet-a-check)
- [Design-time arithmetic has to be re-measured on the filled board](#design-time-arithmetic-has-to-be-re-measured-on-the-filled-board)
- [A threshold nobody can trace back to a reason is itself a defect](#a-threshold-nobody-can-trace-back-to-a-reason-is-itself-a-defect)
- [Making a warning impossible is the same as suppressing it](#making-a-warning-impossible-is-the-same-as-suppressing-it)
- [An acceptance step has to ask the gate's own question](#an-acceptance-step-has-to-ask-the-gates-own-question)
- [Renaming something breaks every script that matches on its old name](#renaming-something-breaks-every-script-that-matches-on-its-old-name)
- [When two checks disagree, settle it with a primary source](#when-two-checks-disagree-settle-it-with-a-primary-source)
- [Read the whole output before forming a hypothesis](#read-the-whole-output-before-forming-a-hypothesis)

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

---

### Making a warning impossible is the same as suppressing it

Hiding every reference designator to zero out the silkscreen warnings, shrinking a courtyard until an overlap stops reporting, or adding an exclusion for each finding all leave the defect on the board and remove the only thing that reported it. Fix the placement or the geometry. If a finding is genuinely unfixable, record it in the project's register of accepted deviations with the reason, and leave the check able to fire.

---

### An acceptance step has to ask the gate's own question

When an early step judges a candidate, such as a router attempt or a scripted placement, it must ask the same question the final gate asks, with the same threshold. One project's router wrapper asked whether a scripted connection could be placed at all, while the gate asked whether it landed close enough to count. Routes were accepted early and rejected several steps later. Run the gate's own check script, read-only, against the candidate, so the two standards cannot drift apart.

---

### Renaming something breaks every script that matches on its old name

After changing how anything is named, whether a footprint gaining a library prefix, a net renamed, or a reference designator changed, search the whole source tree for every script that matches on that name, not only the one the change was aimed at. A pattern anchored to the start of a bare footprint name stopped matching once the name gained a prefix, and the script that split a large solder-paste opening processed zero parts with nothing loud in its output. A count of items examined, as in the section above on checks that skip what they cannot parse, is what makes this visible.

---

### When two checks disagree, settle it with a primary source

Two checks that contradict each other cannot both be right, and the one that flags more is not the stricter one by default. Read the manufacturer's datasheet, the standard, or the assembler's own published guidance, and test each check's underlying assumption against it. Then prove the fix with a deliberately broken case, a synthetic one if the real board no longer reproduces the defect.

---

### Read the whole output before forming a hypothesis

A gate that keeps only a script's standard output, or only its last line, records a failure logged to standard error under a 0 exit code as a silent pass. The same habit misleads a person. On one project two wrong causes for a routing failure were proposed and tested while the router's own log already showed the real one. Read every tool's full output, on both streams, before deciding what it means.
