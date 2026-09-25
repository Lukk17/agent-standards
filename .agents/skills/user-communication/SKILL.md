---
name: user-communication
description: 'How any agent writes a reply to the user and asks the user a question: every point self-contained for a reader with no memory of earlier messages, domain words explained for a newcomer, the user''s own questions answered first, numbers only on points that need the user''s decision, one result reported once, short enough to read in one pass. Use when you ask "how should I answer the user", "ask the user a question", "write the reply", "report the result", or "number these questions". Not for README, docs or other file prose, use `markdown-writer`.'
---

# User Communication

How to write every reply to the user and every question put to the user. Write for a reader who has no memory of
this conversation, has not read anything you read, has no file open, and is new to the topic.

| Task | Open |
|---|---|
| Wording a reply: newcomer explanations, length, and the banned machine-writing marks | [references/writing-style.md](references/writing-style.md) |
| Asking the user something: the shape of a decision point, numbering, and a worked example | [references/question-points.md](references/question-points.md) |
| Reporting a result and ending the reply with the status block | [references/status-block.md](references/status-block.md) |

---

### When to activate

- Writing any reply to the user in a chat session
- Asking the user a question or putting a decision in front of them
- Reporting a finished result, a finding, or a blocker
- Answering a prompt that contains one or more questions from the user

---

### When not to activate

- Writing a README, a docs page or any other markdown file a person reads later, use `markdown-writer`
- Writing a work item description or acceptance criteria, use `project-tracking`
- Recording a design decision, use `architecture-decision-records`
- Writing a report that one agent hands to another agent rather than to the user

---

### Rules

1. Answer every question in the user's prompt, and every point the user raises, before starting, continuing, or
   reporting any work. Number the user's questions yourself when they are not numbered.
2. When you ask the user something, stop, and do not proceed on an assumed answer.
3. Explain every domain word, tool name, and concept in plain words on first use. Never use a name invented during
   the conversation, an acronym, or a file label. Give full file paths.
4. Make every point answerable cold: restate the context it needs, and never point the user at a file, a ticket, or
   an earlier message instead of explaining.
5. Shape a decision point as the question in one line, the problem in plain words, then the recommendation with its
   reason and its minus on a line of its own. The shape and a worked example are in
   [references/question-points.md](references/question-points.md).
6. Number only points that ask the user something, in one continuous sequence per conversation, with subpoints as
   13.1 and never letters.
7. Keep a reply readable in one pass: paragraphs of at most three lines, three or more facts as a list of full
   sentences, code only where the problem needs it.
8. Report each finished result once, when the work is done. While work runs, write at most three lines and the
   status block.
9. End every reply with the status block and nothing after it, copied from the template in
   [references/status-block.md](references/status-block.md) exactly as shown: no heading, no bullets, no numbered
   list, plain lines only, keeping every blank line. `Running:`, the last two finished as `~~DONE: ...~~`, the bold
   `NOW:` line, `Next:` and `Then:`, and `Waiting on:` last. When several tasks run, list each name in backticks on
   the `Running:` line, separated by commas.
10. State no cause you have not checked. Once the user says fix it, investigate first.
11. Use no em dash, no en dash, no clause-joining semicolon, no italic, and no bold except the `NOW:` line. The full
    list of machine-writing tells is in [references/writing-style.md](references/writing-style.md).

---

### Related skills

- `markdown-writer` owns prose written into files rather than into a reply
- `agentic-engineering` owns when to stop and ask, and how to number open questions during planned work
- `project-tracking` owns work item text and acceptance criteria

---

### Checklist

- [ ] Every question in the user's prompt answered before any work or report
- [ ] Every domain word, tool name, and concept explained in plain words on first use
- [ ] No invented names, acronyms, or file labels, full paths only
- [ ] Every decision point is question, problem, then recommendation with its minus
- [ ] Numbers only on points that ask something, each numbered heading ends in a question
- [ ] One continuous sequence, no renumbering, subpoints as 13.1
- [ ] Every reply ends with the status block: running, two crossed-out DONE lines, bold NOW, Next then Then, and
  waiting on last
- [ ] Blank lines separate the five groups of the status block, with no heading, bullet or list marker on any line
- [ ] Each result reported once, readable in one pass, paragraphs at most three lines
- [ ] No em dash, en dash, clause-joining semicolon, or italic, and no bold except the NOW line
