"""The coverage and test commands each language needs on this system, where the tools' own choice would fail.

crapper and mutator pick a coverage tool and a test command per language themselves. Where that choice breaks,
the wrapper hands them a working one through their `--coverage-command` and `--test-command` options:

- Gradle, on every system, because neither tool knows it.
- Windows, for Maven, npm and Python: the tools start `mvn`, `npm` and `npx` without a shell, which cannot run
  `mvn.cmd` or `npm.cmd`, and they look for a project interpreter only under `.venv/bin`.

Go and Rust ship real executables on Windows too, and Clojure is left to the tools.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from quality_loop import build, languages
from quality_loop.host import Host

PYTHON_MARKERS = ("pyproject.toml", "setup.cfg", "setup.py", "pytest.ini", "tox.ini")
VITEST_CONFIGS = tuple(f"vitest.config.{suffix}" for suffix in ("ts", "mts", "cts", "js", "mjs", "cjs"))

JACOCO_REPORTS = ("target/site/jacoco", "*/target/site/jacoco", "*/*/target/site/jacoco")
JACOCO_FILES = tuple(f"{folder}/jacoco.xml" for folder in JACOCO_REPORTS)
PYTHON_REPORT_DIR = "target/coverage/python"
TYPESCRIPT_REPORT_DIR = "target/coverage/typescript"
LCOV_FILES = ("target/coverage/**/lcov.info", "coverage/**/lcov.info")

# mutator stops a mutant at ten times the baseline run. A JVM build in a fresh worker, starting its own Gradle
# daemon or JVM beside the other workers, measured up to nine times its baseline, so Java gets more room.
JVM_TIMEOUT_FACTOR = 30


@dataclass(frozen=True, slots=True)
class LanguagePlan:
    """How the tools measure one language: which files, and the commands that replace their own, if any."""

    language: str
    filters: tuple[str, ...]
    coverage_command: str | None = None
    test_command: str | None = None
    stale_reports: tuple[str, ...] = ()
    report_dir: str | None = None
    reports: tuple[str, ...] = ()
    timeout_factor: int | None = None
    warning: str | None = None

    @property
    def overridden(self) -> bool:
        return self.coverage_command is not None or self.test_command is not None


def python_roots(root: Path, files: Sequence[Path]) -> list[Path]:
    """The directory each Python file is tested from: its nearest marker file up to root, else root."""
    found: set[Path] = set()
    for path in files:
        if languages.language_of(path) != languages.PYTHON:
            continue
        found.add(_nearest_marker(path.parent, root) or root)
    return sorted(found)


def _nearest_marker(start: Path, root: Path) -> Path | None:
    current = start
    while True:
        if any((current / marker).is_file() for marker in PYTHON_MARKERS):
            return current
        if current == root or current.parent == current:
            return None
        current = current.parent


def uses_pytest(directory: Path) -> bool:
    """crapper's own test: a pytest.ini or conftest.py, or pytest named in a project configuration file."""
    if (directory / "pytest.ini").is_file() or (directory / "conftest.py").is_file():
        return True
    for name in ("pyproject.toml", "setup.cfg", "tox.ini"):
        path = directory / name
        if path.is_file() and "pytest" in path.read_text(encoding="utf-8", errors="replace"):
            return True
    return False


def package_scripts(root: Path) -> dict[str, str] | None:
    """The scripts of the root package.json, or None when there is no readable one."""
    path = root / "package.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    scripts = data.get("scripts") if isinstance(data, dict) else None
    if not isinstance(scripts, dict):
        return {}
    return {str(key): str(value) for key, value in scripts.items()}


def uses_vitest(root: Path, scripts: dict[str, str]) -> bool:
    return "vitest" in scripts.get("test", "") or any((root / name).is_file() for name in VITEST_CONFIGS)


def _java_plan(root: Path, host: Host) -> LanguagePlan:
    filters = languages.extension_filters(languages.JAVA)
    kind = build.java_build(root)
    if kind == build.GRADLE:
        gradle = build.gradle_executable(root, host)
        return LanguagePlan(
            languages.JAVA,
            filters,
            coverage_command=f"{gradle} test jacocoTestReport",
            # --rerun-tasks: the baseline in the built project would otherwise be an up-to-date check, and a
            # timeout of ten times that kills mutants that only needed a compile in their fresh worker.
            test_command=f"{gradle} -q --offline --rerun-tasks test",
            stale_reports=JACOCO_REPORTS,
            reports=JACOCO_FILES,
            timeout_factor=JVM_TIMEOUT_FACTOR,
        )
    if kind == build.MAVEN and host.windows:
        maven = build.maven_executable(root, host)
        plugin = build.JACOCO_MAVEN_PLUGIN
        return LanguagePlan(
            languages.JAVA,
            filters,
            coverage_command=f"{maven} -q {plugin}:prepare-agent test {plugin}:report",
            test_command=f"{maven} -q test -DexcludeTags=no-mutate",
            stale_reports=JACOCO_REPORTS,
            reports=JACOCO_FILES,
            timeout_factor=JVM_TIMEOUT_FACTOR,
        )
    return LanguagePlan(languages.JAVA, filters, timeout_factor=JVM_TIMEOUT_FACTOR)


def _python_plan(root: Path, host: Host, interpreters: dict[Path, Path]) -> LanguagePlan:
    filters = languages.extension_filters(languages.PYTHON)
    if not host.windows or not interpreters:
        return LanguagePlan(languages.PYTHON, filters)
    if len(interpreters) > 1:
        names = ", ".join(path.relative_to(root).as_posix() or "." for path in sorted(interpreters))
        return LanguagePlan(
            languages.PYTHON,
            filters,
            warning=f"Python is tested from several folders ({names}). On Windows the tools can run only one, "
            "so mutation testing fails its baseline in the others.",
        )
    directory, python = next(iter(interpreters.items()))
    runner = ["-m", "pytest"] if uses_pytest(directory) else ["-m", "unittest", "discover", "-s", "."]
    report_dir = root / PYTHON_REPORT_DIR
    data_file = report_dir / ".coverage"
    record = host.join([str(python), "-m", "coverage", "run", f"--data-file={data_file}", *runner])
    export = host.join(
        [str(python), "-m", "coverage", "lcov", f"--data-file={data_file}", "-o", str(report_dir / "lcov.info")]
    )
    test = host.join([str(python), *runner])
    relative = directory.relative_to(root).as_posix()
    if relative != ".":
        enter = host.join(["cd", relative.replace("/", "\\")]) + " && "
        record = enter + record
        test = enter + test
    return LanguagePlan(
        languages.PYTHON,
        filters,
        coverage_command=host.then(record, export),
        test_command=test,
        stale_reports=(PYTHON_REPORT_DIR,),
        report_dir=PYTHON_REPORT_DIR,
        reports=(f"{PYTHON_REPORT_DIR}/lcov.info",),
    )


def typescript_coverage_command(root: Path, scripts: dict[str, str]) -> str | None:
    """The same choice crapper makes: the coverage script, then Vitest's own report, then c8 around npm test."""
    if "coverage" in scripts:
        return "npm run coverage"
    if uses_vitest(root, scripts):
        return (
            "npx vitest run --coverage --coverage.reporter=lcov "
            f"--coverage.reportsDirectory={TYPESCRIPT_REPORT_DIR} --coverage.reportOnFailure=true"
        )
    if "test" in scripts:
        return f"npx --yes c8 --reporter=lcov --reports-dir {TYPESCRIPT_REPORT_DIR} npm test"
    return None


def _typescript_plan(root: Path, host: Host) -> LanguagePlan:
    filters = languages.extension_filters(languages.TYPESCRIPT)
    scripts = package_scripts(root)
    if not host.windows or scripts is None:
        return LanguagePlan(languages.TYPESCRIPT, filters)
    return LanguagePlan(
        languages.TYPESCRIPT,
        filters,
        coverage_command=typescript_coverage_command(root, scripts),
        test_command="npm test" if "test" in scripts else None,
        stale_reports=(TYPESCRIPT_REPORT_DIR,),
        reports=LCOV_FILES,
    )


def plan_languages(
    root: Path, present: Sequence[str], host: Host, interpreters: dict[Path, Path] | None = None
) -> list[LanguagePlan]:
    """One plan per language present, in the order given.

    Args:
        interpreters: the project Python of each Python root, from `prepare.project_interpreters`.
    """
    plans: list[LanguagePlan] = []
    for language in present:
        if language == languages.JAVA:
            plans.append(_java_plan(root, host))
        elif language == languages.PYTHON:
            plans.append(_python_plan(root, host, interpreters or {}))
        elif language == languages.TYPESCRIPT:
            plans.append(_typescript_plan(root, host))
        else:
            plans.append(LanguagePlan(language, languages.extension_filters(language)))
    return plans
