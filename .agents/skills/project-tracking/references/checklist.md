# Project Tracking Checklists

Companion reference for the [project-tracking](../SKILL.md) skill. Run the first list before creating a work item and the second before closing one.

---

### Checklist Before Creating an Item

1. The kind matches what the work is, tested against the table in [work-items.md](work-items.md#kinds-of-work), and one mechanism carries it.
2. A Story carries its "As a, I want, so that" sentence, and a Task does not.
3. A Spike names its question and its output artefact.
4. A search for an existing item covering the same work found none.
5. The description follows whatever template the project already defines, and answers the outcome, the verification and the scope boundary either way.
6. Acceptance criteria are testable and independent, in the project's one chosen form.
7. The item is small enough to finish in a normal cycle and to verify on its own, or it is an epic with children.
8. At least one area label, and at most one nature-of-work label, both from the documented lists.
9. The item has a parent set at creation: an epic that is an outcome, or its item for a Subtask. An epic alone has none.
10. Every dependency mentioned in the text also exists as a link.

---

### Checklist Before Closing an Item

1. Every acceptance criterion is met, checked individually rather than in aggregate.
2. Every repository named by the item's area labels has its work merged, not only the one you happened to be in.
3. Closure is recorded in the same operation as the status transition, with the value matching the status.
4. No subtask is still open.
5. Nothing that blocks another item was left undone, and any link to a dependency that is gone is cleared.
6. If closing as a duplicate, the surviving item already has everything unique from this one, merged before the close rather than after.
7. The branch and the merge request carry the id, so the deployment link survives the merge.
