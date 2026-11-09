"""Get a project ready for the tools: ignore their working folder, and install what its tests need.

Each step is idempotent, so `measure` and `mutate` run all of them every time and a ready project costs a few
file checks.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from pathlib import Path

from quality_loop import plan
from quality_loop.host import Host
from quality_loop.process import Runner

# The tools write coverage data and mutation workers here. The folder name is fixed in their code.
WORK_FOLDER = "target"
IGNORE_LINE = "target/"
_IGNORING_LINES = frozenset({"target", "target/", "/target", "/target/", "**/target", "**/target/"})

REQUIREMENT_FILES = ("requirements.txt", "requirements-dev.txt", "requirements-test.txt", "dev-requirements.txt")
TEST_EXTRAS = ("dev", "test", "tests")
PIP = ("-m", "pip", "install", "--disable-pip-version-check", "--quiet")

VITEST_PROVIDER = "@vitest/coverage-v8"
NPM_MANIFESTS = ("package.json", "package-lock.json", "npm-shrinkwrap.json")


def git_ignores_target(root: Path) -> bool | None:
    """git's own answer, which counts every ignore file it reads. None when git cannot answer here."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "-q", "--no-index", f"{WORK_FOLDER}/"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return {0: True, 1: False}.get(result.returncode)


def gitignore_names_target(gitignore: Path) -> bool:
    if not gitignore.is_file():
        return False
    lines = gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    return any(line.strip() in _IGNORING_LINES for line in lines)


def ensure_target_ignored(root: Path, git_check: Callable[[Path], bool | None] = git_ignores_target) -> bool:
    """Add one `target/` line to the root `.gitignore` unless the project already ignores the folder.

    Returns:
        True when the line was added.
    """
    if git_check(root) is True:
        return False
    gitignore = root / ".gitignore"
    if gitignore_names_target(gitignore):
        return False
    existing = gitignore.read_bytes().decode("utf-8", errors="replace") if gitignore.is_file() else ""
    newline = "\r\n" if "\r\n" in existing else "\n"
    separator = "" if not existing or existing.endswith("\n") else newline
    gitignore.write_bytes((existing + separator + IGNORE_LINE + newline).encode("utf-8"))
    return True


def existing_interpreter(directory: Path, host: Host) -> Path | None:
    """The interpreter of the virtual environment the tools look for first, `.venv`, then `venv`."""
    for name in (".venv", "venv"):
        python = host.venv_python(directory / name)
        if python.is_file():
            return python
    return None


def _pyproject(directory: Path) -> dict[str, object]:
    path = directory / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def install_steps(directory: Path, python: Path) -> list[list[str]]:
    """What a fresh project environment needs to run the project's own tests."""
    steps = [[str(python), *PIP, "-r", name] for name in REQUIREMENT_FILES if (directory / name).is_file()]
    project = _pyproject(directory).get("project")
    if isinstance(project, dict) or (directory / "setup.py").is_file():
        optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
        extras = [name for name in TEST_EXTRAS if isinstance(optional, dict) and name in optional]
        target = f".[{','.join(extras)}]" if extras else "."
        steps.append([str(python), *PIP, "-e", target])
    return steps


def ensure_test_modules(
    python: Path, directory: Path, constraints: Path, run: Runner, say: Callable[[str], None]
) -> None:
    """Install coverage, and pytest when the project uses it, at the pinned versions, when they are missing."""
    wanted = ["coverage", "pytest"] if plan.uses_pytest(directory) else ["coverage"]
    for module in wanted:
        if run([str(python), "-c", f"import {module}"], directory) == 0:
            continue
        say(f"Installing {module} into {python.parent.parent} for the coverage run.")
        run([str(python), *PIP, "-c", str(constraints), module], directory)


def project_interpreters(
    root: Path,
    files: Sequence[Path],
    host: Host,
    constraints: Path,
    run: Runner,
    say: Callable[[str], None],
) -> dict[Path, Path]:
    """The Python each Python root tests with, creating `.venv` where there is none.

    Without a project environment, mutator runs the tests with its own interpreter, which has none of the
    project's dependencies, so every baseline fails.
    """
    interpreters: dict[Path, Path] = {}
    for directory in plan.python_roots(root, files):
        python = existing_interpreter(directory, host)
        if python is None:
            python = host.venv_python(directory / ".venv")
            say(f"Creating the project environment {directory / '.venv'} for the Python tests.")
            if run([sys.executable, "-m", "venv", str(directory / ".venv")], directory) != 0:
                say(f"Could not create {directory / '.venv'}. Python tests will fail their baseline.")
                continue
            for argv in install_steps(directory, python):
                if run(argv, directory) != 0:
                    say("A project dependency did not install. The tests may fail until it does.")
        ensure_test_modules(python, directory, constraints, run, say)
        interpreters[directory] = python
    return interpreters


def ensure_node_modules(root: Path, host: Host, run: Runner, say: Callable[[str], None]) -> None:
    """Install the root package's dependencies when node_modules is missing, from the lockfile when there is one."""
    if not (root / "package.json").is_file() or (root / "node_modules").is_dir():
        return
    npm = host.which("npm")
    if npm is None:
        say("npm is not on PATH, so the TypeScript and JavaScript tests cannot run.")
        return
    command = "ci" if (root / "package-lock.json").is_file() else "install"
    run([npm, command], root)


def _vitest_version(root: Path) -> str | None:
    try:
        data = json.loads((root / "node_modules" / "vitest" / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get("version") if isinstance(data, dict) else None
    return version if isinstance(version, str) else None


def ensure_vitest_provider(root: Path, host: Host, run: Runner, say: Callable[[str], None]) -> None:
    """On Windows, install Vitest's coverage provider the way crapper does elsewhere, leaving the manifests as they were.

    crapper installs it itself on Linux and macOS, but starts npm in a way Windows cannot run.
    """
    scripts = plan.package_scripts(root)
    if not host.windows or scripts is None or "coverage" in scripts or not plan.uses_vitest(root, scripts):
        return
    if (root / "node_modules" / "@vitest" / "coverage-v8").is_dir():
        return
    npm = host.which("npm")
    if npm is None:
        return
    version = _vitest_version(root)
    spec = f"{VITEST_PROVIDER}@{version}" if version else VITEST_PROVIDER
    say(f"Installing {spec} so Vitest can write coverage. package.json and the lockfile are restored afterwards.")
    saved = {name: (root / name).read_bytes() if (root / name).is_file() else None for name in NPM_MANIFESTS}
    try:
        run([npm, "install", "--no-save", "--no-package-lock", spec], root)
    finally:
        for name, content in saved.items():
            path = root / name
            if content is None:
                path.unlink(missing_ok=True)
            elif not path.is_file() or path.read_bytes() != content:
                path.write_bytes(content)
