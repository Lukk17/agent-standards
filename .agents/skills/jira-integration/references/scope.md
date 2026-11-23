# Scope

Companion reference for the [jira-integration](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

- Fetching a Jira issue to understand what is being asked
- Searching for issues with a JQL query
- Adding a progress comment to an issue during or after implementation
- Transitioning an issue through the project workflow
- Linking a branch, pull request or merge request back to an issue key
- Diagnosing a failing Jira call, such as a 401 or a rejected transition
- The user says "pull up PROJ-1234", "move this ticket to In Review", "comment the PR link on the ticket" or "find my open issues this sprint"

---

### When not to activate

- Deciding what an item should contain, how it is sized, or when it may close, use `project-tracking`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the key, use `git-workflow`
- Writing the tests the acceptance criteria imply, use `tdd-workflow` or the language test skill
- Reviewing the code the ticket produced, use `code-reviewer`

---

### Related skills

- `project-tracking` owns item kinds, sizing, acceptance criteria, labels, statuses and closure rules
- `github-ops` owns the same operational surface when the tracker is GitHub issues
- `git-workflow` owns branch naming and commit messages that carry the issue key
- `code-reviewer` owns reviewing the change the issue produced
- `application-security-review` owns handling and rotation of the API token itself
