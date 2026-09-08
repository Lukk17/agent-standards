---
name: jira-integration
description: 'Jira mechanics from a coding session: fetching an issue and its comments, running JQL, adding progress comments, transitioning status through the project workflow, and linking branches back to the key, through the Atlassian MCP server or the REST v3 API. Use when you say "pull up PROJ-1234", "move this ticket to In Review", "comment the PR link on the ticket", or "find my open issues this sprint". Not for how a work item should be written or closed, use `project-tracking`.'
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

### Configure the server in your tool's own MCP file

This repository keeps one MCP configuration file per agent tool, and a server has to be declared in the file the tool
actually reads. Add the Atlassian MCP server there, following the setup document `docs/MCP_SETUP.md`, which lists the
file each tool reads and the schema each one expects.

Two rules hold regardless of tool. The secret comes from the process environment, never as a literal value inside a
configuration file that can be committed. Do not pin the server package to a version in project configuration, so a
consumer picks up fixes without editing a file this repository owns.

Pass:

```text
JIRA_URL, JIRA_EMAIL and JIRA_API_TOKEN exported in the shell that starts the agent. Config file names the server only.
```

Fail:

```json
{"env": {"JIRA_API_TOKEN": "the-real-token-pasted-into-a-committed-file"}}
```

Create the token at the Atlassian account security page, store it in the environment or a secrets manager, and scope
it to the projects you actually need. Rotate it immediately if it ever reaches git history.

---

### Fall back to REST v3 when no MCP server is available

The REST API answers the same questions over `curl`. It needs the same three environment variables.

| Variable | What it holds |
|---|---|
| `JIRA_URL` | The instance base URL |
| `JIRA_EMAIL` | The Atlassian account email |
| `JIRA_API_TOKEN` | The API token, from the environment only |

Validate that all three are set before the first call and fail with a clear message if not, because an unset variable
produces a 401 that reads like a permissions problem.

---

### Know which MCP tool answers which question

| Tool | Use it for |
|---|---|
| `jira_search` | JQL queries across a project |
| `jira_get_issue` | Full detail for one key |
| `jira_create_issue` | Creating a Task, Bug, Story or Epic |
| `jira_update_issue` | Changing summary, description or assignee |
| `jira_get_transitions` | The transition IDs valid for this issue right now |
| `jira_transition_issue` | Moving status |
| `jira_add_comment` | Progress updates |
| `jira_get_sprint_issues` | Everything in the active sprint |
| `jira_create_issue_link` | Blocks, relates to, duplicates |
| `jira_get_issue_development_info` | Linked branches, commits and pull requests |

---

### Read a transition ID before transitioning

Transition IDs are per project workflow and change between projects, so an ID that worked on one board fails on the
next. Ask for the available transitions first, match on the name, then execute.

Read the available transitions:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234/transitions" | jq '.transitions[] | {id, name}'
```

Then execute the one you matched:

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d '{"transition": {"id": "31"}}' "$JIRA_URL/rest/api/3/issue/PROJ-1234/transitions"
```

Pass:

```text
Fetched transitions, "In Review" is id 31 on this board, transitioned with 31.
```

Fail:

```text
Used transition id 21 because that was "In Review" on the last project.
```

---

### Fetch an issue with the fields you need

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234" | jq '{key, summary: .fields.summary, status: .fields.status.name, type: .fields.issuetype.name, labels: .fields.labels, description: .fields.description}'
```

Fetch the comment thread separately, because it is large and usually not needed:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" "$JIRA_URL/rest/api/3/issue/PROJ-1234?fields=comment" | jq '.fields.comment.comments[] | {author: .author.displayName, created: .created[:10], body: .body}'
```

Search with JQL:

```bash
curl -s -G -u "$JIRA_EMAIL:$JIRA_API_TOKEN" --data-urlencode "jql=project = PROJ AND status = 'In Progress'" "$JIRA_URL/rest/api/3/search"
```

---

### Post a comment in Atlassian document format

The v3 comment endpoint takes a structured document, not a plain string. A plain string is rejected with a 400 that
does not say why.

```bash
curl -s -X POST -u "$JIRA_EMAIL:$JIRA_API_TOKEN" -H "Content-Type: application/json" -d '{"body":{"version":1,"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Branch feat/PROJ-1234 pushed."}]}]}}' "$JIRA_URL/rest/api/3/issue/PROJ-1234/comment"
```

Pass:

```text
Comment body wrapped in the doc structure with a paragraph node.
```

Fail:

```json
{"body": "Branch pushed."}
```

---

### Write only the fields the user named

Create or modify an issue only when the user asked for it, and set only the fields they named. Adding a label, a
component, a priority or a sprint on your own edits somebody else's board, and the change is invisible until a filter
returns the wrong set. Take the description template from the tracker rather than inventing one.

Pass:

```text
Asked for a bug in PROJ with that summary and description. Created exactly those two fields. Nothing else set.
```

Fail:

```text
Created it and added the "backend" component, priority High and the current sprint, since that seemed right.
```

---

### Update as you go, at the points that carry information

| Moment in the work | What to record on the issue |
|---|---|
| Work starts | Transition to the in-progress status |
| Branch created | Comment with the branch name |
| Tests written | Comment with what they cover |
| Pull request opened | Comment with the link, and link the issue |
| Pull request merged | Transition to the next status in the workflow |

Keep each comment short and link outward rather than pasting content. A comment that reproduces a test report goes
stale the moment the report is regenerated, and a link never does.

Pass:

```text
PR opened: <link>. 6 tests added covering the 429 path. Ready for review.
```

Fail:

```text
[400 lines of pasted test output]
```

---

### Defer the content of the item to project-tracking

What a good acceptance criterion looks like, how to size and split an item, which label taxonomy is allowed, and what
has to be true before an item closes are all owned by `project-tracking`. Read that skill before you write a
description, criteria or a closure comment, and use this skill only for getting that content into and out of Jira.

Where criteria are vague, ask before writing code rather than inventing an interpretation, and check linked issues
first so you understand the full scope of the feature.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `401 Unauthorized` | Token invalid, expired, or not exported into the agent's process | Check the environment, regenerate if needed |
| `403 Forbidden` | Token lacks permission on that project | Check token scope and project access |
| `404 Not Found` | Wrong key or wrong base URL | Verify `JIRA_URL` and the issue key |
| `400` on a comment | Body sent as a plain string | Wrap it in the Atlassian document structure |
| Transition rejected | ID belongs to a different workflow | Read the transitions for this issue first |
| Connection timeout | Network or VPN | Check VPN and firewall rules |
| MCP server will not start | Launcher binary not on the agent's PATH | Use the absolute path, or set PATH in the shell profile that starts the agent |

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
- [ ] No version pin was added to project MCP configuration
- [ ] Transitions were read for this issue before one was executed
- [ ] Only the fields the user named were written
- [ ] Comments link outward rather than pasting reports
- [ ] Item content follows `project-tracking`, not conventions invented here
