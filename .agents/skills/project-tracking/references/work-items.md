# Work Items

Contents:

- [Kinds of Work](#kinds-of-work)
- [Epics Are Outcomes, Never Categories](#epics-are-outcomes-never-categories)
- [Size and Splitting](#size-and-splitting)
- [Acceptance Criteria](#acceptance-criteria)

Companion reference for the [project-tracking](../SKILL.md) skill. Load it when choosing the kind of an item, shaping an epic, splitting an item, or writing its acceptance criteria. The skill states each rule in one line, and this file holds the reasoning and the failure modes behind it. Where a rule needs a mechanism the tool has to provide, the rule says what that mechanism must do and leaves the tool free to provide it however it does.

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

Every item except an epic has a parent epic, and the parent is set when the item is created, not sorted out later.
A Subtask takes its item as parent instead. When no existing epic fits, ask which outcome the work belongs to before
creating the item. Never create it without a parent, and never park it under a catch-all epic to fill the field. The
same rule makes a search for parentless items, epics aside, a hygiene check that should always return nothing.

---

### Size and Splitting

An item is the right size when one person can finish it comfortably inside the team's normal cycle and it can be
verified on its own. Size is the lever behind every flow measure in [flow-and-links.md](flow-and-links.md#ordering-flow-and-bounded-work-in-progress). Small items finish sooner, they
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
