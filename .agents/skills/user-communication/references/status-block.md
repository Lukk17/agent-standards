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

Copy this template exactly as shown: no heading, no bullets, no numbered list, plain lines only, keeping every blank
line. It is the same template the per-prompt reminder carries.

```text
Running: `running task name` (or: nothing)

~~DONE: older finished task~~
~~DONE: most recent finished task~~

**NOW: what is being done right now**

Next: the next task
Then: the task after that

Waiting on: what you wait for (or: nothing)
```

When several tasks run, list each name in backticks on the Running line, separated by commas.

What each group carries:

- `Running:` names each subtask and background agent still running, each in backticks and exactly as the task panel
  shows it, so the user can match it there and close it, or says `nothing`.
- The last two finished tasks, one per line, each prefixed `DONE:` and crossed out with markdown strikethrough, the
  older one first.
- The current task, in bold, after the label `NOW:` in capitals. Use one `NOW:` line per task when several run at
  once. This line is the only bold a reply may carry.
- A `Next:` line names the next task and a `Then:` line names the one after it, in the order they will start.
- `Waiting on:` comes last and says what the agent waits for: the user's answer and to which numbered question, a
  named task, or `nothing`.

A filled example:

```text
Running: `Run containerised sandbox suite`

~~DONE: Fix code review findings~~
~~DONE: First Docker test run (2 checks failed)~~

**NOW: fix the two Docker checks and rerun the suite**

Next: build the live test pipeline once you answer 3.6
Then: build the research skill once you answer 13.1

Waiting on: your answers to 3.6, 10.1, 11.1, 12.1 and 13.1
```
