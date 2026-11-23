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

One command per code block. Anything the user must copy, such as a prompt, a command, a comment or a message, goes in one code block, never in a quote block, with each paragraph on one unbroken line. Any other code block holds only one short command or a few short lines of config, each line under about 60 characters.

Each command goes in its own fenced block, one per block.

Headings start at level three.

## 3. Status tail

End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank line:

Running: `running task name` (or: nothing)

~~DONE: older finished task~~
~~DONE: most recent finished task~~

NOW: what is being done right now

Next: the next task
Then: the task after that

Waiting on: what you wait for (or: nothing)

When several tasks run, list each name in backticks on the Running line, separated by commas.

The block is the whole tail, and nothing comes after it.

A blank line stands between the reply text and the Running line.

Name the skills and subagents that own the task in the reply text above the tail, because the tail has no line for them.

The hook never denies a tool or subagent call over the tail: on tool and subagent events it logs the violation and exits 0.

Exit 2 applies only on a user-reply event if the runner provides one.

## 4. State honesty

Panel flags lie: tasks show completed from the start even while still running.

The status never trusts that flag.

The Running line always lists all running tasks and subagents.

If nothing runs and the reply waits on the user, the Waiting on line says so.

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

A blank line stands before headings, fences, and the status tail.

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

The tool task widget on mobile plus WebUI and the tasks file always show the same state after every change.

The sync hook writes these two from the same source after every task event:

- the tasks file
- the widget snapshot file

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

The main thread keeps the widget and the file current.

The status tail has no Tasks line. A reply that still writes one in its text above the tail, as Tasks: N/M completed, must match the live list: a mismatch blocks the next main thread tool call until synced. Subagents stay exempt and are never blocked over it.

Every failure path allows: a broken sync must never break a session.
