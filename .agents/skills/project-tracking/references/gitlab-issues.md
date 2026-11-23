# GitLab Issues Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside GitLab Issues and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how GitLab Issues expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | GitLab Issues |
|---|---|
| Unit of work | Work item |
| Kind carried by | Work item type |
| Grouping under an outcome | Epic, paid tier |
| Parenting | Seven levels deep |
| Free-text classification | Labels, three scopes |
| Governed classification | Custom fields, group level |
| Lifecycle state | Open or closed, plus Status on paid tiers |
| Closure decided by | Status category |
| Grouping layer for statuses | Status category, paid tiers |
| Backlog ordering | Relative order value |
| Blocked marker | Blocks link type |
| Relationships | Blocks, relates to, duplicate is a status |
| Release grouping | Release on a tag, reached via milestone |
| Code link | Closing keyword and the number |

---

### Features That Carry the Rules

The unit is a work item, a framework that has absorbed issues and epics into one model. The system-defined kinds
are Issue, Incident, Test Case, Requirement, Task, Objective, Key Result, Epic and Ticket, several of them
available only on the paid tiers, and further types can be configured on those tiers. Grouping under an outcome is
an Epic, which is group-level and needs a paid tier, with milestones as the other grouping layer. The hierarchy
runs epic to child epic to issue to task, nesting up to seven levels deep with a maximum of five thousand direct
children, and multi-level hierarchies need the top tier. Free-text classification is labels at project, group or
instance scope, with an administration screen for instance labels only, and scoped labels written as a key and a
value are mutually exclusive within a key on the paid tiers. The governed classification is custom fields, created
by owners or maintainers of the top-level group in single-select, multi-select, number and text forms and capped at
fifty per group. The state a person reads is open or closed, and on the paid tiers a separate Status field adds To
do, In progress, Done, Won't do and Duplicate. Closure is derived rather than recorded: statuses in the Done and
Canceled categories set the item closed and every other category keeps it open, so on the free tier closure is the
open and closed state alone. Board lists are backed by a label, and on paid tiers by an assignee, milestone,
iteration or status, with Open and Closed as two default lists that always exist. Backlog order is a stored
relative order value shared between lists and boards. Blocking is the blocks and is blocked by link type, which
puts an icon on the board card, and relates to is the third link type. Duplicates are not a link type at all:
Duplicate is a status, reached by a quick action. A branch created from an issue takes its name from a configurable
template defaulting to the item number and title, and prefixing any branch with the number and a hyphen cross-links
it. Closing keywords fire when the commit or merge request reaches the default branch. Releases are tied to a
version-control tag and reach issues only indirectly, through the milestones they are associated with.

The trap: several mechanics the rules in the skill depend on, namely the status field, scoped labels, custom fields and
blocking, are paid-tier features, so a free-tier project has the open and closed state and ordinary labels and
nothing else.
