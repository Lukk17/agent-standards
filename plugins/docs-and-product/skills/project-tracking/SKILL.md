---
name: project-tracking
description: 'Tracker-independent standards for planning and tracking work: kinds of work, sizing and splitting, epics as outcomes, labels, statuses and closure, testable acceptance criteria, links and bounded work in progress. Use when the user says "write this ticket", "split this story", "are these criteria testable" or "can we close this". Not for Jira API mechanics, use `jira-integration`.'
---

# Project Tracking

Rules for keeping a backlog a truthful record of what is planned, what is in flight, and what actually shipped. Each rule is a property of the work rather than a feature of a tool, so it survives a change of tracker.

| Task | Open |
|---|---|
| Choosing the kind, shaping an epic, splitting an item, or writing acceptance criteria | [work-items.md](references/work-items.md) |
| Designing statuses, recording closure, ordering the backlog, limiting work in progress, linking, or tying an item to code | [flow-and-links.md](references/flow-and-links.md) |
| Acting inside a named tracker, or porting these rules to a tracker not covered | [tracker-mechanics.md](references/tracker-mechanics.md) |
| Writing or reviewing the implementation plan for an item, with phases, rollback and risk | [implementation-plans.md](references/implementation-plans.md) |
| Adding a label, auditing the label list, or judging whether a label earns its place | [classification.md](references/classification.md) |
| Closing an item as a duplicate, or deciding between duplicate, follow-up and superseded | [links-and-duplicates.md](references/links-and-duplicates.md) |

---

### When to Activate

- Before creating any work item, whatever its kind
- Before editing, splitting, re-typing or re-parenting an existing item
- Before closing or cancelling an item
- Before triaging the backlog, proposing a re-organisation, or running a bulk edit
- Checking that a branch, commit or merge-request title carries the item id
- When a dependency, a duplicate or a parent relationship needs recording
- Before proposing a change to a board, a workflow, a status set or a cadence
- The user says "triage the backlog"

---

### When Not to Activate

- Calling the Jira API to read, comment on or transition an issue, use `jira-integration`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the item key, use `git-workflow`
- Recording an architectural decision rather than a unit of work, use `architecture-decision-records`
- Writing the tests that an acceptance criterion implies, use `tdd-workflow` or the language test skill
- Deciding how to hand the work to an agent once the item exists, use `agentic-engineering`

---

### Rules

1. Pick the kind (Story, Task, Bug, Spike, Epic, Subtask) from what the work is, not how large it feels, and carry it in exactly one mechanism: a type field, else a single-select field, else one governed label.
2. A Story is one "As a persona, I want goal, so that benefit" sentence, or it is a Task. A Spike names its question and its output artefact.
3. An epic names an outcome that will ship and closes on its definition of done. Activity epics (Refactoring, Bugs, Technical Debt) and catch-all epics are forbidden: the activity becomes a label.
4. Every item except an epic gets a parent epic at creation, a Subtask its item. When no epic fits, ask which outcome the work belongs to before creating it.
5. An item is small enough for one person to finish in a normal cycle and verifiable alone. Split along observable behaviour, never along technical layers.
6. Each acceptance criterion is testable on its own and describes the result, not the recipe. One form per project: a flat checklist or Given, When, Then.
7. Use the project's description template. Without one, the description still states the outcome, the verification and what is out of scope.
8. Govern labels: one documented list in two families (area and nature of work), roughly ten to twenty, with a named owner.
9. Keep only statuses somebody actually transitions through. Delivered and abandoned are two terminal statuses on two board columns. Blocked is a marker, never a status.
10. Every transition into a terminal status records closure in the same operation, and every transition out clears it. An API write or a commit-message resolve skips the closure prompt, so set it explicitly.
11. Order the backlog totally rather than bucketing by priority. Priority stays only as a severity signal on a Bug.
12. Bound work in progress with a measured limit, never raised because the team hits it, and track work in progress, work item age, cycle time and throughput.
13. Every dependency stated in prose also exists as a link (duplicate, blocking, related, parent). Touching the same file is not a blocking dependency.
14. Before closing a duplicate, read both items in full and copy what the survivor lacks before the close.
15. The uppercase item id goes in the branch name, the commit message and the merge-request title, so a squash merge keeps the deployment link.

---

### Checklist Before Creating an Item

1. The kind matches what the work is, tested against the table in [work-items.md](references/work-items.md#kinds-of-work), and one mechanism carries it.
2. A Story carries its "As a, I want, so that" sentence, and a Task does not.
3. A Spike names its question and its output artefact.
4. A search for an existing item covering the same work found none.
5. The description follows whatever template the project already defines, and answers the outcome, the verification and the scope boundary either way.
6. Acceptance criteria are testable and independent, in the project's one chosen form.
7. The item is small enough to finish in a normal cycle and to verify on its own, or it is an epic with children.
8. At least one area label, and at most one nature-of-work label, both from the documented lists.
9. The item has a parent set at creation: an epic that is an outcome, or its item for a Subtask. An epic alone has none.
10. Every dependency mentioned in the text also exists as a link.

---

### Checklist Before Closing an Item

1. Every acceptance criterion is met, checked individually rather than in aggregate.
2. Every repository named by the item's area labels has its work merged, not only the one you happened to be in.
3. Closure is recorded in the same operation as the status transition, with the value matching the status.
4. No subtask is still open.
5. Nothing that blocks another item was left undone, and any link to a dependency that is gone is cleared.
6. If closing as a duplicate, the surviving item already has everything unique from this one, merged before the close rather than after.
7. The branch and the merge request carry the id, so the deployment link survives the merge.

---

### Related Skills

- `jira-integration` owns reading, commenting on and transitioning an issue through the Jira API
- `github-ops` owns issue triage, pull request operations and releases on GitHub
- `git-workflow` owns the branch name and commit message that link a change back to an item
- `architecture-decision-records` owns recording a design decision rather than a unit of work
- `agentic-engineering` owns sizing and routing the work once the item exists
- `markdown-writer` owns the human-facing documents an item may produce
