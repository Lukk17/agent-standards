# Status Block

How to report results and how to end every reply. Load this file when a reply reports finished work, reports work
still running, or needs its closing status block.

---

### Say each result once

Report each finished result exactly once, when the work is done. While work is still running, the reply is at most
three lines saying what is running, followed by the status block, with no partial results and no interim summaries.
When subagents run, summarise once when all of them have finished, without narrating their progress or repeating
findings early.

---

### End every reply with the status block

Every reply ends with the status block, and nothing comes after it. It carries both what the agent waits on and the
names of the tasks still running, so no separate closing line exists for either.

Copy this template exactly as shown, with the crossed Done lines, every code block, the one dash rule,
and every blank line in place.

---------------------

Status

~~Done: older finished task~~
~~Done: most recent finished task~~

```text
Running: name of each running task, with progress like 3 of 10 todos done
```

```text
NOW: what is being done right now, one line
```

```text
Next: the next task
Then: the task after that
```

```text
Waiting on: what the agent waits for
```

```text
State: WAITING FOR YOU
```

The Done group is plain text, no code fence, each Done line wrapped in double tilde strikethrough,
older task first. Every other item sits in its own code block. Blank lines
separate the code blocks from each other so they parse as separate blocks. The Running block is omitted when
nothing runs. When several tasks run, list each name on the Running line separated by commas, no backticks.

Done lists the last two finished tasks, older first, as crossed plain text lines.

State is exactly one of three values in capitals: WAITING FOR YOU, WORKING, DONE.

State is WAITING FOR YOU only when work is blocked on the user answer. State is WORKING while any task or subagent
runs, even when a question waits that does not block. State is DONE when finished and idle.

Nothing comes after the State block. The State block is the last block of every reply.

No other markdown anywhere in the block. No bold, no italics, no other markdown in the block,
except the double-tilde strikethrough on the Done lines. The 21-hyphen rule
sits above the word Status and nowhere else. No dash lines anywhere else.

A filled example:

---------------------

Status

~~Done: Fix code review findings~~
~~Done: First Docker test run, 2 checks failed~~

```text
Running: Run containerised sandbox suite, 7 of 10 todos done
```

```text
NOW: fix the two Docker checks and rerun the suite
```

```text
Next: build the live test pipeline once you answer 3.6
Then: build the research skill once you answer 13.1
```

```text
Waiting on: your answers to 3.6, 10.1, 11.1, 12.1 and 13.1
```

```text
State: WORKING
```
