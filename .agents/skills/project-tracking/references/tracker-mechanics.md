# Tracker Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside a
named tracker and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how
seven trackers express them, so a reader on any of those tools can act without translating first. A tracker not
listed here is covered by the four porting questions at the end of the skill.

---

### Concept Map

| Concept | Jira | YouTrack | Linear | Azure DevOps Boards | GitHub | GitLab | Trello |
|---|---|---|---|---|---|---|---|
| Unit of work | Issue | Issue | Issue | Work item | Issue | Work item | Card |
| Kind carried by | Issue type | Type custom field | No type field, use a label | Work item type, fixed by the process | Issue type, organisation level | Work item type | No equivalent |
| Grouping under an outcome | Epic issue type | Issue typed Epic | Project, initiative above it | Epic and Feature backlog levels | Sub-issues, milestone, project | Epic, paid tier | Board and list only |
| Parenting | Fixed by hierarchy level | Subtask link, any type parents any | Sub-issue, no stated limit | Child-Parent link, one parent | Sub-issue, eight levels deep | Seven levels deep | None native |
| Free-text classification | Labels, any string | Tags, private by default | Labels, created in settings | Tags | Labels, repository scoped | Labels, three scopes | Labels, board scoped |
| Governed classification | Components | Subsystem custom field | Label group, single select | Area Path | Organisation issue fields | Custom fields, group level | Custom fields power-up |
| Lifecycle state | Status | State custom field | Status | State | Open or closed, plus a project Status field | Open or closed, plus Status on paid tiers | Which list, plus a complete flag |
| Closure decided by | Resolution field | Resolved property on the state | Status category | Category state | State reason | Status category | Complete flag and archive flag |
| Grouping layer for statuses | Status category, three values | None | Status category, six values | Category state, five values | None | Status category, paid tiers | None |
| Backlog ordering | Rank, hidden total order | None, manual sort in a cell | Manual ordering, workspace wide | Stack Rank or Backlog Priority | Stored position on the project item | Relative order value | Numeric position in a list |
| Blocked marker | Flagged field, value Impediment | None, shared tag is nearest | Blocked by relation | Dedicated Blocked field | Blocked by relationship | Blocks link type | None |
| Relationships | Duplicates, blocks, relates to, is cloned by | Duplicate, Depend, Relates, Subtask | Duplicate, blocking, related | Parent, related, duplicate, no blocks type | Parent, blocked by, duplicate by comment | Blocks, relates to, duplicate is a status | Attachment link, no type |
| Release grouping | Fix version | Fix versions, multi-valued | Project milestone is nearest | Iteration Path | Release built on a tag | Release on a tag, reached via milestone | None |
| Code link | Key in branch, commit and title | Issue id in a commit message | Identifier in branch or title | AB and the work item number | Closing keyword and the number | Closing keyword and the number | Manual, through a power-up |

---

### Jira

The unit is an issue and its kind is the issue type. Each type sits at a numbered hierarchy level, so the type
decides what may parent what: Epic is a distinct type at level one and Subtask a distinct type at level minus one.
Grouping under an outcome is the Epic type. Free-text classification is Labels, which are global, accept any string
and have no administration screen, so a documented list is the only validation that exists. Governed classification
is Components, which are project-scoped, administrator-created and available in company-managed projects only. The
state a person reads is Status, and every status maps to one of exactly three status categories, To Do, In Progress
and Done. Closure is the separate Resolution field, and an item counts as open whenever Resolution is empty
whatever the status says. Backlog order is Rank, a hidden total-ordering field maintained by drag and drop in the
backlog view, which is not the Priority field. Blocking is the Flagged field, whose single value is Impediment, and
it colours the card without moving it. Link types include duplicates, blocks and is blocked by, relates to, and is
cloned by. Releases are fix versions, which are project-scoped. Branch names, commit messages and pull-request
titles each carry the uppercase item key, and different panels read different artefacts, so a squash merge that
rewrites the commit message can break the deployment link.

Two searches are worth running on a regular cadence, written here against an invented project key ABC. The first
lists items with no parent, which should return only work that is genuinely standalone rather than work nobody has
sorted yet. The second lists items sitting in a done status with no resolution recorded, which is the state
described above and should always return nothing at all.

```
project = ABC AND parent IS EMPTY ORDER BY created DESC
```

```
project = ABC AND statusCategory = Done AND resolution IS EMPTY ORDER BY updated DESC
```

The trap: Resolution is a second closure field that none of the other tools here has, so an item transitioned to
Done without it reads as finished on the board and open to every query.

---

### YouTrack

There is no separate epic entity and no separate subtask entity. An epic is an ordinary issue whose Type custom
field carries the value Epic. Containment is the Subtask link type, whose two directions are named parent for and
subtask of, and any issue can parent any issue with no type restriction, the vendor stating that the hierarchy has
no depth limit and no structure restrictions. An issue has exactly one parent. The hierarchy renders as a tree in
the issues list, in the agile board backlog Tree view and in the Gantt chart, though the board itself shows three
levels at a time, and story points sum per epic swimlane. Free-text classification is Tags, and a tag is visible
only to its owner by default, with three separate sharing settings for view, use and edit. Governed classification
is the Subsystem custom field, which is single-valued as shipped and can be made required. The state is a custom
field whose values each carry a Resolved property, and that property alone decides whether an issue is resolved, so
there is no separate closure field and no status category layer. One state-type field per project is the vendor's
strong advice. There is no documented total-ordering field, board cards are sorted manually within a cell, and
manual sorting is disabled when the board filter carries its own sort. There is no flag equivalent, and the nearest
mechanism is a shared tag. Default link types are Depend, Duplicate, Relates and Subtask. Release grouping is the
Fix versions default custom field, which names the version the issue is to be resolved in, is configured to store
several values at once and starts with an empty set, and it has a sibling called Affected versions naming the
versions a defect shows up in. Code linking runs off the issue id in a commit message: writing the id after a hash
or a caret creates the link, anything following the id on the same line is read as a command so the same commit can
also resolve the issue, an integration setting allows commits to be linked instead by an issue id appearing in the
branch name, and a command placed in a pull-request title or description is ignored rather than applied. A tag can
be converted to a Subsystem value in bulk from the command dialog, setting the subsystem and removing the tag in
one line. An official remote Model Context Protocol server, which is the interface an agent would drive this tool
through, is available from release 2025.3 onward at the instance address.

The trap: containment is a link rather than a typed level, so nothing stops an issue parenting an epic and the tool
will not object.

---

### Linear

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

---

### Azure DevOps Boards

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

---

### GitHub Issues and Projects

The unit is an issue, and issue types exist as an organisation-level feature, shipping with task, bug and feature
as defaults and allowing up to twenty-five types per organisation. Work groups under an outcome in three ways, none
of them called an epic: sub-issues form the hierarchy, milestones group issues and pull requests behind a due date,
and Projects aggregate items across repositories. Sub-issues nest up to eight levels deep with up to one hundred
sub-issues per parent. Free-text classification is labels, which are repository-scoped, need write access to create
and have a labels page per repository, so they are local rather than governed. The governed classification is
organisation issue fields, created and deleted only by organisation administrators in single-select, text, number
and date forms, and a single-select field there is the closest equivalent to a component. The state on the issue
itself has exactly two values, open and closed, while a Project adds a Status field that is an ordinary
single-select field. Closure is decided by a separate state reason carrying completed, not planned, duplicate,
reopened or nothing at all. There is no status category concept, and a board column is simply a value of whichever
single-select or iteration field the board is grouped by. Backlog order is a stored position on the project item
rather than an artefact of a sort, and while a board is sorted, manual reordering within a column is unavailable.
Blocking is a first-class dependency, marked as blocked by or blocking, which puts a blocked icon on the board.
Relationships are parent and sub-issue, blocked by and blocking, duplicate marked by a comment naming the other
item, and linked pull requests. A branch can be created from the issue, and a pull request or commit links back
through a closing keyword such as closes or fixes followed by the item number, with cross-repository references
written as owner, repository and number. Closing keywords take effect only against the default branch. Releases are
built on a version-control tag and are a separate thing from milestones.

The trap: a keyword in a commit message closes the issue but does not list the pull request as linked, while the
same keyword in the pull-request description does both, so the two placements are not interchangeable.

---

### GitLab Issues

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

The trap: several mechanics the rules above depend on, namely the status field, scoped labels, custom fields and
blocking, are paid-tier features, so a free-tier project has the open and closed state and ordinary labels and
nothing else.

---

### Trello

The unit is a card and there is no issue-type equivalent, the documented card types being structural objects such
as template, mirror and link cards rather than a classification anyone picks. The hierarchy is workspace, board,
list, card, with Collections grouping boards on the paid tier, so nothing groups cards under an outcome below board
level. There is no native card-to-card parent and child relationship: the documented approach to dependencies is a
checklist plus an automation rule, and converting a checklist item to a card records no link back to its source.
Classification is labels, which are board-scoped, coloured, optionally named and applied several at a time. There
is no administrator-owned classification, the nearest being the custom fields power-up, which is board-scoped and
capped at fifty fields per board. The state a person reads is which list the card sits in, and list names are free,
alongside a two-valued native card status of complete or not complete that the board filter can search on. Closure
has two independent mechanisms, marking a card complete and archiving it, which are separate flags in the interface
and separate properties in the interface behind it. Nothing between a list and the board groups cards natively.
Card order within a list is a stored numeric position. There is no native blocked marker. Cards can be linked to
one another by attachment, and that link carries no type. Branch, commit and pull-request linking is manual through
a power-up, and no commit-message syntax exists.

The trap: neither closure mechanism distinguishes delivered from abandoned, so that distinction has to be carried
entirely by which list a card finishes in.
