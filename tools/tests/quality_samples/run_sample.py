#!/usr/bin/env python3
"""Run the quality loop on one sample project the way a consumer would, and check what it wrote.

The sample is copied into a fresh git repository together with `.metrics/tools`, as an import would deliver it,
and `.metrics/tools/run measure` and `summary` run there through the launcher of this system: `run` on Linux and
macOS, `run.cmd` on Windows. The check then reads the score files: some function was scored with real coverage,
dryer found the planted duplicate, and mutator reported the planted surviving mutant, which `summary` names too.

Usage:
  python tools/tests/quality_samples/run_sample.py <sample> [--workdir DIR]

Exit codes: 0 every check held, 1 a check failed, 2 usage error or the wrapper itself failed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
TOOLS = REPO_ROOT / ".metrics" / "tools"

# Every sample plants the same gaps, so the same six mutants survive in each, named as the language spells them.
# The exact list also catches a false kill, a mutant counted as killed only because its test run timed out.
_SURVIVORS = (
    ("isAdult", ">= -> >"),
    ("shippingCost", "<= -> <"),
    ("shippingCost", "> -> >="),
    ("shippingCost", "> -> >="),
    ("orderTotal", "< -> <="),
    ("orderTotal", "0 -> 1"),
)
_SNAKE = {"isAdult": "is_adult", "shippingCost": "shipping_cost", "orderTotal": "order_total"}
EXPECTED_SURVIVORS = {
    "python": sorted((_SNAKE[name], change) for name, change in _SURVIVORS),
    "typescript": sorted(_SURVIVORS),
    "java-maven": sorted(_SURVIVORS),
    "java-gradle": sorted(_SURVIVORS),
}
PLANTED_SURVIVOR = {sample: survivors[0][0] for sample, survivors in EXPECTED_SURVIVORS.items()}

LAUNCHERS = ("run", "run.cmd")
IGNORED = shutil.ignore_patterns(".venv", "__pycache__", "*.egg-info", "node_modules", "target", "build", ".gradle")


def stage(sample: str, workdir: Path) -> Path:
    """Copy the sample and the tools into a fresh repository, the shape a consumer project has after an import."""
    project = workdir / sample
    shutil.copytree(HERE / sample, project, ignore=IGNORED)
    shutil.copytree(TOOLS, project / ".metrics" / "tools", ignore=IGNORED)
    git = ["git", "-C", str(project), "-c", "user.name=quality-sample", "-c", "user.email=quality-sample@example.invalid"]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "add", "-A"], check=True)
    subprocess.run([*git, "commit", "-q", "-m", "sample"], check=True)
    # Check the launchers out again, so they hold the bytes .metrics/tools/.gitattributes gives a consumer's
    # checkout rather than the bytes of this repository's own.
    for name in LAUNCHERS:
        (project / ".metrics" / "tools" / name).unlink()
    subprocess.run([*git, "checkout", "--", ".metrics/tools"], check=True)
    return project


def launcher(project: Path) -> list[str]:
    tools = project / ".metrics" / "tools"
    if os.name == "nt":
        return ["cmd", "/c", str(tools / "run.cmd")]
    return [str(tools / "run")]


def run_wrapper(project: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    command = [*launcher(project), *arguments]
    print(f"+ {' '.join(command)}", flush=True)
    result = subprocess.run(command, cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace")
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result


def load_scores(project: Path) -> dict[str, object]:
    """The three score files, read with the wrapper's own EDN reader."""
    sys.path.insert(0, str(project / ".metrics" / "tools"))
    from quality_loop import edn, summary

    metrics = project / ".metrics"
    snapshots = [edn.loads(path.read_text(encoding="utf-8")) for path in sorted((metrics / "mutate").rglob("*.edn"))]
    return {
        "crap": edn.loads((metrics / "crap.edn").read_text(encoding="utf-8")),
        "dry": edn.loads((metrics / "dry.edn").read_text(encoding="utf-8")),
        "survivors": summary.survivors(project)[0],
        "snapshots": snapshots,
    }


def failures(sample: str, scores: dict[str, object], summary_text: str) -> list[str]:
    found: list[str] = []
    entries = scores["crap"]["entries"]
    if not any(isinstance(entry.get("coverage"), (int, float)) and entry["coverage"] > 0 for entry in entries):
        found.append("crap.edn scores no function with coverage above 0, so no coverage report was read")
    if not scores["dry"]["candidates"]:
        found.append("dry.edn lists no duplicate pair")
    planted = PLANTED_SURVIVOR[sample]
    survived = sorted((survivor.function, survivor.render().split("  ")[-1]) for survivor in scores["survivors"])
    if survived != EXPECTED_SURVIVORS[sample]:
        found.append(f"surviving mutants {survived}, expected {EXPECTED_SURVIVORS[sample]}")
    killed = sum(form.get("killed", 0) for snapshot in scores["snapshots"] for form in snapshot.get("forms", []))
    if killed == 0:
        found.append("mutator killed no mutant, so the tests never ran against one")
    if planted not in summary_text:
        found.append(f"summary does not name {planted}")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sample", choices=sorted(PLANTED_SURVIVOR))
    parser.add_argument("--workdir", type=Path, default=None, help="where to stage the project, default a temp dir")
    arguments = parser.parse_args()
    workdir = arguments.workdir or Path(tempfile.mkdtemp(prefix="quality-sample-"))
    workdir.mkdir(parents=True, exist_ok=True)
    project = stage(arguments.sample, workdir)
    measured = run_wrapper(project, "measure")
    if measured.returncode != 0:
        print(f"measure exited {measured.returncode}", file=sys.stderr)
        return 2
    report = run_wrapper(project, "summary")
    if report.returncode != 0:
        print(f"summary exited {report.returncode}", file=sys.stderr)
        return 2
    problems = failures(arguments.sample, load_scores(project), report.stdout)
    for problem in problems:
        print(f"FAIL {arguments.sample}: {problem}", file=sys.stderr)
    if not problems:
        print(f"ok {arguments.sample}: scores in {project / '.metrics'}, planted survivor reported")
    print(json.dumps({"sample": arguments.sample, "project": str(project), "failures": problems}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
