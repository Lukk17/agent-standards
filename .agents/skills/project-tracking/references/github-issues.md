# GitHub Issues and Projects Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside GitHub Issues and Projects and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how GitHub Issues and Projects expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | GitHub Issues and Projects |
|---|---|
| Unit of work | Issue |
| Kind carried by | Issue type, organisation level |
| Grouping under an outcome | Sub-issues, milestone, project |
| Parenting | Sub-issue, eight levels deep |
| Free-text classification | Labels, repository scoped |
| Governed classification | Organisation issue fields |
| Lifecycle state | Open or closed, plus a project Status field |
| Closure decided by | State reason |
| Grouping layer for statuses | None |
| Backlog ordering | Stored position on the project item |
| Blocked marker | Blocked by relationship |
| Relationships | Parent, blocked by, duplicate by comment |
| Release grouping | Release built on a tag |
| Code link | Closing keyword and the number |

---

### Features That Carry the Rules

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
