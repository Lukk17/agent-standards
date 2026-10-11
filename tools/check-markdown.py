#!/usr/bin/env python3
"""Markdown lint for human-facing docs, the command CI runs.

The rules live in `.agents/hooks/_check_markdown.py`, which ships to consumers
so the markdown lint hook can reach them there. This file only runs that one
copy, with the same arguments, so the rules are never written twice.
"""

import runpy
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / ".agents" / "hooks" / "_check_markdown.py"


if __name__ == "__main__":
    runpy.run_path(str(RULES), run_name="__main__")
