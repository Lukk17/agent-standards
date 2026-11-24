#!/usr/bin/env python3
"""Starter of the shared preflight gate, the file every agent wiring runs.

The rules live in gate_rules.py beside this file and are imported from it, so
the interpreter keeps a compiled copy of them in __pycache__ and loads that on
the next start. A rules file that is missing or cannot be imported allows the
call: exit 0 and nothing printed, like every other allow.

HOOK_ORDER is the runner order of the gate, which the OpenCode and Kilo Code
runner reads from this file (docs/hooks-contract.md).
"""

import sys

HOOK_ORDER = 10


def main() -> int:
    try:
        from gate_rules import main as decide
    except Exception:
        return 0

    return decide()


if __name__ == "__main__":
    sys.exit(main())
