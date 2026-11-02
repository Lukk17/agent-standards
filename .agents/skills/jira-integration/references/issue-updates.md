# Issue Updates

Contents:

- [Write the parent and labels, and only the other fields the user named](#write-the-parent-and-labels-and-only-the-other-fields-the-user-named)
- [Propose updates as you go, at the points that carry information](#propose-updates-as-you-go-at-the-points-that-carry-information)
- [Defer the content of the item to project-tracking](#defer-the-content-of-the-item-to-project-tracking)

Companion reference for the [jira-integration](../SKILL.md) skill. Load it for the pass and fail examples behind creating an issue, proposing progress updates, and deferring item content to `project-tracking`.

---

### Write the parent and labels, and only the other fields the user named

Create or modify an issue only when the user asked for it, and create each new issue only after the user approved
that one issue. A new issue always gets its parent epic and the labels the project's tracking conventions require: at
least one area label and at most one nature-of-work label, taken only from the project's own documented label list and
never invented. Every other field, meaning priority, components, sprint and assignee, is set only when the user names
it. Adding one of those on your own edits somebody else's board, and the change is invisible until a filter returns
the wrong set. Take the description template from the tracker rather than inventing one.

Pass:

```text
Asked for a bug in PROJ with that summary and description. Created it with those two fields, the parent epic and the area label from the project's list.
```

Fail:

```text
Created it with no parent, invented a "misc" label, and added priority High and the current sprint, since that seemed right.
```

---

### Propose updates as you go, at the points that carry information

Every row below is a proposal, not an action. Tell the user the transition or the comment you would make, and run it
only after they approve that one action.

| Moment in the work | What to propose for the issue |
|---|---|
| Work starts | Transition to the in-progress status |
| Branch created | Comment with the branch name |
| Tests written | Comment with what they cover |
| Pull request opened | Comment with the link, and link the issue |
| Pull request merged | Transition to the next status in the workflow |

Keep each comment short and link outward rather than pasting content. A comment that reproduces a test report goes
stale the moment the report is regenerated, and a link never does.

Pass:

```text
PR opened: <link>. 6 tests added covering the 429 path. Ready for review.
```

Fail:

```text
[400 lines of pasted test output]
```

---

### Defer the content of the item to project-tracking

What a good acceptance criterion looks like, how to size and split an item, which label taxonomy is allowed, and what
has to be true before an item closes are all owned by `project-tracking`. Read that skill before you write a
description, criteria or a closure comment, and use this skill only for getting that content into and out of Jira.

Where criteria are vague, ask before writing code rather than inventing an interpretation, and check linked issues
first so you understand the full scope of the feature.
