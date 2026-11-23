# TDD Workflow Checklist

Run it before calling the work done.

- [ ] A user journey was stated before the first test was written.
- [ ] The test was executed and produced a valid RED for the intended reason.
- [ ] No production code changed before that RED was confirmed.
- [ ] The implementation is the minimum that turns the test green.
- [ ] Refactoring happened only under green, with the suite rerun after each step.
- [ ] Around 90 percent line coverage of real logic, branch coverage 70 to 80 percent, enforced in CI.
- [ ] The coverage config uses the key the tool actually reads.
- [ ] Test names describe behaviour and condition, in one convention across the codebase.
- [ ] Every test builds its own data and passes in any order.
- [ ] No comment in a test but the bare Given, When and Then markers.
- [ ] No test class or file past about 300 lines, and no `*BranchTest` beside its behaviour class.
- [ ] Assertions target observable behaviour, and none was weakened to get green.
- [ ] Mocks sit at interfaces the project owns, and integration tests use Testcontainers.
- [ ] The full suite ran, not just the one test that was being fixed.
- [ ] No test is skipped or disabled without a tracked quarantine entry.
