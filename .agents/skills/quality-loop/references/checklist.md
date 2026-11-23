# Quality Loop Checklist

Run it before reporting the loop as finished.

- [ ] The wrapper ran `measure` and `summary`, and no tool ran on its own
- [ ] Nothing under `.metrics/tools/crapper`, `dryer` or `mutator` changed
- [ ] Every CRAP score over 30 was fixed or reported with its reason
- [ ] No surviving mutant is left in code the change touched, or each one left is reported
- [ ] Every duplicate pair at or above 0.82 was reviewed, and merged only when both copies are one rule
- [ ] No test was weakened, skipped or deleted
- [ ] The project's own tests pass after the last round
- [ ] The full-run scores in `.metrics/` are committed when the caller asked, staged otherwise, and the report shows them before and after
