# Scope

Companion reference for the [git-workflow](../SKILL.md) skill. Open it when it is unclear whether a job belongs to this skill or to a neighbouring one.

---

### When to activate

Everything in this skill is about the local repository and the shared history, so operating the hosting platform belongs to `github-ops`. The skill applies when:

- Setting up the git workflow for a new project
- Choosing between GitHub Flow, trunk-based development and GitFlow
- Writing a commit message or a pull request description
- Deciding whether to merge or rebase in a specific situation
- Naming a branch, or cleaning up branches after a merge
- Resolving a conflict, or reducing how often conflicts happen
- Undoing a mistake in local or shared history
- Setting line endings, `.gitattributes`, `core.symlinks` or handling case sensitivity across operating systems
- The user says "what should I name this branch", "write the commit message for this", "merge or rebase here", "I have a conflict in this file", "set up .gitattributes" or "set up our git workflow"

---

### When not to activate

- Triaging issues, managing pull requests on the platform, or cutting a release, use `github-ops`
- Recording work items, sizing and acceptance criteria, use `project-tracking`
- Operating a Jira workflow around the branch, use `jira-integration`
- Reviewing the content of a diff for correctness, use `code-reviewer`
- Wording a review comment or a reply to one, use `review-comments`
- Designing the pipeline the branch triggers, use `deployment-patterns`
- Formatting Dart, Java or Python code inside the commit, use `code-formatter`. Any other language follows its
  language skill or its default formatter

---

### Related skills

- `github-ops` owns issues, pull request operations, CI triage and the whole release procedure
- `project-tracking` owns the work item the branch and commit reference
- `jira-integration` owns reading and updating the Jira issue behind the branch
- `code-reviewer` owns reviewing the content of the diff
- `review-comments` owns the wording of review comments and of the replies to them
- `deployment-patterns` owns what happens after the merge
- `application-security-review` owns the response when a secret does reach history
