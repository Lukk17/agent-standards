"""The two runs the quality loop makes: `measure`, all three tools in full, and `mutate`, mutator alone.

When every language present runs on the tools' own commands, each tool runs once over the whole project. When a
language needs a command of the wrapper's, and the project holds more than one language, the tools run once per
language, selected by the file extensions they accept as filters, because a `--coverage-command` or a
`--test-command` applies to every file of a run. crapper then runs once more in full on the coverage already
written, because a partial run replaces `.metrics/crap.edn` with only what it measured. crapper never runs with
`--changed`, which also scans files under `.metrics/tools`.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from quality_loop import build, environments, languages, plan, prepare
from quality_loop.host import Host
from quality_loop.plan import LanguagePlan
from quality_loop.process import Runner, tool_environment

SUCCESS = 0
FAILED = 1
SURVIVED = 3

# mutator's own exit statuses.
MUTATOR_SURVIVED = 3

WORKERS = Path("target") / "mutation-workers"
SYMLINK_FIX = (
    "mutator runs each mutant in a copy of the project built from symbolic links, and Windows refused to create "
    "one: {error}\n"
    "Turn on Developer Mode (Settings, System, For developers, Developer Mode), open a new terminal and run "
    "again. A terminal started as administrator works too."
)


@dataclass(frozen=True, slots=True)
class Session:
    """Everything one wrapper run works with, so a test can swap the system and the process runner."""

    root: Path
    tools_dir: Path
    host: Host
    run: Runner
    say: Callable[[str], None]


@dataclass(frozen=True, slots=True)
class Prepared:
    plans: list[LanguagePlan]
    pythons: dict[str, Path]

    @property
    def split(self) -> bool:
        """True when the tools must run once per language."""
        return len(self.plans) > 1 and any(item.overridden for item in self.plans)


def prepare_project(session: Session) -> Prepared | None:
    """Ready the project and the three tool environments. None when a tool environment cannot be built."""
    root = session.root
    files = languages.source_files(root)
    found = {languages.language_of(path) for path in files}
    present = tuple(language for language in languages.SUPPORTED if language in found)
    if not present:
        session.say(f"No Clojure, Go, Java, JavaScript, Python, Rust or TypeScript source under {root}.")
        return Prepared([], {})
    session.say(f"Languages: {', '.join(present)}.")
    if prepare.ensure_target_ignored(root):
        session.say("Added target/ to .gitignore, the folder the tools write their working files into.")
    interpreters: dict[Path, Path] = {}
    constraints = session.tools_dir / environments.CONSTRAINTS_NAME
    if languages.PYTHON in present:
        interpreters = prepare.project_interpreters(root, files, session.host, constraints, session.run, session.say)
    if languages.TYPESCRIPT in present:
        prepare.ensure_node_modules(root, session.host, session.run, session.say)
        prepare.ensure_vitest_provider(root, session.host, session.run, session.say)
    if languages.JAVA in present and build.java_build(root) == build.GRADLE:
        changed = build.ensure_gradle_report(root)
        if changed is not None:
            session.say(f"Added the JaCoCo report block to {changed.name}. Commit it on its own.")
    plans = plan.plan_languages(root, present, session.host, interpreters)
    for item in plans:
        if item.warning:
            session.say(item.warning)
    pythons: dict[str, Path] = {}
    for tool in environments.TOOLS:
        python = environments.tool_python(session.tools_dir, tool, session.host, session.run, session.say)
        if python is None:
            return None
        pythons[tool] = python
    return Prepared(plans, pythons)


def tool_argv(session: Session, prepared: Prepared, tool: str, *arguments: str) -> list[str]:
    """One tool started from its own environment against the project root.

    On Windows mutator starts through `mutator_windows.py`, which gives it the process-group kill a timed-out
    mutant needs and Windows lacks.
    """
    python = str(prepared.pythons[tool])
    if tool == "mutator" and session.host.windows:
        entry = [python, str(session.tools_dir / "quality_loop" / "mutator_windows.py")]
    else:
        entry = [python, "-m", tool]
    return [*entry, "--root", str(session.root), *arguments]


def clear_reports(root: Path, item: LanguagePlan) -> None:
    """Remove a language's old coverage reports before the wrapper's command writes new ones, so none is read stale."""
    for pattern in item.stale_reports:
        for path in root.glob(pattern):
            shutil.rmtree(path, ignore_errors=True)
    if item.report_dir:
        (root / item.report_dir).mkdir(parents=True, exist_ok=True)


def coverage_written(root: Path, item: LanguagePlan) -> bool:
    """True when the wrapper's coverage command left a report where the tools read one."""
    return any(path.is_file() for pattern in item.reports for path in root.glob(pattern))


def _report_missing(session: Session, item: LanguagePlan | None) -> bool:
    """Say so when a coverage command of the wrapper's wrote no report, which crapper only scores as 0%."""
    if item is None or item.coverage_command is None or coverage_written(session.root, item):
        return False
    session.say(
        f"No {item.language} coverage report was written, so crapper scored every {item.language} function at "
        "0% coverage. The coverage command's output above says why. Fix that and measure again."
    )
    return True


def _execute(session: Session, prepared: Prepared, tool: str, arguments: Sequence[str]) -> int:
    return session.run(tool_argv(session, prepared, tool, *arguments), session.root, tool_environment())


def _coverage_arguments(session: Session, item: LanguagePlan | None) -> list[str]:
    if item is None or item.coverage_command is None:
        return []
    clear_reports(session.root, item)
    return ["--coverage-command", item.coverage_command]


def _test_arguments(item: LanguagePlan | None) -> list[str]:
    if item is None or item.test_command is None:
        return []
    return ["--test-command", item.test_command]


def _timeout_arguments(plans: Sequence[LanguagePlan]) -> list[str]:
    """The largest timeout factor any of the plans asks for, since one mutator run serves them all."""
    factors = [item.timeout_factor for item in plans if item.timeout_factor is not None]
    return ["--timeout-factor", str(max(factors))] if factors else []


def _only(prepared: Prepared) -> LanguagePlan | None:
    return prepared.plans[0] if len(prepared.plans) == 1 else None


def run_crapper(session: Session, prepared: Prepared) -> bool:
    """crapper in full, writing the whole `.metrics/crap.edn`. True when every run exited 0."""
    if not prepared.split:
        item = _only(prepared)
        ok = _execute(session, prepared, "crapper", _coverage_arguments(session, item)) == 0
        return ok and not _report_missing(session, item)
    ok = True
    for item in prepared.plans:
        session.say(f"crapper: coverage for {item.language}")
        ok &= _execute(session, prepared, "crapper", [*_coverage_arguments(session, item), *item.filters]) == 0
        ok &= not _report_missing(session, item)
    session.say("crapper: every language together, on the coverage just written")
    return _execute(session, prepared, "crapper", ["--use-existing-coverage"]) == 0 and ok


def symlinks_work(root: Path) -> str | None:
    """None when this account can create the symbolic links mutator's workers are made of, else the error."""
    folder = root / WORKERS
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "quality-loop-probe-target"
    link = folder / "quality-loop-probe-link"
    try:
        target.write_text("probe\n", encoding="utf-8")
        link.unlink(missing_ok=True)
        os.symlink(target, link)
    except OSError as exc:
        return str(exc)
    finally:
        link.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
    return None


def run_mutator(session: Session, prepared: Prepared, leading: Sequence[str], own_coverage: bool) -> tuple[bool, bool]:
    """mutator once, or once per language. Returns (every run worked, some mutant survived).

    Args:
        leading: the arguments every run starts with, such as `--changed` or `--reuse-coverage`.
        own_coverage: True when mutator produces coverage itself, so the wrapper's coverage command goes with it.
    """
    if (error := symlinks_work(session.root)) is not None:
        session.say(SYMLINK_FIX.format(error=error))
        return False, False
    runs: list[list[str]] = []
    if not prepared.split:
        item = _only(prepared)
        coverage = _coverage_arguments(session, item) if own_coverage else []
        runs.append([*leading, *coverage, *_test_arguments(item), *_timeout_arguments(prepared.plans)])
    else:
        for item in prepared.plans:
            coverage = _coverage_arguments(session, item) if own_coverage else []
            runs.append([*leading, *coverage, *_test_arguments(item), *_timeout_arguments([item]), *item.filters])
    ok, survived = True, False
    for arguments in runs:
        code = _execute(session, prepared, "mutator", arguments)
        survived |= code == MUTATOR_SURVIVED
        ok &= code in (SUCCESS, MUTATOR_SURVIVED)
    return ok, survived


def measure(session: Session) -> int:
    """crapper and dryer in full, then mutator on the coverage crapper wrote. Survivors are data, not a failure."""
    prepared = prepare_project(session)
    if prepared is None:
        return FAILED
    if not prepared.plans:
        return SUCCESS
    ok = run_crapper(session, prepared)
    ok &= _execute(session, prepared, "dryer", []) == 0
    mutated, survived = run_mutator(session, prepared, ["--reuse-coverage"], own_coverage=False)
    ok &= mutated
    session.say("Scores are in .metrics/. Read the worst with: .metrics/tools/run summary")
    if survived:
        session.say("Some mutants survived. Each one is a test the project is missing.")
    return SUCCESS if ok else FAILED


def mutate(session: Session, changed: bool) -> int:
    """mutator alone with fresh coverage, on the changed files when `changed` is set. Exit 3 when a mutant survives."""
    prepared = prepare_project(session)
    if prepared is None:
        return FAILED
    if not prepared.plans:
        return SUCCESS
    ok, survived = run_mutator(session, prepared, ["--changed"] if changed else [], own_coverage=True)
    if not ok:
        return FAILED
    return SURVIVED if survived else SUCCESS
