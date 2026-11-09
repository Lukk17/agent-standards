"""The command line: `measure`, `mutate [--changed]` and `summary [--limit N]`.

Exit status: 0 the run finished, 1 a tool or a setup step failed, 2 a usage error, 3 `mutate` left a surviving
mutant.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from quality_loop import loop, summary
from quality_loop.host import Host
from quality_loop.process import run_process

TOOLS_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LIMIT = 10


def _positive(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--root", type=Path, default=None, help="the project to measure, default the folder holding .metrics/"
    )
    commands = argparse.ArgumentParser(
        prog=".metrics/tools/run",
        description="Measure code with Robert C. Martin's crapper, dryer and mutator, and read the scores back.",
    )
    subcommands = commands.add_subparsers(dest="command", required=True)
    subcommands.add_parser(
        "measure", parents=[common], help="run all three tools in full and write their scores into .metrics/"
    )
    mutate = subcommands.add_parser("mutate", parents=[common], help="run mutator alone, with fresh coverage")
    mutate.add_argument("--changed", action="store_true", help="only the source files git reports as changed")
    report = subcommands.add_parser(
        "summary", parents=[common], help="print the worst entries of the three score files"
    )
    report.add_argument("--limit", type=_positive, default=DEFAULT_LIMIT, help="entries per section, default 10")
    return commands


def _say(message: str) -> None:
    print(f"quality-loop: {message}", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    root = (arguments.root or TOOLS_DIR.parent.parent).resolve()
    if arguments.command == "summary":
        sys.stdout.write(summary.render(root, arguments.limit))
        return loop.SUCCESS
    session = loop.Session(root=root, tools_dir=TOOLS_DIR, host=Host.current(), run=run_process, say=_say)
    if arguments.command == "measure":
        return loop.measure(session)
    return loop.mutate(session, changed=arguments.changed)
