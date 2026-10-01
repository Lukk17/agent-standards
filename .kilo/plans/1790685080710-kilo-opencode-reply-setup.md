# Kilo and OpenCode reply setup, executed

Target is latest stable: OpenCode 1.x plus Kilo CLI 7.x. OpenCode 2.x beta stays out of scope.

## Built this run

1. The reply-rules file at .agents/instructions/reply-rules.md, wired as second entry of the instructions array in opencode.json. Rule 1 in its own section is question numbering: number every question, one continuous sequence per conversation, subpoints like 13.1, never proceed on an assumed answer, numbers only on decision points, every question answered first with nothing dropped. Then plain words, the status tail template, State honesty (panel flags ignored, State always prints all running tasks and subagents, idle and run-plus-wait both stated), docs-first, readability with the backslash line-break trick, approval plus interrupt, never-skip user words.
2. Rovo atlassian block in opencode.json only, same flat shape as the context7 block. Auth stays a manual OAuth step per client.
3. New status_block_check.py in .agents/hooks, order 35, plain format only, subagent payloads exempt, fail open. It demands the Status header plus a State line holding WAITING FOR YOU, WORKING, or DONE at the next tool call. Its reason embeds the locked sentence: Fix what was flagged and anything else other hooks asked you to fix, then end with the status block.
4. No shared files touched: the two old hook reasons stay byte-identical, the user-communication skill is not deleted and not edited, stray edits outside Kilo and OpenCode files were reverted (see git log for this run).
5. Tests: tools/tests/test_status_block_check.py, 8 cases green. Full suite green, 1953 passed with 37 skipped, zero failures. CI runs the suite on every pull request and push to master.

## Remaining, user side

Live proof on the user machine, in this repo folder, once per tool: send a reply holding a long dash, ask the agent to call any tool, watch the block, send Correction lines plus the status tail, confirm the next call passes. Proof of instruction load is behavior: the tail appears unprompted.

## Known limits and parked work

No Stop event on these tools, so the status bite lands at the next tool call. When OpenCode 2.x goes stable the wiring needs a recheck and the plugin file needs a rewrite. Parked, not dropped: the narrow docs-citation hook waits on an explicit yes.
