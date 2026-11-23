# Azure DevOps Boards Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside Azure DevOps Boards and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how Azure DevOps Boards expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | Azure DevOps Boards |
|---|---|
| Unit of work | Work item |
| Kind carried by | Work item type, fixed by the process |
| Grouping under an outcome | Epic and Feature backlog levels |
| Parenting | Child-Parent link, one parent |
| Free-text classification | Tags |
| Governed classification | Area Path |
| Lifecycle state | State |
| Closure decided by | Category state |
| Grouping layer for statuses | Category state, five values |
| Backlog ordering | Stack Rank or Backlog Priority |
| Blocked marker | Dedicated Blocked field |
| Relationships | Parent, related, duplicate, no blocks type |
| Release grouping | Iteration Path |
| Code link | AB and the work item number |

---

### Features That Carry the Rules

The unit is a work item and its kind is the work item type, and which types exist is fixed by the process chosen at
project creation, one of Basic, Agile, Scrum and Capability Maturity Model Integration, whose type sets differ:
Basic has only Epic, Issue and Task where Agile adds Feature, User Story and Bug. Grouping is Epic and Feature, the
two portfolio backlog levels above the requirement level. Parenting is the Child-Parent link, one parent per item
and no circular references, and the type restricts nothing about what may parent what, with no maximum nesting
depth documented. A same-type hierarchy such as a story under a story is accepted by the link but then shows only
the leaf node on boards, which is why the guidance is to link across different types. Classification is two things,
Tags as the free-text form, and Area Path and Iteration Path as the governed form, both defined at project level by
an administrator rather than typed freely, the first grouping work by product or team and the second by sprint.
Area Path then does three jobs at once, which most other trackers have no equivalent for: it carries what
Components carries in Jira, it decides which team's backlog an item appears on because a team is configured with
the area paths it owns, and view and edit permissions are granted per area path node. The lifecycle field is State
and each process ships its own set. Every state maps to one of five category states, Proposed, In Progress,
Resolved, Completed and Removed, and closure is derived from that category rather than from a separate field, so
there is no equivalent of Jira's Resolution to leave empty. An item in Removed is hidden from every backlog and
board. Reason sits beside State, is filled automatically, and is not the closure decision. Backlog order is a
hidden total ordering, called Backlog Priority under Scrum and Stack Rank under the others, and a bulk modify
destroys the relative order. Blocked is a dedicated field rather than a link type or a tag convention, and there is
no blocks link type at all. Code linking runs on the work item number, and for a repository hosted on GitHub the
reference is the letters AB, a hash and the number, so AB#125 names work item 125. A state name, or a keyword such
as fixes, placed in front of that reference also transitions the item, but only when the pull request merges into
the default branch.

The trap: the work item types and the workflow states both come from the process chosen when the project was
created, and that base process cannot be changed afterwards, so what looks like a configurable vocabulary is fixed
at creation and changing it means a new project and a bulk move of every item.
