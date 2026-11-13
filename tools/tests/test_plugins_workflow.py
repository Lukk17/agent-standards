"""The Plugins workflow keeps the token where it is needed and nowhere else."""

import re

import pytest
import yaml

from tests.conftest import REPO_ROOT

WORKFLOW = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "plugins.yml").read_text(encoding="utf-8"))
JOBS = WORKFLOW["jobs"]
FULL_SHA = re.compile(r"[^@]+@[0-9a-f]{40}")
PIP = re.compile(r"\bpip3?\s+install\b|-m\s+pip\b")


def installs_packages(step: dict) -> bool:
    return "setup-python" in step.get("uses", "") or bool(PIP.search(step.get("run", "")))


def steps(job: str) -> list[dict]:
    return JOBS[job]["steps"]


def test_every_action_is_pinned_to_a_full_commit_sha():
    for job in JOBS.values():
        for step in job["steps"]:
            if "uses" in step:
                assert FULL_SHA.fullmatch(step["uses"]), step["uses"]


def test_no_checkout_keeps_credentials():
    for name, job in JOBS.items():
        for step in job["steps"]:
            if step.get("uses", "").startswith("actions/checkout@"):
                assert step.get("with", {}).get("persist-credentials") is False, name


def test_the_tag_list_is_planned_read_only_and_with_no_package_installed():
    plan = JOBS["tag-plan"]

    assert plan["permissions"] == {"contents": "read"}
    assert "tags" in plan["outputs"]
    assert not any(installs_packages(step) for step in plan["steps"])


def test_only_the_push_step_of_the_tag_job_holds_the_token():
    tag = JOBS["tag"]
    holders = [step["name"] for step in tag["steps"] if "secrets.GITHUB_TOKEN" in repr(step)]

    assert tag["permissions"] == {"contents": "write"}
    assert tag["needs"] == "tag-plan"
    assert holders == [s["name"] for s in tag["steps"] if "git -c" in s.get("run", "") and " push " in s.get("run", "")]
    assert len(holders) == 1
    assert not any(installs_packages(step) for step in tag["steps"])
    assert "${{" not in "".join(step.get("run", "") for step in tag["steps"]), "outputs reach the scripts through env only"


def test_the_tag_jobs_do_not_re_run_the_marketplace_check():
    for job in ("tag-plan", "tag"):
        assert not any("gen_plugins.py" in step.get("run", "") for step in steps(job))


@pytest.mark.parametrize("job", ["tag-plan", "tag"])
def test_tagging_runs_only_on_a_push_to_master(job):
    condition = JOBS[job]["if"]

    assert job == "tag" or ("github.event_name == 'push'" in condition and "refs/heads/master" in condition)
    assert job != "tag" or JOBS["tag"]["needs"] == "tag-plan"


def test_every_push_has_its_own_uncancelled_concurrency_group():
    concurrency = WORKFLOW["concurrency"]

    assert "github.sha" in concurrency["group"]
    assert concurrency["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
