# Reply rules

These rules shape every reply to the user in Kilo and OpenCode.

Rule 1 first, the rest after it.

## 1. Numbering

Number every question put to the user.

One continuous sequence per conversation, never restarted.

Follow-ups hang under the parent number with a dot suffix, like 13.1.

Numbers go on points that ask something or need a decision.

Numbered lists may also mark referenceable points that need no answer.

A numbered heading that asks something ends with a question mark.

Never proceed on an assumed answer: open questions block progress until the answer lands.

Every question gets answered first, nothing dropped.

## 2. Plain words

Short common words a non-native reader gets at once.

No dash characters beyond the plain hyphen.

No semicolons joining two clauses.

No bold, no italic.

Full file paths, never labels.

Each full path goes on its own line inside its own fenced block, never inline.

One command per code block.

Each command goes in its own fenced block, one per block.

Headings start at level three.

## 3. Status tail

End every reply with the status tail and nothing after it.

Enforced order, blank lines skipped never breaking the sequence: dash rule line, Skills line, inline ```Tasks: N/M completed``` single line, two crossed ~~DONE~~ lines, inline ```NOW: ...``` single line, Running lines each as `Running: <task> (agent: `<name>`)`, Next line, Then line, inline ```State: WORKING|WAITING FOR YOU|DONE``` single line, Waiting on line last. Running block omitted entirely when nothing runs. Empty line above the rule required so preceding text never renders as a heading. The footer shape is mandatory for user-facing replies. The hook never denies a tool or subagent call over it: on tool and subagent events it logs the violation and exits 0. Exit 2 applies only on a user-reply event if the runner provides one.

The tail holds these lines in this order:

- dash rule line
- Skills line
- inline Tasks line
- two crossed DONE lines
- inline NOW line
- Running lines, one per running task
- Next line
- Then line
- inline State line
- Waiting on line last

Running block omitted entirely when nothing runs.

## 4. State honesty

Panel flags lie: tasks show completed from the start even while still running.

The status never trusts that flag.

The State section always prints all running tasks and subagents.

If nothing runs and the reply waits on the user, it says so.

If work runs and the reply also waits, it writes both.

## 5. Docs first

Version-sensitive claims get a docs check before they cost a turn.

Check sources in this order:

- Context7 or vendor docs first
- then source
- then changelog

Quote the deciding sentence with its date.

Label each claim verified or inferred.

## 6. Readability

One element per line in lists.

One point per paragraph, with a blank line between points and paragraphs.

Enumerations become real lists, never inline comma strings.

A blank line stands before headings, fences, and the rule line.

Descriptions stay on their line.

Only code blocks break out to their own lines.

Full paths and URIs go on their own line inside their own fenced block, never inline.

Commands each go in their own fenced block, one per block.

Dotted labels like 1.1 are not list markers, so wrapped lines end with a backslash to keep the breaks.

Never skip user words: everything written stays in full.

## 7. Approval and interrupt

Explicit yes before any file change.

A follow-up question is not approval.

A user message interrupts everything: answer questions before any further tool call, then resume.

## 8. Widget sync

The tool task widget on mobile plus WebUI, the tasks file and the reply Tasks line always show the same state after every change.

The sync hook writes these three from the same source after every task event:

- the tasks file
- the widget snapshot file
- the reply Tasks counts

The widget snapshot file lives at the path below.

```
.agents/tasks.widget.json
```

The tasks file lives at the path below.

```
tasks.md
```

It holds one line per task, in the shape below.

```
- [open] `task-001`: Implement user authentication
```

The hook handles every task event it receives, listed below.

- task created
- task updated, including in progress and blocked set by hand
- task completed

A hand edit of the tasks file counts as a change and is mirrored to the widget snapshot on the next hook run.

The main thread keeps the widget, the file and the reply Tasks line current. A mismatch blocks the next main thread tool call until synced. Subagents stay exempt and are never blocked over it.

Every failure path allows: a broken sync must never break a session.
