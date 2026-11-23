# Jira Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside Jira and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how Jira expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | Jira |
|---|---|
| Unit of work | Issue |
| Kind carried by | Issue type |
| Grouping under an outcome | Epic issue type |
| Parenting | Fixed by hierarchy level |
| Free-text classification | Labels, any string |
| Governed classification | Components |
| Lifecycle state | Status |
| Closure decided by | Resolution field |
| Grouping layer for statuses | Status category, three values |
| Backlog ordering | Rank, hidden total order |
| Blocked marker | Flagged field, value Impediment |
| Relationships | Duplicates, blocks, relates to, is cloned by |
| Release grouping | Fix version |
| Code link | Key in branch, commit and title |

---

### Features That Carry the Rules

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
lists items other than epics with no parent, which should always return nothing at all, because every item gets
its parent when it is created. The second lists items sitting in a done status with no resolution recorded, which is
the state described above and should always return nothing at all.

```
project = ABC AND parent IS EMPTY AND issuetype != Epic ORDER BY created DESC
```

```
project = ABC AND statusCategory = Done AND resolution IS EMPTY ORDER BY updated DESC
```

The trap: Resolution is a second closure field that none of the other trackers this skill covers has, so an item transitioned to
Done without it reads as finished on the board and open to every query.
