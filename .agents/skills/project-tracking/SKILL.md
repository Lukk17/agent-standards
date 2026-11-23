---
name: project-tracking
description: 'Tracker-independent rules for work items: kind, size, epics, labels, closure, acceptance criteria. Use when the user says "write this ticket" or "split this story". Not for Jira API calls, use `jira-integration`.'
metadata:
  version: "1.1.0"
---

# Project Tracking

Rules for keeping a backlog a truthful record of what is planned, what is in flight, and what actually shipped. Each rule is a property of the work rather than a feature of a tool, so it survives a change of tracker.

---

### When Not to Activate

- Calling the Jira API to read, comment on or transition an issue, use `jira-integration`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the item key, use `git-workflow`

---

### Rules

1. Pick the kind (Story, Task, Bug, Spike, Epic, Subtask) from what the work is, not how large it feels, and carry it in exactly one mechanism.
2. A Story is one "As a persona, I want goal, so that benefit" sentence, or it is a Task. A Spike names its question and its output artefact.
3. An epic names an outcome that will ship and closes on its definition of done. Activity epics and catch-all epics are forbidden: the activity becomes a label.
4. Every item except an epic gets a parent epic at creation, a Subtask its item. When no epic fits, ask which outcome the work belongs to before creating it.
5. An item is small enough for one person to finish in a normal cycle and verifiable alone. Split along observable behaviour, never along technical layers.
6. Each acceptance criterion is testable on its own and describes the result, not the recipe. One form per project: a flat checklist or Given, When, Then.
7. Use the project's description template. Without one, the description still states the outcome, the verification and what is out of scope.
8. Govern labels: one documented list in two families (area and nature of work), roughly ten to twenty, with a named owner.
9. Keep only statuses somebody actually transitions through. Delivered and abandoned are two terminal statuses on two board columns. Blocked is a marker, never a status.
10. Every transition into a terminal status records closure in the same operation, and every transition out clears it. An API write or a commit-message resolve skips the closure prompt, so set it explicitly.
11. Order the backlog totally rather than bucketing by priority. Priority stays only as a severity signal on a Bug.
12. Bound work in progress with a measured limit, never raised because the team hits it, and track work in progress, work item age, cycle time and throughput.
13. Every dependency stated in prose also exists as a link. Touching the same file is not a blocking dependency.
14. Before closing a duplicate, read both items in full and copy what the survivor lacks before the close.
15. The uppercase item id goes in the branch name, the commit message and the merge-request title, so a squash merge keeps the deployment link.

---

### Reference Files

| Task | Open |
|---|---|
| The kind table, epics, splitting an item, acceptance criteria | [work-items.md](references/work-items.md) |
| Statuses, closure, backlog order, work in progress, the link types, tying an item to code | [flow-and-links.md](references/flow-and-links.md) |
| An implementation plan with phases, rollback and risk | [implementation-plans.md](references/implementation-plans.md) |
| Adding a label or auditing the label list | [classification.md](references/classification.md) |
| Duplicate, follow-up or superseded | [links-and-duplicates.md](references/links-and-duplicates.md) |
| Acting inside the tracker a file is named for | [jira.md](references/jira.md), [youtrack.md](references/youtrack.md), [linear.md](references/linear.md), [azure-devops.md](references/azure-devops.md), [github-issues.md](references/github-issues.md), [gitlab-issues.md](references/gitlab-issues.md), [trello.md](references/trello.md) |
| Any other tracker, or a move between trackers | [porting.md](references/porting.md) |
| Whether a neighbouring skill owns the job | [scope.md](references/scope.md) |
| Before creating or closing an item | [checklist.md](references/checklist.md) |
