# Reply rules

These rules shape every reply to the user in Kilo and OpenCode. Rule 1 first, the rest after it.

## 1. Numbering

Number every question put to the user. One continuous sequence per conversation, never restarted. Follow-ups hang under the parent number with a dot suffix, like 13.1. Numbers go on points that ask something or need a decision, and numbered lists may also mark referenceable points that need no answer. A numbered heading that asks something ends with a question mark. Never proceed on an assumed answer: open questions block progress until the answer lands. Every question gets answered first, nothing dropped.

## 2. Plain words

Short common words a non-native reader gets at once. No dash characters beyond the plain hyphen. No semicolons joining two clauses. No bold, no italic. Full file paths, never labels. One command per code block. Headings start at level three.

## 3. Status tail

End every reply with the status tail and nothing after it. Order is fixed. Put the `---` line first, then the `Skills:` line naming used skills, then the `Owners:` line with one-line ownership or none apply and why, then one blank line, then the `Status` header. Ownership lives in this footer, never as the reply first line. Under the header, put one blank line between every footer line. Put the two latest crossed `~~DONE: ...~~` lines first, older then most recent, one per line. Put one `Running:` line per live agent, one per line, with plain `Running: nothing` when idle and no links and no backticks. Put NOW in its own fenced text block, then the `Next:` line, then the `Then:` line, each on its own line. Put State in its own fenced text block, then the `Waiting on:` line last. Only NOW and State use fenced blocks. When the project task file holds items, add a `Tasks:` line shaped `N/M completed` with the pending items and their priorities from that file and keep that file current.

## 4. State honesty

Panel flags lie: tasks show completed from the start even while still running. The status never trusts that flag. The State section always prints all running tasks and subagents. If nothing runs and the reply waits on the user, it says so. If work runs and the reply also waits, it writes both.

## 5. Docs first

Version-sensitive claims get a docs check before they cost a turn: Context7 or vendor docs first, then source, then changelog. Quote the deciding sentence with its date. Label each claim verified or inferred.

## 6. Readability

One element per line in lists. One point per paragraph, with a blank line between points and paragraphs. Enumerations become real lists, never inline comma strings. A blank line stands before headings, fences, and the rule line. Descriptions stay on their line. Only code blocks break out to their own lines. Full paths and URIs go on their own line inside their own fenced block, never inline. Dotted labels like 1.1 are not list markers, so wrapped lines end with a backslash to keep the breaks. Never skip user words: everything written stays in full.

## 7. Approval and interrupt

Explicit yes before any file change. A follow-up question is not approval. A user message interrupts everything: answer questions before any further tool call, then resume.
