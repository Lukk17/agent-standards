# E2E Runbooks Checklist

Run it before calling a spec, a run or a sweep done.

- [ ] One capability per spec, one spec per file, seven sections in order.
- [ ] Every assertion is observable through the API or the persisted state, never a log line.
- [ ] The `{N}` prefix matches the test's real setup cost class.
- [ ] Every fixture carries canary content the model could not have memorised.
- [ ] The Reset section wipes everything the Run section writes.
- [ ] The Concurrency section names every resource the test mutates.
- [ ] The spec and template were not edited to make a run pass.
- [ ] Every run record carries Start, End, Duration, token counts, a Result summary, and a Verdict.
- [ ] A sweep used one timestamp across every run record.
- [ ] The parallel cap was confirmed with the user before fan-out.
