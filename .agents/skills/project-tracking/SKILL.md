---
name: project-tracking
description: "Tracker-independent standards for planning and tracking work: choosing the kind of work, sizing and splitting an item, keeping epics as outcomes, a governed label taxonomy, statuses and how closure is recorded, testable acceptance criteria, dependency and duplicate links, bounded work in progress with the measures that go with it, and tying an item back to the code. Invoke before creating, editing, splitting, closing or triaging a work item, and before proposing any change to a backlog, board or workflow."
---

# Project Tracking

Rules for keeping a backlog a truthful record of what is planned, what is in flight, and what actually shipped.

Every rule below is stated as a property of the work rather than as a feature of a tool, so it survives a change of
tracker. Where a rule needs a mechanism the tool has to provide, the rule says what that mechanism must do and
leaves the tool free to provide it however it does. Per-tool detail lives in
[tracker-mechanics.md](references/tracker-mechanics.md), which you load only when acting inside a named tracker.

---

### When to Activate

- Before creating any work item, whatever its kind
- Before editing, splitting, re-typing or re-parenting an existing item
- Before closing or cancelling an item
- Before triaging the backlog, proposing a re-organisation, or running a bulk edit
- Before writing a branch name, a commit message or a merge-request title that has to link back to a work item
- When a dependency, a duplicate or a parent relationship needs recording
- Before proposing a change to a board, a workflow, a status set or a cadence

---

### Kinds of Work

Pick the kind from what the work is, not from how large it feels.

| Kind | What it is | The test |
|---|---|---|
| Story | A user-facing behaviour | A person outside the team could notice the difference after it ships |
| Task | Technical work with no user-facing story | Nobody outside the team sees a change, but the system is measurably different |
| Bug | A defect in behaviour that already shipped | The behaviour exists, and it is wrong |
| Spike | Research that ends in a decision | It names a question and produces a named artefact |
| Epic | A deliverable outcome made of several items | Something will have shipped when its children are done |
| Subtask | A step inside one item, with no value on its own | Shipping it alone would deliver nothing to anyone |

Trackers carry the kind differently. Some have a type field, some fix the available types when the project is
created, and some have no type concept at all. Exactly one mechanism has to carry it: a type field where one exists,
otherwise a single-select field, otherwise one label drawn from a governed list. Two mechanisms answering the same
question drift apart, and no mechanism at all means the distinction lives only in people's heads.

A Story is written as one sentence in the form "As a persona, I want goal, so that benefit". If that sentence cannot
be written without inventing a persona, the item is a Task.

A Spike carries the question it answers and the artefact it produces. Timeboxing one is a separate decision. What is
not optional is the named output, because a Spike with no named output cannot be closed on evidence and turns into
open-ended reading.

Failure modes to check for before saving:

- A Task whose summary is a user story. Re-type it to Story, or rewrite the summary as the technical change.
- A summary that starts with the word SPIKE. A field carries the kind, so the summary does not have to.
- A Spike that is really a body of work. If its research is a sequence of changes someone will implement, it is an
  epic with children, and calling it a Spike hides the size.
- A subtask created under a parent that is already closed. Either the parent is not actually done, or the subtask is
  independent work and needs its own item.

---

### Epics Are Outcomes, Never Categories

An epic names something that will have shipped. It carries a definition of done, and it gets closed when that
definition is met. A definition of done that works: every child is done, and anything discovered later becomes a
Phase 2 epic rather than being added to this one. Without a rule of that shape an epic accretes children forever and
never closes, which makes it useless for tracking progress.

Epics named after an activity do not work: Refactoring, Documentation, Bugs, Technical Debt, Maintenance. None of
them can ever be finished, so none of them can ever be closed, and an item parked under one loses the connection to
the thing it is actually changing. The activity becomes a label, and the item lives in the epic of the feature or
component being changed. A catch-all epic for work that fits nowhere fails the same way, plus one more: it hides the
fact that the work has no home, which is usually the more interesting problem.

Not every item needs an epic. A small standalone chore, a one-off bug, or a spike may legitimately have no parent,
and that is a normal state rather than a gap to fill. This only stays true if nobody invents a bucket epic to absorb
them, because a search for parentless items is a useful hygiene check exactly as long as the parentless set means
"genuinely standalone" and not "someone has not sorted these yet".

---

### Size and Splitting

An item is the right size when one person can finish it comfortably inside the team's normal cycle and it can be
verified on its own. Size is the lever behind every measure further down this file. Small items finish sooner, they
age less, and they make a count of finished items mean something.

Six properties test an item before it is accepted. It should be independent of other items, negotiable in how it is
done, valuable to somebody, estimable, small, and testable. An item failing more than one of those is usually two
items badly joined.

Split along observable behaviour, never along technical layers. A split into a backend item and a frontend item
produces two items neither of which can be shipped or verified alone, so both sit unfinished until the other lands
and neither reports anything useful about progress. Split lines that do work: one step of a workflow, one rule out
of a set of rules, one data variation, the happy path separately from the error paths, or one platform.

An item that cannot be split without leaving something unverifiable is a genuine unit, which is not a licence to
leave it large. If it is also too big to finish in a cycle, it is an epic and the split is its children.

---

### Acceptance Criteria

Note the spelling: one criterion, several criteria.

Each criterion has to be clear, testable, outcome-focused, measurable and independent. In practice that means each
one maps onto something you could execute as a test and get an unambiguous pass or fail from.

Describe the result, not the recipe. "The order list returns at most 20 rows per page" is a result. "Add a pageSize
parameter to the repository method" is a recipe, and a recipe locks in an implementation before anyone has thought
about alternatives.

If two criteria only make sense when read together, they are one criterion split badly. Rewrite them as one, or make
each stand alone. A criterion that cannot be evaluated by itself cannot be checked off by itself either.

Pick one form per project and stay with it, either a flat checklist or Given, When, Then. Do not mix the two inside
one tracker, because a reader then has to work out which convention a given item follows before they can read it,
and the two forms carry different implicit promises about how much detail is present.

An item is now routinely the whole specification handed to a coding agent, which raises the cost of vagueness. An
underspecified item does not make an agent stop and ask. It makes the agent explore widely and retry, burning time
and producing work nobody asked for. Criteria a test could evaluate are the boundary that stops that.

Use whatever description template the tracker or the project already defines, rather than one invented here. Where a
project has none, the description still has to answer three things: the outcome, how it will be verified, and what
is out of scope.

---

### Classification

Labels are free text in most trackers, with no administration screen and no validation, so near-duplicates get
created silently and nobody notices until a filter quietly returns the wrong set. Governance is what replaces the
validation the tool does not provide.

The rule has four parts.

A documented list, extended deliberately. Every label that may be used is written down in one documented place, and
adding a label is a deliberate act that puts it on that list rather than someone typing a new string into an item.
The list is meant to grow. What matters is that it grows by decision rather than by accident, because the failure
mode is not a list that is too short, it is two spellings of one idea splitting every filter in half.

Two families. One family says which part of the system the work touches, which is what makes "what is outstanding in
this area" answerable. The other says what nature of work it is, which is what makes "how much of the backlog is
security work" answerable. Requiring at least one from the first family and at most one from the second keeps both
questions answerable without turning labels into a second description.

A size of roughly ten to twenty labels in total. Below that the labels are too coarse to filter anything. Above it
people stop reading the list, start guessing, and the near-duplicates begin.

A named owner and a periodic audit. One person decides what enters the list, and someone compares the labels
actually in use against the documented list on a regular cadence. Without both, the list is a document about the
past.

Four kinds of label do not earn their place:

- A label duplicating the kind of work, such as bug or spike. A field already answers that, and two answers to one
  question drift apart.
- A synonym of an existing label, such as documentation beside docs, or refactor beside tech-debt. Two spellings
  split every filter in half without telling anyone.
- A label so broad it filters nothing, such as backend or integration. If it matches most of the backlog it carries
  no information.
- A label naming a file format rather than a kind of work, or duplicating a field that already answers more
  precisely. Either one spreads across unrelated items, because nobody can tell from the name when it applies.

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
ritual behind it. That only holds if items are kept small and similar, which is the section on size above.

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

Before closing anything as a duplicate, prove it is one. A matching summary is not evidence: the same words get used
for different work all the time, and two items can share a title while describing opposite halves of a problem. Read
both descriptions and all comments on both first.

Most trackers have no merge operation. Closing a duplicate carries nothing across, not the description text, not the
comments, not the attachments and not the links. So anything the survivor lacks has to be copied over before the
close, or it is not merged, it is buried in a closed item nobody will search.

| Verdict | What you found | What to do |
|---|---|---|
| Same title only | Similar words, different work | Rename one so the titles stop colliding, keep both, link as related if they are |
| True duplicate | Same work, described twice | Merge anything unique into the survivor, then link and close the other, recording closure as duplicate |
| Follow-up | One is done, the open one carries scope that was never delivered | Keep both, link as related, keep the open one open |
| Superseded | A later decision replaced the approach | Close as deliberately not delivered, link to the item carrying the new approach |

The survivor is normally the older item, unless the newer one is materially better described, in which case keep
that one and say so in a comment on both.

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

---

### Checklist Before Creating an Item

1. The kind matches what the work is, tested against the table above, and one mechanism carries it.
2. A Story carries its "As a, I want, so that" sentence, and a Task does not.
3. A Spike names its question and its output artefact.
4. A search for an existing item covering the same work found none.
5. The description follows whatever template the project already defines, and answers the outcome, the verification
   and the scope boundary either way.
6. Acceptance criteria are testable and independent, in the project's one chosen form.
7. The item is small enough to finish in a normal cycle and to verify on its own, or it is an epic with children.
8. At least one area label, and at most one kind label, both from the documented lists.
9. The parent epic is an outcome, or the item is deliberately standalone.
10. Every dependency mentioned in the text also exists as a link.

---

### Checklist Before Closing an Item

1. Every acceptance criterion is met, checked individually rather than in aggregate.
2. Every repository named by the item's area labels has its work merged, not only the one you happened to be in.
3. Closure is recorded in the same operation as the status transition, with the value matching the status.
4. No subtask is still open.
5. Nothing that blocks another item was left undone, and any link to a dependency that is gone is cleared.
6. If closing as a duplicate, the surviving item already has everything unique from this one, merged before the
   close rather than after.
7. The branch and the merge request carry the id, so the deployment link survives the merge.

---

### Porting This to Any Tracker

Ask five questions of any candidate tracker before assuming a rule above still lands. Per-tool answers for seven
common trackers are in [tracker-mechanics.md](references/tracker-mechanics.md).

How is the kind of work carried? A type field, a fixed type set, a single-select field, or nothing at all. Where
there is nothing, one governed label has to carry it and be governed as strictly as a field would be.

How is an impediment marked? Some tools have a dedicated flag field, some expect a shared tag, some offer only a
status. If the only mechanism is a status, the rule that blocking is not a status has to be satisfied some other
way, or the age and cycle-time measurements it protects are lost.

How is closure recorded, separately from the status a person reads? Some tools carry a second field that can
disagree with the status. Some derive closure from a property on the status value itself, in which case there is no
second field to disagree and the delivered-versus-abandoned distinction has to live in the status name. That
difference decides whether a single Done status is safe.

How is backlog order stored? A hidden total-ordering field, a manual sort within a board cell, and a numeric column
all behave differently, and some of them are silently discarded when a filter carries its own sort. If the tool has
no total ordering, deciding what comes next needs a different mechanism.

How does the tool group statuses for reporting? A grouping layer between a status and a board column is what makes
"looks done to a person, open to every query" possible in the first place. A tool without one fails differently, and
a tool with one needs the mapping checked whenever a status is added.

Three portability rules fall out of comparing real trackers. Where closure is derived from the status value rather
than recorded separately, the difference between delivered and abandoned has to live in the status name, which means
two terminal statuses rather than one. Where containment is a link rather than a typed level, nothing stops an
inverted or nonsensical hierarchy, so the discipline has to come from the team rather than from the tool. And where
classification is free text with no administration screen, the documented list is the only validation that exists.

One more thing to check rather than assume: whether an item id survives a migration at all. An item whose only
identity is its id is fragile across a tool change. Two mitigations are cheap. Carry the original id inside the item
body or in a dedicated field, and keep a committed id-to-summary mapping file in the repository, so a code marker
naming an item stays resolvable even if the id it names does not survive.
