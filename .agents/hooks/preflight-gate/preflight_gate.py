#!/usr/bin/env python3
"""Starter of the shared preflight gate, the file every agent wiring runs.

The rules live in gate_rules.py beside this file. The starter first takes its
own folder off the import path, so no file planted there can stand in for a
standard module, and then loads the rules by their path with Python's source
loader, so no package, extension module or other file of that name can stand in
for them either. The source loader keeps a compiled copy in __pycache__ and
loads that on the next start. A rules file that is missing or cannot be loaded
allows the call: exit 0 and nothing on stdout, like every other allow, with one
line on stderr that names the failure, which no agent reads as a decision on
exit 0 (docs/agent-compatibility.md).

HOOK_ORDER is the runner order of the gate, which the OpenCode and Kilo Code
runner reads from this file (docs/hooks-contract.md).
"""

import sys

HOOK_ORDER = 10

RULES_MODULE = "gate_rules"
RULES_FILE = RULES_MODULE + ".py"
LOAD_FAILURE = "preflight-gate: gate_rules failed to load: {kind}: {message}\n"
MESSAGE_CAP = 300


def _drop_own_folder() -> None:
    """Take the folder Python put first on the import path for this script off it.

    Run as a script, Python puts the script's folder first on sys.path, unless
    -P, -I or PYTHONSAFEPATH asked it not to. Only the standard library stays.
    """
    if sys.path and not getattr(sys.flags, "safe_path", False):
        del sys.path[0]


def _one_clean_line(text: str) -> str:
    """The text on one line, every character that cannot be printed as ?, cut to MESSAGE_CAP."""
    joined = " ".join(text.split())

    return "".join(character if character.isprintable() else "?" for character in joined)[:MESSAGE_CAP]


def _report_load_failure(error: BaseException) -> None:
    """Write one line naming the load failure to stderr, and never raise."""
    try:
        line = LOAD_FAILURE.format(kind=_one_clean_line(type(error).__name__), message=_one_clean_line(str(error)))
        sys.stderr.write(line)
        sys.stderr.flush()
    except Exception:
        pass


def _load_rules():
    """The rules module, loaded from RULES_FILE beside this file and nowhere else.

    Raises:
        Exception: any error the rules file raises while it is read or run.
        SystemExit: when the rules file calls sys.exit while it runs.
    """
    import os
    from importlib.machinery import SourceFileLoader
    from importlib.util import module_from_spec, spec_from_file_location

    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), RULES_FILE)
    spec = spec_from_file_location(RULES_MODULE, path, loader=SourceFileLoader(RULES_MODULE, path))
    module = module_from_spec(spec)
    sys.modules[RULES_MODULE] = module
    spec.loader.exec_module(module)

    return module


def main() -> int:
    try:
        decide = _load_rules().main
    except (Exception, SystemExit) as error:
        _report_load_failure(error)
        return 0

    return decide()


if __name__ == "__main__":
    _drop_own_folder()
    sys.exit(main())
