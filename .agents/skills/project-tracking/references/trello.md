# Trello Mechanics

Companion reference for the [project-tracking](../SKILL.md) skill. Load it only when you have to act inside Trello and need to know which feature carries which rule there.

Nothing here changes a rule. The rules live in the skill and hold whatever tool is in use. This file records how Trello expresses them, so a reader on that tool can act without translating first.

---

### Concept Map

| Concept | Trello |
|---|---|
| Unit of work | Card |
| Kind carried by | No equivalent |
| Grouping under an outcome | Board and list only |
| Parenting | None native |
| Free-text classification | Labels, board scoped |
| Governed classification | Custom fields power-up |
| Lifecycle state | Which list, plus a complete flag |
| Closure decided by | Complete flag and archive flag |
| Grouping layer for statuses | None |
| Backlog ordering | Numeric position in a list |
| Blocked marker | None |
| Relationships | Attachment link, no type |
| Release grouping | None |
| Code link | Manual, through a power-up |

---

### Features That Carry the Rules

The unit is a card and there is no issue-type equivalent, the documented card types being structural objects such
as template, mirror and link cards rather than a classification anyone picks. The hierarchy is workspace, board,
list, card, with Collections grouping boards on the paid tier, so nothing groups cards under an outcome below board
level. There is no native card-to-card parent and child relationship: the documented approach to dependencies is a
checklist plus an automation rule, and converting a checklist item to a card records no link back to its source.
Classification is labels, which are board-scoped, coloured, optionally named and applied several at a time. There
is no administrator-owned classification, the nearest being the custom fields power-up, which is board-scoped and
capped at fifty fields per board. The state a person reads is which list the card sits in, and list names are free,
alongside a two-valued native card status of complete or not complete that the board filter can search on. Closure
has two independent mechanisms, marking a card complete and archiving it, which are separate flags in the interface
and separate properties in the interface behind it. Nothing between a list and the board groups cards natively.
Card order within a list is a stored numeric position. There is no native blocked marker. Cards can be linked to
one another by attachment, and that link carries no type. Branch, commit and pull-request linking is manual through
a power-up, and no commit-message syntax exists.

The trap: neither closure mechanism distinguishes delivered from abandoned, so that distinction has to be carried
entirely by which list a card finishes in.
