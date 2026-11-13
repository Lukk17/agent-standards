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


TAG_GUARD = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "plugin-tags.yml").read_text(encoding="utf-8"))


def test_the_tag_guard_runs_on_tag_pushes_deletions_and_a_schedule():
    triggers = TAG_GUARD[True]  # YAML 1.1 reads the key `on` as True

    assert triggers["push"] == {"tags": ["*--v*"]}
    assert "delete" in triggers and triggers["schedule"]


def test_the_tag_guard_only_reads_and_runs_master_s_own_check():
    job = TAG_GUARD["jobs"]["check"]
    checkout, run = job["steps"]

    assert TAG_GUARD["permissions"] == {"contents": "read"} and "permissions" not in job
    assert FULL_SHA.fullmatch(checkout["uses"])
    assert checkout["with"]["ref"] == "master" and checkout["with"]["persist-credentials"] is False
    assert run["run"] == "python3 tools/check_tags.py --master origin/master"
    assert not any(installs_packages(step) for step in job["steps"])
    assert "secrets." not in repr(TAG_GUARD)


def test_every_unquoted_tags_expansion_runs_with_globbing_off():
    for step in JOBS["tag"]["steps"]:
        script = step.get("run", "")
        if "$TAGS" in script:
            assert script.index("set -f") < script.index("$TAGS"), step["name"]


def test_the_tag_guard_header_says_a_tag_push_runs_the_tagged_commit_s_workflow():
    header = (REPO_ROOT / ".github" / "workflows" / "plugin-tags.yml").read_text(encoding="utf-8").split("\non:")[0]

    assert "as it is at\n# the tagged commit" in header
