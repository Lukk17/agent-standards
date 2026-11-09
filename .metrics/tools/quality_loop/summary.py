"""The worst entries of the three score files, as plain text an agent reads before it fixes anything.

The bands are Robert C. Martin's: a CRAP score over 30 must be fixed and a changed function aims under 10, every
surviving mutant is a missing test, and every duplicate pair at or above 0.82 is reviewed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from quality_loop import edn

CRAP_MUST_FIX = 30.0
CRAP_GOAL = 10.0
DUPLICATE_REVIEW = 0.82

CRAP_FILE = Path(".metrics") / "crap.edn"
DRY_FILE = Path(".metrics") / "dry.edn"
MUTATE_DIR = Path(".metrics") / "mutate"


@dataclass(frozen=True, slots=True)
class Survivor:
    file: str
    line: int | None
    function: str
    original: str
    mutant: str

    def render(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        change = f"delete {self.original}" if self.mutant == "" else f"{self.original} -> {self.mutant}"
        return f"  {where}  {self.function}  {change}"


def _read(path: Path) -> object | None:
    try:
        return edn.loads(path.read_text(encoding="utf-8"))
    except (OSError, edn.EdnError):
        return None


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _band(crap: float) -> str:
    if crap > CRAP_MUST_FIX:
        return "  must fix, over 30"
    if crap >= CRAP_GOAL:
        return "  over the goal of 10"
    return ""


def crap_section(root: Path, limit: int) -> list[str]:
    data = _read(root / CRAP_FILE)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return [f"CRAP: no {CRAP_FILE.as_posix()} yet. Run .metrics/tools/run measure."]
    entries = [entry for entry in data["entries"] if isinstance(entry, dict)]
    scored = sorted(
        (entry for entry in entries if isinstance(entry.get("crap"), (int, float))),
        key=lambda entry: -float(entry["crap"]),
    )
    over = sum(1 for entry in scored if float(entry["crap"]) > CRAP_MUST_FIX)
    goal = sum(1 for entry in scored if CRAP_GOAL <= float(entry["crap"]) <= CRAP_MUST_FIX)
    lines = [f"CRAP ({CRAP_FILE.as_posix()}): {_count(len(entries), 'function')}, {over} over 30, {goal} from 10 to 30"]
    for entry in scored[:limit]:
        crap = float(entry["crap"])
        coverage = entry.get("coverage")
        covered = f"{float(coverage):5.1f}%" if isinstance(coverage, (int, float)) else "  n/a "
        name = f"{entry.get('namespace', '?')}.{entry.get('name', '?')}"
        lines.append(f"  {crap:7.1f}  cc {int(entry.get('complexity', 0)):3d}  cov {covered}  {name}{_band(crap)}")
    if len(scored) > limit:
        lines.append(f"  and {len(scored) - limit} more")
    return lines


def _span(span: object) -> str:
    if not isinstance(span, dict):
        return "?"
    return f"{span.get('file', '?')}:{span.get('start-line', '?')}-{span.get('end-line', '?')}"


def dry_section(root: Path, limit: int) -> list[str]:
    data = _read(root / DRY_FILE)
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        return [f"Duplicates: no {DRY_FILE.as_posix()} yet. Run .metrics/tools/run measure."]
    pairs = sorted(
        (pair for pair in data["candidates"] if isinstance(pair, dict) and isinstance(pair.get("score"), (int, float))),
        key=lambda pair: -float(pair["score"]),
    )
    review = [pair for pair in pairs if float(pair["score"]) >= DUPLICATE_REVIEW]
    lines = [f"Duplicates ({DRY_FILE.as_posix()}): {_count(len(review), 'pair')} at or above {DUPLICATE_REVIEW}"]
    for pair in review[:limit]:
        lines.append(f"  {float(pair['score']):.2f}  {_span(pair.get('left'))}  and  {_span(pair.get('right'))}")
    if len(review) > limit:
        lines.append(f"  and {len(review) - limit} more")
    return lines


def _line_of(root: Path, file: str, offset: object) -> int | None:
    if not isinstance(offset, int):
        return None
    try:
        source = (root / file).read_bytes()
    except OSError:
        return None
    return source[:offset].count(b"\n") + 1


def _survivor(root: Path, mutation: str) -> Survivor | None:
    try:
        file, _namespace, form, start, _end, original, mutant = json.loads(mutation)
    except (ValueError, TypeError):
        return None
    function = str(form).split("/", 1)[-1]
    return Survivor(str(file), _line_of(root, str(file), start), function, str(original), str(mutant))


def survivors(root: Path) -> tuple[list[Survivor], int]:
    """Every surviving mutant in the snapshots, and the count of sites no test reaches."""
    found: list[Survivor] = []
    uncovered = 0
    directory = root / MUTATE_DIR
    for path in sorted(directory.rglob("*.edn")) if directory.is_dir() else ():
        data = _read(path)
        if not isinstance(data, dict):
            continue
        outcomes = data.get("outcomes")
        for mutation, status in outcomes.items() if isinstance(outcomes, dict) else ():
            if status == "survived" and (survivor := _survivor(root, str(mutation))) is not None:
                found.append(survivor)
        forms = data.get("forms")
        for form in forms if isinstance(forms, list) else ():
            if isinstance(form, dict) and isinstance(form.get("uncovered"), int):
                uncovered += form["uncovered"]
    found.sort(key=lambda item: (item.file, item.line or 0, item.function))
    return found, uncovered


def mutate_section(root: Path, limit: int) -> list[str]:
    if not (root / MUTATE_DIR).is_dir():
        return [f"Mutants: no {MUTATE_DIR.as_posix()}/ yet. Run .metrics/tools/run measure."]
    found, uncovered = survivors(root)
    lines = [f"Mutants ({MUTATE_DIR.as_posix()}/): {len(found)} survived, {_count(uncovered, 'site')} no test reaches"]
    lines.extend(survivor.render() for survivor in found[:limit])
    if len(found) > limit:
        lines.append(f"  and {len(found) - limit} more")
    return lines


def render(root: Path, limit: int) -> str:
    """The three sections, worst first, each cut to `limit` entries."""
    sections = (crap_section(root, limit), dry_section(root, limit), mutate_section(root, limit))
    return "\n\n".join("\n".join(section) for section in sections) + "\n"
