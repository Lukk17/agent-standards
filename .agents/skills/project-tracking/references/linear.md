# Linear Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside Linear and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how Linear expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | Linear |
|---|---|
| Unit of work | Issue |
| Kind carried by | No type field, use a label |
| Grouping under an outcome | Project, initiative above it |
| Parenting | Sub-issue, no stated limit |
| Free-text classification | Labels, created in settings |
| Governed classification | Label group, single select |
| Lifecycle state | Status |
| Closure decided by | Status category |
| Grouping layer for statuses | Status category, six values |
| Backlog ordering | Manual ordering, workspace wide |
| Blocked marker | Blocked by relation |
| Relationships | Duplicate, blocking, related |
| Release grouping | Project milestone is nearest |
| Code link | Identifier in branch or title |

---

### Features That Carry the Rules

The unit is an issue, described as the fundamental unit of work, and there is no issue type field at all, so kinds
are carried by labels. Work groups under an outcome in a Project, which gathers issues around a shared outcome,
with Initiatives above projects and Milestones organising issues inside one project. Parenting is parent and
sub-issue, a sub-issue inherits the parent's team, priority and project but not its labels, and no nesting depth
limit is documented. Labels are not free text: they are created deliberately in settings at workspace or team
scope, they can be edited, merged and deleted there, and a label group permits only one of its labels on an issue
at a time, which is the nearest thing to a governed single-valued classification. The state is the Status, and
every status belongs to one of six fixed categories, Backlog, Unstarted, Started, Completed, Canceled and
Duplicate. Closure is derived from that category rather than from a separate field, and because Canceled is its own
category, delivered and abandoned are already distinct without any extra convention. Backlog order is Manual
ordering, the default for board views, and it updates the order for everyone in the workspace rather than for one
viewer. Blocking is the blocked by relation rather than a flag, alongside blocking, related and duplicate, and
marking an issue a duplicate moves it into the reserved Duplicate status. A branch carries the issue identifier
copied from the issue, and a pull request links by carrying that identifier in its title or by a magic word in a
commit message, where closing words move the issue and reference-only words link without moving it. Priority is a
five-value field from no priority to urgent, deliberately not made more granular. Release grouping has no dedicated
field and a project milestone is the nearest equivalent.

The trap: there is no issue type field, so anyone arriving expecting to pick Story or Bug has to carry that
distinction in a label and govern it accordingly.
