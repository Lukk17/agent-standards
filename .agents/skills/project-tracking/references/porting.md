# Porting to Any Tracker

Companion reference for the [project-tracking](../SKILL.md) skill. Load it when the project uses a tracker with no file of its own in this folder, or when work moves from one tracker to another.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. Seven trackers each have a file recording how they express the rules, so a reader on any of those tools can act without translating first: [jira.md](jira.md), [youtrack.md](youtrack.md), [linear.md](linear.md), [azure-devops.md](azure-devops.md), [github-issues.md](github-issues.md), [gitlab-issues.md](gitlab-issues.md) and [trello.md](trello.md). Each one opens with the same concept map, so two trackers compare row by row. A tracker not listed there is covered by the five porting questions below.

---

### Five Questions for Any Tracker

Ask five questions of any candidate tracker before assuming a rule in the skill still lands. The per-tracker files answer them for seven common trackers.

How is the kind of work carried? A type field, a fixed type set, a single-select field, or nothing at all. Where there is nothing, one governed label has to carry it and be governed as strictly as a field would be.

How is an impediment marked? Some tools have a dedicated flag field, some expect a shared tag, some offer only a status. If the only mechanism is a status, the rule that blocking is not a status has to be satisfied some other way, or the age and cycle-time measurements it protects are lost.

How is closure recorded, separately from the status a person reads? Some tools carry a second field that can disagree with the status. Some derive closure from a property on the status value itself, in which case there is no second field to disagree and the delivered-versus-abandoned distinction has to live in the status name. That difference decides whether a single Done status is safe.

How is backlog order stored? A hidden total-ordering field, a manual sort within a board cell, and a numeric column all behave differently, and some of them are silently discarded when a filter carries its own sort. If the tool has no total ordering, deciding what comes next needs a different mechanism.

How does the tool group statuses for reporting? A grouping layer between a status and a board column is what makes "looks done to a person, open to every query" possible in the first place. A tool without one fails differently, and a tool with one needs the mapping checked whenever a status is added.

---

### Portability Rules

Three portability rules fall out of comparing real trackers. Where closure is derived from the status value rather than recorded separately, the difference between delivered and abandoned has to live in the status name, which means two terminal statuses rather than one. Where containment is a link rather than a typed level, nothing stops an inverted or nonsensical hierarchy, so the discipline has to come from the team rather than from the tool. And where classification is free text with no administration screen, the documented list is the only validation that exists.

---

### Item Ids Across a Migration

One more thing to check rather than assume: whether an item id survives a migration at all. An item whose only identity is its id is fragile across a tool change. Two mitigations are cheap. Carry the original id inside the item body or in a dedicated field, and keep a committed id-to-summary mapping file in the repository, so a code marker naming an item stays resolvable even if the id it names does not survive.
