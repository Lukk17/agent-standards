#!/usr/bin/env python3
"""Appends the preflight reminder to the prompt GitHub Copilot sends the model.

Copilot's userPromptTransformed event hands the hook a JSON payload on stdin
whose `transformedPrompt` field is the model-facing content, and replaces that
content with `modifiedTransformedPrompt` from the JSON the hook prints. See
https://docs.github.com/en/copilot/reference/hooks-reference.

It lives in a subdirectory of .agents/hooks/ because the OpenCode and Kilo Code
runner discovers only the files sitting directly in that directory, so this
Copilot-only helper never costs their tool calls an interpreter start.

Copilot also fires the event for the prompt that opens a subagent's session,
and the payload names no agent. The CLI puts the subagentStart text at the
start of that prompt, so a prompt opening with it gets no reminder: the
reminder tells its reader to delegate, and a subagent told that turns its own
task away.

Every failure path prints nothing and exits 0, which Copilot reads as no
output and passes the prompt through unchanged.
"""

import json
import sys
from typing import Optional

REMINDER = "\n".join(
    [
        "PREFLIGHT: before code work, name the skills and subagents that own this task and invoke them, "
        "or say none apply and why. Delegate investigation, review and bounded implementation by default. "
        "Follow the user-communication skill when writing to the user. "
        "If the prompt asks anything, answer every question first, then start the work. "
        "End every reply to the user with this block, exactly as shown: no heading, no bullets, "
        "no numbered list, plain lines only, keeping every blank line:",
        "",
        "Running: `running task name` (or: nothing)",
        "",
        "~~DONE: older finished task~~",
        "~~DONE: most recent finished task~~",
        "",
        "**NOW: what is being done right now**",
        "",
        "Next: the next task",
        "Then: the task after that",
        "",
        "Waiting on: what you wait for (or: nothing)",
        "",
        "When several tasks run, list each name in backticks on the Running line, separated by commas.",
    ]
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
