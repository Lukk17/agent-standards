# Flow, Closure and Links

Contents:

- [Status and Closure](#status-and-closure)
- [Ordering, Flow and Bounded Work in Progress](#ordering-flow-and-bounded-work-in-progress)
- [Links and Duplicates](#links-and-duplicates)
- [Tying an Item to the Code](#tying-an-item-to-the-code)

Companion reference for the [project-tracking](../SKILL.md) skill. Load it when designing a status set, closing or reopening an item through an API, ordering the backlog, setting a work-in-progress limit, recording a dependency, or tying an item to its branch, commit and merge request.

---

### Status and Closure

Every status has to be one somebody actually transitions an item through. Each extra one is a drag step on every
item and a board column nobody reads, so a status earns its place by being a state the team can genuinely tell apart
from its neighbours. There is no correct number, only the set the team can name without looking it up.

Delivered and deliberately abandoned are two different terminal states, and both are needed. Keeping them as two
named statuses, rather than as one status plus a field that distinguishes them, is the arrangement most likely to
survive a tracker change, because a status name travels and an auxiliary field may not. If the board maps both to
the same Done column, someone will eventually drag a cancelled card and it will be recorded as delivered. Map them
to different columns.

Blocked is not a status. A blocked item keeps the status describing what the work was actually doing, and gains a
separate marker saying it is impeded. Two things break if blocking becomes a status. The information about where the
work stood when it stalled is destroyed, so nobody knows what resuming involves. And the time an item takes becomes
meaningless, because time sitting in a Blocked column is indistinguishable from time being worked.

Closure is often decided by something other than the status a person reads. The two can disagree, and when they do
the disagreement is invisible on the board. An item sitting in Done with no closure recorded is still returned by
every open-items filter and still counts against every measure of what is outstanding: it looks finished to a person
and unfinished to every query. The reverse is worse, because a cancelled item recorded as delivered is counted as
output in every burndown chart and every report of what shipped.

The rule: every transition into a terminal status records closure in the same operation, with the value that matches
the status, and every transition back out of a terminal status clears it.

Two warnings apply specifically when writing through an application programming interface rather than clicking
through a web interface, which is the normal case for an agent. A programmatic write skips whatever screen the tool
would use to prompt for the closure value, so an agent that transitions an item and does not set closure in the same
request produces exactly the empty-field state above. And a commit-message command that resolves an item usually
moves the status only, so an item closed that way needs closure set separately.

---

### Ordering, Flow and Bounded Work in Progress

Order the backlog rather than bucketing it. An explicit ordering is a total ordering: every item sits above or below
every other item, so the question of what comes next always has exactly one answer. A five-level priority field
cannot do that, because it puts hundreds of items into five buckets and says nothing about the order within a
bucket. A priority field still earns its place as a severity signal on a Bug, answering how badly the defect hurts
rather than when it gets scheduled.

A five-level priority field drifts for a mechanical reason worth knowing: the middle value is usually the default on
the create screen. An item reading Medium is therefore indistinguishable from an item nobody ever prioritised, so
once a majority of the backlog reads Medium the field has stopped carrying information and cannot be repaired by
sorting on it.

Work in progress has to be bounded. Unbounded work in progress means everything is started, nothing is finished, and
every estimate of when anything will be done is guesswork. A fixed iteration bounds it by capacity per iteration, a
flow approach bounds it by an explicit per-stage limit written on the board, and neither bounds it by good
intentions. Set the limit from measurement rather than from opinion, and do not raise it because the team keeps
hitting it. Hitting the limit is the mechanism, not a malfunction, because it is what forces the team to finish
something before starting the next thing.

Four measures go with that, and they need nothing beyond a start date and a finish date on each item.

| Measure | What it is | What it is for |
|---|---|---|
| Work in progress | Items started and not finished | The thing the limit applies to |
| Work item age | Elapsed time since an unfinished item started | The only one you can still act on |
| Cycle time | Elapsed time from start to finish, per finished item | How long things took, after the fact |
| Throughput | Items finished per unit of time | How much gets done, counted rather than estimated |

Work item age is the one most often missing and the one worth adding first. Cycle time and throughput describe items
that already finished, which is too late to help those items, whereas an item ageing past the usual cycle time is a
warning while there is still something to do about it. Age also finds work that has quietly stalled without anyone
marking it blocked.

Throughput counts finished items without weighting them by size, which is what makes it usable without an estimation
ritual behind it. That only holds if items are kept small and similar, which is the size rule in [work-items.md](work-items.md#size-and-splitting).

---

### Links and Duplicates

Every dependency stated in prose must also exist as a link. A dependency written only in a description is invisible
to the board: it cannot show a stalled item, it cannot be filtered on, and it cannot warn anyone that starting one
item needs another finished first. Prose is for the explanation, the link is for the machine.

Four relationships cover almost everything, and every tracker expresses them in some form.

| Relationship | Use when |
|---|---|
| Duplicate | The two items describe identical work |
| Blocking | One is a genuine precondition of the other |
| Related | Partial overlap, neither contains the other |
| Parent | One item is contained by the other |

Do not use a blocking link for the case where two items touch the same file. A blocking link makes the board show a
stall, so a wrong one reports work as unstartable when it is merely inconvenient to do in parallel, and people plan
around a constraint that does not exist. Merge conflicts are a coordination problem, not a dependency.

Before closing anything as a duplicate, read both descriptions and all comments, because a matching summary is not evidence, and copy anything the survivor lacks before the close, because most trackers have no merge. The four verdicts and what to do for each are in [links-and-duplicates.md](links-and-duplicates.md).

---

### Tying an Item to the Code

The item id goes in three places, always uppercase: the branch name, the commit message, and the merge-request
title. A lowercase id usually links nothing, because id matching is commonly case-sensitive.

All three are needed because different integrations read different artefacts. A branch link reads the branch name, a
commit link reads the commit message, a merge-request link reads its title or its source branch, and a deployment
link usually reads the commit message. The consequence worth remembering: a squash merge rewrites the commit
message, so an id that lived only in the merge-request title leaves the squashed commit carrying no id at all, and
the deployment link is lost even though the merge request was linked correctly the whole time.

Branch naming, commit message format and merge strategy are not this skill's subject. They belong to the
`git-workflow` skill.
