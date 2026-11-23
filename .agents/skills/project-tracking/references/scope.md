# Scope

Companion reference for the [project-tracking](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Before creating any work item, whatever its kind
- Before editing, splitting, re-typing or re-parenting an existing item
- Before closing or cancelling an item
- Before triaging the backlog, proposing a re-organisation, or running a bulk edit
- Checking that a branch, commit or merge-request title carries the item id
- When a dependency, a duplicate or a parent relationship needs recording
- Before proposing a change to a board, a workflow, a status set or a cadence
- The user says "write this ticket", "split this story", "are these criteria testable", "can we close this" or "triage the backlog"

The skill holds tracker-independent standards for planning and tracking work: kinds of work, sizing and splitting, epics as outcomes, labels, statuses and closure, testable acceptance criteria, links and bounded work in progress.

---

### When not to activate

- Calling the Jira API to read, comment on or transition an issue, use `jira-integration`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the item key, use `git-workflow`
- Recording an architectural decision rather than a unit of work, use `architecture-decision-records`
- Writing the tests that an acceptance criterion implies, use `tdd-workflow` or the language test skill
- Deciding how to hand the work to an agent once the item exists, use `agentic-engineering`

---

### Related skills

- `jira-integration` owns reading, commenting on and transitioning an issue through the Jira API
- `github-ops` owns issue triage, pull request operations and releases on GitHub
- `git-workflow` owns the branch name and commit message that link a change back to an item
- `architecture-decision-records` owns recording a design decision rather than a unit of work
- `agentic-engineering` owns sizing and routing the work once the item exists
- `markdown-writer` owns the human-facing documents an item may produce
