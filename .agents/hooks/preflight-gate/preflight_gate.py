#!/usr/bin/env python3
"""Starter of the shared preflight gate, the file every agent wiring runs.

The rules live in gate_rules.py beside this file and are imported from it, so
the interpreter keeps a compiled copy of them in __pycache__ and loads that on
the next start. A rules file that is missing or cannot be imported allows the
call: exit 0 and nothing on stdout, like every other allow, with one line on
stderr that names the failure, which no agent reads as a decision on exit 0
(docs/agent-compatibility.md).

HOOK_ORDER is the runner order of the gate, which the OpenCode and Kilo Code
runner reads from this file (docs/hooks-contract.md).
"""

import sys

HOOK_ORDER = 10

LOAD_FAILURE = "preflight-gate: gate_rules failed to load: {kind}: {message}\n"


def _report_load_failure(error: Exception) -> None:
    """Write one line naming the import failure to stderr, and never raise."""
    message = " ".join(str(error).split())

    try:
        sys.stderr.write(LOAD_FAILURE.format(kind=type(error).__name__, message=message))
        sys.stderr.flush()
    except (AttributeError, OSError, ValueError):
        pass


def main() -> int:
    try:
        from gate_rules import main as decide
    except Exception as error:
        _report_load_failure(error)
        return 0

    return decide()


if __name__ == "__main__":
    sys.exit(main())
