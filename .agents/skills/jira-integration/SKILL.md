---
name: jira-integration
description: 'Jira mechanics from a coding session through the Atlassian MCP server or the REST v3 API: fetching an issue, running JQL, progress comments, status transitions and linking branches to the key. Use when the user says "pull up PROJ-1234", "move this ticket to In Review", "comment the PR link on the ticket" or "find my open issues this sprint". Not for writing a work item, use `project-tracking`.'
---

# Jira Integration

How to talk to Jira from a coding session: authenticate, read an issue, act on it, and record progress against it.
The content rules for a work item, what it should say and when it may close, live in `project-tracking`, and this
skill defers to them rather than restating them.

---

### When to activate

- Fetching a Jira issue to understand what is being asked
- Searching for issues with a JQL query
- Adding a progress comment to an issue during or after implementation
- Transitioning an issue through the project workflow
- Linking a branch, pull request or merge request back to an issue key
- Diagnosing a failing Jira call, such as a 401 or a rejected transition

---

### When not to activate

- Deciding what an item should contain, how it is sized, or when it may close, use `project-tracking`
- Operating GitHub issues, pull requests and releases, use `github-ops`
- Naming the branch or writing the commit message that carries the key, use `git-workflow`
- Writing the tests the acceptance criteria imply, use `tdd-workflow` or the language test skill
- Reviewing the code the ticket produced, use `code-reviewer`

---

### Reference files

| Task | Open |
|---|---|
| Adding the MCP server, the REST v3 variables, the MCP tool table, transition, fetch, JQL and comment commands, troubleshooting | [references/access-and-calls.md](references/access-and-calls.md) |
| Examples of a correctly scoped new issue, the update-point table, and the deferral to `project-tracking` | [references/issue-updates.md](references/issue-updates.md) |

---

### Ask before acting

Create or modify an issue only when the user asked for it, and create each new issue only after the user approved
that one issue. Every transition or comment is a proposal, not an action: tell the user the transition or the comment
you would make, and run it only after they approve that one action.

---

### Rules

1. Add Atlassian's hosted remote MCP server yourself, signed in by OAuth 2.1 or an API token in an `Authorization` header. No configuration file in this repository declares one.
2. A token comes from the process environment or a secrets manager, never as a literal in a configuration file that can be committed. Scope it to the projects you need and rotate it at once if it reaches git history.
3. Without an MCP server, use REST v3 with `JIRA_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN`, and check all three are set before the first call, because an unset one reads as a 401.
4. Call the MCP tool name the connected server actually lists, since older servers list older names.
5. Read the available transitions for this issue and match on the name before transitioning. Transition IDs differ per workflow.
6. Fetch only the fields you need, and the comment thread separately. Search through `/rest/api/3/search/jql` with `fields` named and a bounded query, never the deprecated `/rest/api/3/search`.
7. A v3 comment body is an Atlassian document (`doc` with a paragraph node), never a plain string.
8. A new issue gets its parent epic and at least one area label and at most one nature-of-work label from the project's documented list, never invented. Priority, components, sprint and assignee are set only when the user names them. Take the description template from the tracker.
9. Propose updates at the points that carry information (work starts, branch created, tests written, pull request opened, pull request merged), and keep comments short, linking outward rather than pasting reports.
10. Item content (criteria, sizing, labels, closure) follows `project-tracking`. Where criteria are vague, ask before writing code, and check linked issues first.

---

### Related skills

- `project-tracking` owns item kinds, sizing, acceptance criteria, labels, statuses and closure rules
- `github-ops` owns the same operational surface when the tracker is GitHub issues
- `git-workflow` owns branch naming and commit messages that carry the issue key
- `code-reviewer` owns reviewing the change the issue produced
- `security-review` owns handling and rotation of the API token itself

---

### Checklist

- [ ] Credentials come from the process environment, never a literal in a config file
- [ ] The MCP server is declared in the file the running tool actually reads
- [ ] Each MCP tool called is one the connected server actually lists
- [ ] Every transition and comment ran only after the user approved that one action
- [ ] Transitions were read for this issue before one was executed
- [ ] A new issue carries its parent epic and the required labels from the project's list
- [ ] Every other field written was one the user named
- [ ] Comments link outward rather than pasting reports
- [ ] Item content follows `project-tracking`, not conventions invented here
