# GitHub Operations Checklist

Run it before reporting triage, pull request, CI, release or security alert work as done.

- [ ] Every triaged issue carries a type and a priority label
- [ ] No pull request past five days without a review, and none idle seven days without a stale comment
- [ ] Every CI failure was investigated to a named cause, not just re-run
- [ ] Release notes reflect what actually merged since the last tag
- [ ] Security alerts are acknowledged and tracked, criticals raised immediately
- [ ] Every state-changing or CI-dispatching command was approved before it ran
- [ ] No literal date is hardcoded where a computed cutoff belongs
