#!/usr/bin/env python3
"""Appends the preflight reminder to the prompt GitHub Copilot sends the model.

Copilot's userPromptTransformed event hands the hook a JSON payload on stdin
whose `transformedPrompt` field is the model-facing content, and replaces that
content with `modifiedTransformedPrompt` from the JSON the hook prints. See
https://docs.github.com/en/copilot/reference/hooks-reference.

It lives under .agents/hooks/copilot/ because the OpenCode and Kilo Code
runner discovers only a script directly inside a hook folder of
.agents/hooks/, so this Copilot-only helper never costs their tool calls an
interpreter start.

Copilot also fires the event for the prompt that opens a subagent's session,
and the payload names no agent. The CLI puts the subagentStart text at the
start of that prompt, so a prompt opening with it gets no reminder: the
reminder tells its reader to delegate, and a subagent told that turns its own
task away.

Every failure path prints nothing and exits 0, which Copilot reads as no
output and passes the prompt through unchanged.

REMINDER is also the main-thread reminder the OpenCode and Kilo Code plugin,
.agents/plugin/hooks.js, reads from this file and adds to every prompt of a
root session. The plugin reads it as written, a parenthesised run of plain
double-quoted literals whose only escape is the newline, so keep that shape.
tools/tests/test_reminder_plugin.py fails when the two readings differ.

The reminder ends with the status block section 3 of
.agents/instructions/reply-rules.md defines, and
tools/tests/test_status_template.py holds the two equal.
"""

import json
import sys
from typing import Optional

REMINDER = (
    "Before code work, name the skills and subagents that own this task and invoke them, "
    "or say none apply and why, in one line. "
    "End every reply to the user with this block, exactly as shown: no heading, no bullets, no numbered "
    "list, plain lines only, keeping every blank line:\n"
    "\n"
    "Running: `running task name` (or: nothing)\n"
    "\n"
    "~~DONE: older finished task~~\n"
    "~~DONE: most recent finished task~~\n"
    "\n"
    "NOW: what is being done right now\n"
    "\n"
    "Next: the next task\n"
    "Then: the task after that\n"
    "\n"
    "Waiting on: what you wait for (or: nothing)\n"
    "\n"
    "When several tasks run, list each name in backticks on the Running line, separated by commas."
)


SUBAGENT_OPENING = "PREFLIGHT for a subagent:"


def with_reminder(transformed_prompt: str) -> Optional[str]:
    if transformed_prompt.rstrip().endswith(REMINDER):
        return None

    return f"{transformed_prompt}\n{REMINDER}"


def opens_a_subagent(prompt: object) -> bool:
    return isinstance(prompt, str) and prompt.startswith(SUBAGENT_OPENING)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        transformed_prompt = payload["transformedPrompt"]
        if not isinstance(transformed_prompt, str) or opens_a_subagent(payload.get("prompt")):
            return

        modified = with_reminder(transformed_prompt)
        if modified is None:
            return

        output = json.dumps({"modifiedTransformedPrompt": modified})
        sys.stdout.write(output)
        sys.stdout.flush()
    except Exception:
        return


if __name__ == "__main__":
    main()
    sys.exit(0)
