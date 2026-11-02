# Classification

Companion reference for the [project-tracking](../SKILL.md) skill. Load it when adding a label, auditing the label list, or deciding whether a label earns its place.

---

### Governance replaces validation

Labels are free text in most trackers, with no administration screen and no validation, so near-duplicates get created silently and nobody notices until a filter quietly returns the wrong set. Governance is what replaces the validation the tool does not provide.

The rule has four parts.

A documented list, extended deliberately. Every label that may be used is written down in one documented place, and adding a label is a deliberate act that puts it on that list rather than someone typing a new string into an item. The list is meant to grow. What matters is that it grows by decision rather than by accident, because the failure mode is not a list that is too short, it is two spellings of one idea splitting every filter in half.

Two families. One family says which part of the system the work touches, which is what makes "what is outstanding in this area" answerable. The other says what nature of work it is, which is what makes "how much of the backlog is security work" answerable. Requiring at least one from the first family and at most one from the second keeps both questions answerable without turning labels into a second description.

A size of roughly ten to twenty labels in total. Below that the labels are too coarse to filter anything. Above it people stop reading the list, start guessing, and the near-duplicates begin.

A named owner and a periodic audit. One person decides what enters the list, and someone compares the labels actually in use against the documented list on a regular cadence. Without both, the list is a document about the past.

Four kinds of label do not earn their place:

- A label duplicating the kind of work, such as bug or spike. A field already answers that, and two answers to one question drift apart.
- A synonym of an existing label, such as documentation beside docs, or refactor beside tech-debt. Two spellings split every filter in half without telling anyone.
- A label so broad it filters nothing, such as backend or integration. If it matches most of the backlog it carries no information.
- A label naming a file format rather than a kind of work, or duplicating a field that already answers more precisely. Either one spreads across unrelated items, because nobody can tell from the name when it applies.
