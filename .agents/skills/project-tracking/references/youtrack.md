# YouTrack Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside YouTrack and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how YouTrack expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | YouTrack |
|---|---|
| Unit of work | Issue |
| Kind carried by | Type custom field |
| Grouping under an outcome | Issue typed Epic |
| Parenting | Subtask link, any type parents any |
| Free-text classification | Tags, private by default |
| Governed classification | Subsystem custom field |
| Lifecycle state | State custom field |
| Closure decided by | Resolved property on the state |
| Grouping layer for statuses | None |
| Backlog ordering | None, manual sort in a cell |
| Blocked marker | None, shared tag is nearest |
| Relationships | Duplicate, Depend, Relates, Subtask |
| Release grouping | Fix versions, multi-valued |
| Code link | Issue id in a commit message |

---

### Features That Carry the Rules

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
