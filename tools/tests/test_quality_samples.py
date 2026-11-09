"""Tests for tools/tests/quality_samples/run_sample.py, the check CI runs on each quality loop sample project.

The check itself starts the real tools, which only the CI job does. These cases feed its scoring step made-up scores,
so each failure it exists to catch is seen to fire, and hold the sample folders to the samples CI names.
"""

import importlib.util
import re

import pytest
from tests.conftest import REPO_ROOT
from tests.quality_loop_support import QUALITY_TOOLS  # noqa: F401  puts quality_loop on the path

from quality_loop.summary import Survivor

SAMPLES = REPO_ROOT / "tools" / "tests" / "quality_samples"


def _load_run_sample():
    spec = importlib.util.spec_from_file_location("run_sample", SAMPLES / "run_sample.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN_SAMPLE = _load_run_sample()


def scores(sample, survivors=None, coverage=50.0, candidates=1, killed=3):
    names = RUN_SAMPLE.EXPECTED_SURVIVORS[sample] if survivors is None else survivors
    return {
        "crap": {"entries": [{"name": "f", "coverage": coverage}]},
        "dry": {"candidates": [{}] * candidates},
        "survivors": [Survivor("src/x", 1, name, *change.split(" -> ")) for name, change in names],
        "snapshots": [{"forms": [{"killed": killed}]}],
    }


@pytest.mark.parametrize("sample", sorted(RUN_SAMPLE.EXPECTED_SURVIVORS))
def test_the_planted_scores_pass(sample):
    planted = RUN_SAMPLE.PLANTED_SURVIVOR[sample]

    assert RUN_SAMPLE.failures(sample, scores(sample), f"... {planted} ...") == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"coverage": 0.0}, "no function with coverage above 0"),
        ({"candidates": 0}, "no duplicate pair"),
        ({"killed": 0}, "killed no mutant"),
        ({"survivors": [("shippingCost", "> -> >=")]}, "surviving mutants"),
    ],
)
def test_each_missing_score_is_reported(change, expected):
    problems = RUN_SAMPLE.failures("java-gradle", scores("java-gradle", **change), "isAdult")

    assert any(expected in problem for problem in problems), problems


def test_a_false_kill_of_one_planted_survivor_fails_the_check():
    survivors = RUN_SAMPLE.EXPECTED_SURVIVORS["python"][1:]

    problems = RUN_SAMPLE.failures("python", scores("python", survivors), "is_adult")

    assert problems and problems[0].startswith("surviving mutants")


def test_a_summary_that_does_not_name_the_planted_function_fails():
    assert RUN_SAMPLE.failures("typescript", scores("typescript"), "nothing here") == ["summary does not name isAdult"]


def test_every_sample_ci_runs_has_a_folder():
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    named = set(re.findall(r"sample: ([a-z-]+)", workflow))

    assert named == set(RUN_SAMPLE.EXPECTED_SURVIVORS)
    assert all((SAMPLES / sample).is_dir() for sample in named)


def test_the_suite_never_collects_a_samples_own_tests():
    assert "quality_samples" in (REPO_ROOT / "tools" / "pyproject.toml").read_text(encoding="utf-8")
